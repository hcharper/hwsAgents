from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import discord

from proposal_agent.config import Config

logger = logging.getLogger(__name__)


@dataclass
class PricingResult:
    raw_text: str
    line_items: list[tuple[str, float]]
    total: float


class PricingTimeoutError(Exception):
    """Raised when the pricing bot doesn't respond in time."""


class PricingParseError(Exception):
    """Raised when the pricing bot's response can't be parsed."""


def build_pricing_request(project_details: dict) -> str:
    """Format the structured message body sent alongside the @mention.

    The ``project_details`` dict is expected to contain keys populated
    during the gathering phase.  Missing keys are silently skipped.
    """
    lines = ["estimate for:"]
    field_map = {
        "project_name": "Project",
        "tech_stack": "Tech",
        "features": "Pages/Features",
        "timeline": "Timeline",
    }
    for key, label in field_map.items():
        value = project_details.get(key)
        if value:
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


async def request_pricing(
    channel: discord.abc.Messageable,
    config: Config,
    project_details: dict,
) -> str:
    """Send an @mention to the pricing bot and return the raw message text.

    This sends the message and returns immediately — the caller is
    responsible for waiting for the response via
    :func:`wait_for_pricing_response`.
    """
    mention = f"<@{config.pricing_bot_id}>"
    body = build_pricing_request(project_details)
    full_message = f"{mention} {body}"
    await channel.send(full_message)
    return full_message


async def wait_for_pricing_response(
    bot: discord.Client,
    channel_id: int,
    config: Config,
) -> str:
    """Block until the pricing bot replies in the given channel, or timeout."""

    def _is_pricing_reply(message: discord.Message) -> bool:
        return (
            message.author.id == config.pricing_bot_id
            and message.channel.id == channel_id
        )

    try:
        msg: discord.Message = await bot.wait_for(
            "message",
            check=_is_pricing_reply,
            timeout=config.pricing_timeout_seconds,
        )
        return msg.content
    except asyncio.TimeoutError:
        raise PricingTimeoutError(
            f"Pricing bot did not respond within "
            f"{config.pricing_timeout_seconds}s"
        )


def parse_pricing_response(raw: str) -> PricingResult:
    """Extract line items and total from the pricing bot's text response.

    Expected format (flexible)::

        Some header text:
        - Item description: $1,234.56
        - Another item: $789
        Total: $2,023.56

    Returns a :class:`PricingResult` with parsed data.
    """
    item_pattern = re.compile(
        r"[-•*]\s*(.+?):\s*\$?([\d,]+(?:\.\d{1,2})?)"
    )
    total_pattern = re.compile(
        r"[Tt]otal\s*:\s*\$?([\d,]+(?:\.\d{1,2})?)"
    )

    line_items: list[tuple[str, float]] = []
    for match in item_pattern.finditer(raw):
        desc = match.group(1).strip()
        amount = float(match.group(2).replace(",", ""))
        if "total" not in desc.lower():
            line_items.append((desc, amount))

    total_match = total_pattern.search(raw)
    if total_match:
        total = float(total_match.group(1).replace(",", ""))
    elif line_items:
        total = sum(amt for _, amt in line_items)
    else:
        raise PricingParseError(
            "Could not parse any pricing data from the response"
        )

    return PricingResult(raw_text=raw, line_items=line_items, total=total)
