"""Manager agent message handler — parses update instructions, writes YAML."""

import json
import re
from copy import deepcopy

import discord
from anthropic import AsyncAnthropic
from loguru import logger

from shared.llm import chat
from shared.memory import ChannelMemory
from manager_agent.prompts import build_system_prompt


class ManagerHandler:
    """Handles messages in admin channels. Parses plain-text instructions via LLM, updates YAML."""

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str,
        memory: ChannelMemory,
        data_manager,
        managed_agents: list[str] | None = None,
    ):
        self.client = client
        self.model = model
        self.memory = memory
        self.data_manager = data_manager
        self.managed_agents = managed_agents or ["pricing_agent"]
        self._system_prompt: str | None = None
        self._pending_changes: dict[int, dict] = {}

        data_manager.on_change(self._rebuild_prompt)

    def _rebuild_prompt(self) -> None:
        self._system_prompt = build_system_prompt(
            self.data_manager.pricing,
            self.data_manager.objections,
            managed_agents=self.managed_agents,
        )
        logger.info("Manager system prompt rebuilt ({} chars)", len(self._system_prompt))

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._rebuild_prompt()
        return self._system_prompt

    async def handle(self, message: discord.Message) -> None:
        content = message.content.strip()
        channel_id = message.channel.id

        if content.lower() == "!clear":
            self.memory.clear(channel_id)
            self._pending_changes.pop(channel_id, None)
            await message.reply("Conversation cleared.")
            return

        # Confirmation flow
        if channel_id in self._pending_changes and content.lower() in ("yes", "y", "confirm"):
            await self._apply_change(message, self._pending_changes.pop(channel_id))
            return

        if channel_id in self._pending_changes and content.lower() in ("no", "n", "cancel"):
            self._pending_changes.pop(channel_id)
            await message.reply("Change cancelled.")
            return

        self.memory.add(channel_id, "user", f"{message.author.display_name}: {content}")
        messages = self.memory.get_messages(channel_id)

        try:
            async with message.channel.typing():
                reply = await chat(
                    client=self.client,
                    model=self.model,
                    system_prompt=self.system_prompt,
                    messages=messages,
                    temperature=0.3,
                )

            self.memory.add(channel_id, "assistant", reply)

            action = self._extract_json(reply)

            if action and action.get("action") == "show_data":
                await self._handle_show(message, reply)
            elif action and action.get("action") in ("update_pricing", "update_objections"):
                await self._handle_update_proposal(message, channel_id, action)
            else:
                await self._send_reply(message, reply)

        except Exception:
            logger.exception("Error in manager handler")
            await message.reply("Something went wrong — try again in a moment.")

    def _extract_json(self, text: str) -> dict | None:
        match = re.search(r"```json\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from LLM response")
                return None
        return None

    async def _handle_show(self, message: discord.Message, full_reply: str) -> None:
        clean = re.sub(r"```json\s*\n?.*?\n?\s*```", "", full_reply, flags=re.DOTALL).strip()
        await self._send_reply(message, clean if clean else full_reply)

    async def _handle_update_proposal(
        self, message: discord.Message, channel_id: int, action: dict
    ) -> None:
        self._pending_changes[channel_id] = action

        summary = action.get("summary", "Update data")
        old_val = action.get("old_value", "?")
        new_val = action.get("new_value", "?")
        path = action.get("path", "?")

        confirm_msg = (
            f"**Proposed Change:**\n"
            f"- **Field:** `{path}`\n"
            f"- **Old:** {old_val}\n"
            f"- **New:** {new_val}\n"
            f"- **Summary:** {summary}\n\n"
            f"Type **yes** to confirm or **no** to cancel."
        )
        await message.reply(confirm_msg)

    async def _apply_change(self, message: discord.Message, action: dict) -> None:
        file_target = action.get("file", "pricing")
        path = action.get("path", "")
        new_value = action.get("new_value")

        try:
            if file_target == "pricing":
                data = deepcopy(self.data_manager.pricing)
            else:
                data = deepcopy(self.data_manager.objections)

            _set_nested(data, path, new_value)

            if file_target == "pricing":
                self.data_manager.save_pricing(data)
            else:
                self.data_manager.save_objections(data)

            summary = action.get("summary", "Data updated")
            await message.reply(
                f"Done. {summary}\n\n"
                f"All agents using this data will pick up the changes on their next message."
            )
            logger.info("Manager applied change: {} → {}", path, new_value)

        except Exception as e:
            logger.exception("Failed to apply change")
            await message.reply(f"Failed to apply change: {e}")
            self._pending_changes.pop(message.channel.id, None)

    async def _send_reply(self, message: discord.Message, text: str) -> None:
        chunks = _split_text(text, 1990)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)


def _set_nested(data: dict, path: str, value) -> None:
    """Set a value in a nested dict using dot notation with bracket indexing."""
    keys = []
    for part in path.split("."):
        bracket_match = re.match(r"^(\w+)\[(\d+)\]$", part)
        if bracket_match:
            keys.append(bracket_match.group(1))
            keys.append(int(bracket_match.group(2)))
        else:
            keys.append(part)
    obj = data
    for key in keys[:-1]:
        obj = obj[key]
    obj[keys[-1]] = value


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
