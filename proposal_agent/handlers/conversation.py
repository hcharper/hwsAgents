from __future__ import annotations

import io
import logging

import discord

from proposal_agent.config import Config
from proposal_agent.handlers.pricing import (
    PricingTimeoutError,
    PricingParseError,
    parse_pricing_response,
    request_pricing,
    wait_for_pricing_response,
)
from proposal_agent.services.claude import ClaudeService, ClaudeServiceError
from proposal_agent.services.pdf import generate_pdf
from proposal_agent.services.proposal import PricingLineItem, Proposal
from proposal_agent.templates.proposal_embed import build_proposal_embed
from proposal_agent.utils.context import ContextStore, ConversationState

logger = logging.getLogger(__name__)

READY_SENTINEL = "[READY_FOR_PRICING]"

GREETING = (
    "Hey! I'm the Proposal Bot. Tell me about the project you'd "
    "like a proposal for and I'll help put one together."
)


class ConversationHandler:
    """Drives the per-channel conversation state machine."""

    def __init__(
        self,
        bot: discord.Client,
        config: Config,
        claude: ClaudeService,
        store: ContextStore,
    ) -> None:
        self._bot = bot
        self._config = config
        self._claude = claude
        self._store = store

    async def handle_message(self, message: discord.Message) -> None:
        """Main entry point called from ``on_message``."""
        ctx = self._store.get(message.channel.id)

        if ctx.state == ConversationState.IDLE:
            await self._on_idle(message, ctx)
        elif ctx.state == ConversationState.GATHERING:
            await self._on_gathering(message, ctx)
        elif ctx.state == ConversationState.WAITING_FOR_PRICING:
            # Ignore human messages while waiting; pricing replies are
            # handled via wait_for in the pricing module.
            await message.channel.send(
                "Still waiting on the pricing bot -- hang tight!"
            )
        elif ctx.state == ConversationState.REVIEW:
            await self._on_review(message, ctx)
        elif ctx.state == ConversationState.FINALIZED:
            await self._on_finalized(message, ctx)

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    async def _on_idle(self, message, ctx):
        ctx.state = ConversationState.GATHERING
        ctx.add_user_message(message.content)
        try:
            reply = await self._claude.gather_info(
                ctx.get_messages_for_api()
            )
        except ClaudeServiceError as exc:
            await message.channel.send(f"Sorry, something went wrong: {exc}")
            ctx.reset()
            return

        if READY_SENTINEL in reply:
            reply_clean = reply.replace(READY_SENTINEL, "").strip()
            if reply_clean:
                await message.channel.send(reply_clean)
            ctx.add_assistant_message(reply)
            await self._transition_to_pricing(message.channel, ctx)
        else:
            ctx.add_assistant_message(reply)
            await message.channel.send(reply)

    async def _on_gathering(self, message, ctx):
        ctx.add_user_message(message.content)
        try:
            reply = await self._claude.gather_info(
                ctx.get_messages_for_api()
            )
        except ClaudeServiceError as exc:
            await message.channel.send(f"Sorry, something went wrong: {exc}")
            return

        if READY_SENTINEL in reply:
            reply_clean = reply.replace(READY_SENTINEL, "").strip()
            if reply_clean:
                await message.channel.send(reply_clean)
            ctx.add_assistant_message(reply)
            await self._transition_to_pricing(message.channel, ctx)
        else:
            ctx.add_assistant_message(reply)
            await message.channel.send(reply)

    async def _on_review(self, message, ctx):
        content_lower = message.content.strip().lower()
        if content_lower in ("approve", "looks good", "finalize", "done", "yes"):
            await self._finalize(message.channel, ctx)
            return

        if content_lower in ("cancel", "start over", "reset"):
            ctx.reset()
            await message.channel.send(
                "No problem — proposal discarded. Send a message whenever "
                "you'd like to start a new one."
            )
            return

        ctx.add_user_message(message.content)
        await message.channel.send("Applying your changes...")
        try:
            proposal = await self._claude.revise_proposal(
                ctx.get_messages_for_api(),
                message.content,
                ctx.proposal_json,
            )
        except ClaudeServiceError as exc:
            await message.channel.send(
                f"Couldn't apply revisions: {exc}. Please try again."
            )
            return

        ctx.proposal_json = proposal.to_json()
        ctx.add_assistant_message(
            f"Updated proposal:\n```json\n{ctx.proposal_json}\n```"
        )
        embed = build_proposal_embed(proposal)
        await message.channel.send(
            "Here's the updated proposal. Reply with changes, "
            "or say **approve** to finalize.",
            embed=embed,
        )

    async def _on_finalized(self, message, ctx):
        ctx.reset()
        ctx.state = ConversationState.GATHERING
        ctx.add_user_message(message.content)
        try:
            reply = await self._claude.gather_info(
                ctx.get_messages_for_api()
            )
        except ClaudeServiceError as exc:
            await message.channel.send(f"Sorry, something went wrong: {exc}")
            ctx.reset()
            return
        ctx.add_assistant_message(reply)
        await message.channel.send(reply)

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    async def _transition_to_pricing(self, channel, ctx):
        ctx.state = ConversationState.WAITING_FOR_PRICING
        await channel.send(
            "Great, I have enough details! Let me check with the pricing bot..."
        )

        try:
            await request_pricing(channel, self._config, ctx.project_details)
            raw_pricing = await wait_for_pricing_response(
                self._bot, channel.id, self._config
            )
        except PricingTimeoutError:
            await channel.send(
                "The pricing bot didn't respond in time. You can paste "
                "pricing info here and I'll use that instead."
            )
            ctx.state = ConversationState.GATHERING
            return

        ctx.pricing_data = raw_pricing
        ctx.add_assistant_message(f"Pricing received:\n{raw_pricing}")

        await self._generate_draft(channel, ctx)

    async def _generate_draft(self, channel, ctx):
        ctx.state = ConversationState.DRAFTING
        await channel.send("Drafting your proposal now...")

        try:
            proposal = await self._claude.generate_proposal(
                ctx.get_messages_for_api(),
                ctx.pricing_data,
            )
        except ClaudeServiceError as exc:
            await channel.send(
                f"Failed to generate proposal: {exc}. "
                "Let me know if you'd like to try again."
            )
            ctx.state = ConversationState.GATHERING
            return

        ctx.proposal_json = proposal.to_json()
        ctx.state = ConversationState.REVIEW
        ctx.add_assistant_message(
            f"Draft proposal:\n```json\n{ctx.proposal_json}\n```"
        )

        embed = build_proposal_embed(proposal)
        await channel.send(
            "Here's your draft proposal! Review it below and let me know "
            "if you'd like any changes, or say **approve** to finalize.",
            embed=embed,
        )

    async def _finalize(self, channel, ctx):
        ctx.state = ConversationState.FINALIZED
        proposal = Proposal.from_json(ctx.proposal_json)

        pdf_bytes = generate_pdf(proposal)
        filename = (
            f"proposal_{proposal.project_title.replace(' ', '_').lower()}.pdf"
        )
        pdf_file = discord.File(
            io.BytesIO(pdf_bytes), filename=filename
        )
        embed = build_proposal_embed(proposal)

        await channel.send(
            "Proposal finalized! Here's your completed proposal with the PDF attached.",
            embed=embed,
            file=pdf_file,
        )
        await channel.send(
            "Send another message whenever you'd like to start a new proposal."
        )
