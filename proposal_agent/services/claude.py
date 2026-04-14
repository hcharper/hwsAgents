from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import anthropic

from proposal_agent.config import Config
from proposal_agent.services.proposal import Proposal

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "templates" / "proposal_prompt.txt"

MAX_HISTORY_MESSAGES = 40


class ClaudeServiceError(Exception):
    """Raised when the Claude API call fails."""


class ClaudeService:
    def __init__(self, config: Config) -> None:
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self._model = config.claude_model
        self._system_prompt = _PROMPT_PATH.read_text()

    async def gather_info(
        self, messages: list[dict[str, str]]
    ) -> str:
        """Send conversation history and get a gathering response.

        Returns the assistant's text reply.  If the model decides it has
        enough information it will include ``[READY_FOR_PRICING]`` in
        the response.
        """
        return await self._chat(messages)

    async def generate_proposal(
        self,
        messages: list[dict[str, str]],
        pricing_data: str,
    ) -> Proposal:
        """Ask Claude to produce a full proposal JSON given the conversation
        history and pricing data from the pricing bot."""
        enriched = list(messages) + [
            {
                "role": "user",
                "content": (
                    "Here is the pricing data from our pricing system:\n\n"
                    f"{pricing_data}\n\n"
                    "Please generate the full project proposal as JSON."
                ),
            }
        ]
        raw = await self._chat(enriched)
        return self._parse_proposal(raw)

    async def revise_proposal(
        self,
        messages: list[dict[str, str]],
        revision_request: str,
        current_proposal_json: str,
    ) -> Proposal:
        """Apply a user's revision request to an existing proposal."""
        enriched = list(messages) + [
            {
                "role": "user",
                "content": (
                    f"Current proposal:\n```json\n{current_proposal_json}\n```\n\n"
                    f"Requested changes: {revision_request}\n\n"
                    "Return the updated full proposal JSON."
                ),
            }
        ]
        raw = await self._chat(enriched)
        return self._parse_proposal(raw)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _chat(self, messages: list[dict[str, str]]) -> str:
        trimmed = messages[-MAX_HISTORY_MESSAGES:]
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=self._system_prompt,
                messages=trimmed,
            )
            return response.content[0].text
        except anthropic.APIError as exc:
            logger.exception("Claude API error")
            raise ClaudeServiceError(str(exc)) from exc

    @staticmethod
    def _parse_proposal(raw: str) -> Proposal:
        """Extract JSON from a fenced code block in the response."""
        match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if not match:
            raise ClaudeServiceError(
                "Claude response did not contain a JSON code block"
            )
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ClaudeServiceError(
                f"Invalid JSON in Claude response: {exc}"
            ) from exc
        return Proposal.from_dict(data)
