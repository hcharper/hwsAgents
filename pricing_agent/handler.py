"""Pricing agent message handler."""

import discord
from anthropic import AsyncAnthropic
from loguru import logger

from shared.llm import chat
from shared.memory import ChannelMemory
from pricing_agent.prompts import build_system_prompt


class PricingHandler:
    """Handles messages in sales/pricing channels."""

    def __init__(
        self,
        client: AsyncAnthropic,
        model: str,
        memory: ChannelMemory,
        data_manager,
        proposal_bot_id: int | None = None,
    ):
        self.client = client
        self.model = model
        self.memory = memory
        self.data_manager = data_manager
        self.proposal_bot_id = proposal_bot_id
        self._system_prompt: str | None = None

        data_manager.on_change(self._rebuild_prompt)

    def _rebuild_prompt(self) -> None:
        self._system_prompt = build_system_prompt(
            self.data_manager.pricing,
            self.data_manager.objections,
            proposal_bot_id=self.proposal_bot_id,
        )
        logger.info("Pricing system prompt rebuilt ({} chars)", len(self._system_prompt))

    @property
    def system_prompt(self) -> str:
        if self._system_prompt is None:
            self._rebuild_prompt()
        return self._system_prompt

    async def handle(self, message: discord.Message) -> None:
        content = message.content.strip()
        channel_id = message.channel.id

        if content.lower() in ("!clear", "/clear"):
            self.memory.clear(channel_id)
            # Purge bot messages from the channel
            try:
                # Delete all messages except pinned ones
                deleted = await message.channel.purge(
                    limit=100,
                    check=lambda m: not m.pinned,
                )
                await message.channel.send(f"Cleared {len(deleted)} messages.", delete_after=5)
            except discord.Forbidden:
                await message.reply("Conversation memory cleared (no permission to delete messages).")
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
                    temperature=0.7,
                    agent_name="pricing_agent",
                )

            self.memory.add(channel_id, "assistant", reply)
            await self._send_reply(message, reply)

        except Exception:
            logger.exception("Error in pricing handler")
            await message.reply("Something went wrong — try again in a moment.")

    async def _send_reply(self, message: discord.Message, text: str) -> None:
        chunks = _split_text(text, 1990)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)


def _split_text(text: str, max_len: int) -> list[str]:
    """Split text into chunks at line boundaries."""
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
