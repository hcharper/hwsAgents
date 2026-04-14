"""End-to-end integration test with all externals mocked."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from proposal_agent.config import Config
from proposal_agent.handlers.conversation import ConversationHandler
from proposal_agent.services.claude import ClaudeService
from proposal_agent.services.proposal import Proposal, PricingLineItem, TimelinePhase
from proposal_agent.utils.context import ContextStore, ConversationState
from tests.proposal.conftest import make_mock_bot, make_mock_message


SAMPLE_PROPOSAL = Proposal(
    client_name="Acme Corp",
    project_title="Customer Portal",
    executive_summary="A portal for Acme's customers.",
    scope_of_work=["Auth system", "Dashboard", "API"],
    deliverables=["Web app", "Docs"],
    timeline=[TimelinePhase("Build", "4 weeks", "Development")],
    pricing=[
        PricingLineItem("Frontend", 6000),
        PricingLineItem("Backend", 4000),
    ],
    terms_and_conditions="Net 30",
    date="2026-04-14",
)


@pytest.fixture
def setup(config):
    bot = make_mock_bot()
    store = ContextStore()
    with patch("proposal_agent.services.claude.anthropic.Anthropic"):
        claude = ClaudeService(config)
    handler = ConversationHandler(bot, config, claude, store)
    return handler, store, bot, claude


@pytest.mark.asyncio
class TestFullHappyPath:
    async def test_end_to_end(self, setup, config):
        handler, store, bot, claude = setup

        # --- Step 1: User describes project (Idle -> Gathering) ---
        claude.gather_info = AsyncMock(
            return_value="What tech stack and timeline do you have in mind?"
        )
        msg1 = make_mock_message(content="I need a customer portal for Acme Corp")
        await handler.handle_message(msg1)

        ctx = store.get(msg1.channel.id)
        assert ctx.state == ConversationState.GATHERING
        assert len(ctx.history) == 2  # user + assistant

        # --- Step 2: User provides more detail -> Claude says ready ---
        claude.gather_info = AsyncMock(
            return_value="Perfect, I have everything I need. [READY_FOR_PRICING]"
        )

        pricing_reply = MagicMock()
        pricing_reply.content = (
            "Estimate for Customer Portal:\n"
            "- Frontend: $6,000\n"
            "- Backend: $4,000\n"
            "Total: $10,000"
        )
        bot.wait_for = AsyncMock(return_value=pricing_reply)

        claude.generate_proposal = AsyncMock(return_value=SAMPLE_PROPOSAL)

        msg2 = make_mock_message(content="React + Node, 4 week timeline")
        await handler.handle_message(msg2)

        assert ctx.state == ConversationState.REVIEW
        assert ctx.proposal_json is not None
        assert ctx.pricing_data is not None

        # Verify pricing bot was @mentioned
        send_calls = msg2.channel.send.call_args_list
        mention_calls = [
            c for c in send_calls
            if c.args and f"<@{config.pricing_bot_id}>" in str(c.args[0])
        ]
        assert len(mention_calls) >= 1

        # --- Step 3: User requests a revision ---
        revised = Proposal.from_json(SAMPLE_PROPOSAL.to_json())
        revised.project_title = "Customer Portal v2"
        claude.revise_proposal = AsyncMock(return_value=revised)

        msg3 = make_mock_message(content="Change the title to Customer Portal v2")
        await handler.handle_message(msg3)

        assert ctx.state == ConversationState.REVIEW
        assert "Customer Portal v2" in ctx.proposal_json

        # --- Step 4: User approves ---
        msg4 = make_mock_message(content="approve")
        await handler.handle_message(msg4)

        assert ctx.state == ConversationState.FINALIZED

        # Verify final message included a file attachment (PDF)
        final_calls = msg4.channel.send.call_args_list
        file_calls = [c for c in final_calls if c.kwargs.get("file")]
        assert len(file_calls) == 1
        assert file_calls[0].kwargs["file"].filename.endswith(".pdf")

        # Verify final message included an embed
        embed_calls = [c for c in final_calls if c.kwargs.get("embed")]
        assert len(embed_calls) == 1


@pytest.mark.asyncio
class TestPricingTimeoutRecovery:
    async def test_timeout_then_manual_flow(self, setup, config):
        handler, store, bot, claude = setup

        # Gathering -> ready
        claude.gather_info = AsyncMock(
            return_value="Got it. [READY_FOR_PRICING]"
        )
        bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

        msg = make_mock_message(content="Build me an app")
        await handler.handle_message(msg)

        ctx = store.get(msg.channel.id)
        assert ctx.state == ConversationState.GATHERING

        # User can continue providing info
        claude.gather_info = AsyncMock(return_value="Thanks for the pricing info.")
        msg2 = make_mock_message(content="Here's the pricing: Dev $5000")
        await handler.handle_message(msg2)

        assert ctx.state == ConversationState.GATHERING
