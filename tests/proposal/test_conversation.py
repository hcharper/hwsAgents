from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proposal_agent.config import Config
from proposal_agent.handlers.conversation import ConversationHandler, READY_SENTINEL
from proposal_agent.services.claude import ClaudeService, ClaudeServiceError
from proposal_agent.services.proposal import Proposal, PricingLineItem, TimelinePhase
from proposal_agent.utils.context import ContextStore, ConversationState
from tests.proposal.conftest import make_mock_bot, make_mock_message


def _sample_proposal_json() -> str:
    return Proposal(
        client_name="Test",
        project_title="App",
        executive_summary="Summary",
        scope_of_work=["Build"],
        deliverables=["App"],
        timeline=[TimelinePhase("P1", "2w", "Dev")],
        pricing=[PricingLineItem("Dev", 5000)],
        terms_and_conditions="Terms",
    ).to_json()


@pytest.fixture
def handler(config):
    bot = make_mock_bot()
    store = ContextStore()
    with patch("proposal_agent.services.claude.anthropic.Anthropic"):
        claude = ClaudeService(config)
    handler = ConversationHandler(bot, config, claude, store)
    return handler, store, bot


class TestIdleToGathering:
    @pytest.mark.asyncio
    async def test_transitions_to_gathering(self, handler):
        h, store, _ = handler
        msg = make_mock_message(content="I need a website")
        h._claude.gather_info = AsyncMock(return_value="What tech stack?")

        await h.handle_message(msg)

        ctx = store.get(msg.channel.id)
        assert ctx.state == ConversationState.GATHERING
        msg.channel.send.assert_called_with("What tech stack?")

    @pytest.mark.asyncio
    async def test_claude_error_resets_to_idle(self, handler):
        h, store, _ = handler
        msg = make_mock_message(content="I need a site")
        h._claude.gather_info = AsyncMock(side_effect=ClaudeServiceError("fail"))

        await h.handle_message(msg)

        ctx = store.get(msg.channel.id)
        assert ctx.state == ConversationState.IDLE


class TestGathering:
    @pytest.mark.asyncio
    async def test_stays_in_gathering(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.GATHERING

        msg = make_mock_message(content="React and Node")
        h._claude.gather_info = AsyncMock(return_value="What about timeline?")

        await h.handle_message(msg)
        assert ctx.state == ConversationState.GATHERING

    @pytest.mark.asyncio
    async def test_records_user_message(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.GATHERING

        msg = make_mock_message(content="React stack")
        h._claude.gather_info = AsyncMock(return_value="Got it.")

        await h.handle_message(msg)
        assert any(m.content == "React stack" for m in ctx.history)

    @pytest.mark.asyncio
    async def test_ready_sentinel_triggers_pricing(self, handler):
        h, store, bot = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.GATHERING

        h._claude.gather_info = AsyncMock(
            return_value=f"Got it! {READY_SENTINEL}"
        )

        pricing_reply = MagicMock()
        pricing_reply.content = "- Dev: $5000\nTotal: $5000"
        bot.wait_for = AsyncMock(return_value=pricing_reply)

        proposal_json = _sample_proposal_json()
        h._claude.generate_proposal = AsyncMock(
            return_value=Proposal.from_json(proposal_json)
        )

        msg = make_mock_message(content="4 weeks timeline")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.REVIEW


class TestWaitingForPricing:
    @pytest.mark.asyncio
    async def test_user_message_while_waiting(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.WAITING_FOR_PRICING

        msg = make_mock_message(content="How long?")
        await h.handle_message(msg)

        msg.channel.send.assert_called_with(
            "Still waiting on the pricing bot -- hang tight!"
        )
        assert ctx.state == ConversationState.WAITING_FOR_PRICING


class TestReview:
    @pytest.mark.asyncio
    async def test_approve_finalizes(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.REVIEW
        ctx.proposal_json = _sample_proposal_json()

        msg = make_mock_message(content="approve")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.FINALIZED

    @pytest.mark.asyncio
    async def test_cancel_resets(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.REVIEW
        ctx.proposal_json = _sample_proposal_json()

        msg = make_mock_message(content="cancel")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.IDLE

    @pytest.mark.asyncio
    async def test_revision_request(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.REVIEW
        ctx.proposal_json = _sample_proposal_json()

        revised = Proposal.from_json(ctx.proposal_json)
        revised.project_title = "Updated App"
        h._claude.revise_proposal = AsyncMock(return_value=revised)

        msg = make_mock_message(content="Change the title")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.REVIEW
        assert "Updated App" in ctx.proposal_json

    @pytest.mark.asyncio
    async def test_revision_error_stays_in_review(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.REVIEW
        ctx.proposal_json = _sample_proposal_json()

        h._claude.revise_proposal = AsyncMock(
            side_effect=ClaudeServiceError("fail")
        )

        msg = make_mock_message(content="Make it cheaper")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.REVIEW


class TestFinalized:
    @pytest.mark.asyncio
    async def test_new_message_starts_new_conversation(self, handler):
        h, store, _ = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.FINALIZED

        h._claude.gather_info = AsyncMock(return_value="What do you need?")

        msg = make_mock_message(content="New project")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.GATHERING


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_pricing_timeout_falls_back(self, handler):
        h, store, bot = handler
        ctx = store.get(123456789)
        ctx.state = ConversationState.GATHERING

        h._claude.gather_info = AsyncMock(
            return_value=f"Sounds good. {READY_SENTINEL}"
        )
        bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

        msg = make_mock_message(content="details")
        await h.handle_message(msg)

        assert ctx.state == ConversationState.GATHERING
        calls = [c[0][0] for c in msg.channel.send.call_args_list]
        assert any("didn't respond" in c for c in calls)
