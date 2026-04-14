from __future__ import annotations

import discord

from proposal_agent.services.proposal import Proposal

EMBED_COLOR = 0x2B6CB0  # professional blue
FIELD_CHAR_LIMIT = 1024


def _truncate(text: str, limit: int = FIELD_CHAR_LIMIT) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def build_proposal_embed(proposal: Proposal) -> discord.Embed:
    """Build a rich Discord embed summarising the proposal."""
    embed = discord.Embed(
        title=f"Proposal: {proposal.project_title}",
        description=_truncate(proposal.executive_summary),
        color=EMBED_COLOR,
    )
    embed.set_author(name=f"Prepared for {proposal.client_name}")
    embed.add_field(name="Date", value=proposal.date, inline=True)
    embed.add_field(
        name="Total", value=proposal.formatted_total, inline=True
    )

    scope_text = "\n".join(f"• {item}" for item in proposal.scope_of_work)
    embed.add_field(
        name="Scope of Work",
        value=_truncate(scope_text),
        inline=False,
    )

    deliverables_text = "\n".join(
        f"• {item}" for item in proposal.deliverables
    )
    embed.add_field(
        name="Deliverables",
        value=_truncate(deliverables_text),
        inline=False,
    )

    timeline_text = "\n".join(
        f"**{phase.name}** ({phase.duration}): {phase.description}"
        for phase in proposal.timeline
    )
    embed.add_field(
        name="Timeline",
        value=_truncate(timeline_text),
        inline=False,
    )

    pricing_text = "\n".join(
        f"• {item.description}: {item.formatted_amount()}"
        for item in proposal.pricing
    )
    pricing_text += f"\n\n**Total: {proposal.formatted_total}**"
    embed.add_field(
        name="Pricing",
        value=_truncate(pricing_text),
        inline=False,
    )

    embed.set_footer(text="Full proposal attached as PDF")
    return embed
