from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from proposal_agent.handlers.pricing import (
    PricingParseError,
    PricingTimeoutError,
    build_pricing_request,
    parse_pricing_response,
    request_pricing,
    wait_for_pricing_response,
)
from tests.proposal.conftest import make_mock_bot


class TestBuildPricingRequest:
    def test_full_details(self):
        details = {
            "project_name": "Dashboard",
            "tech_stack": "React, Node",
            "features": "5 pages, auth",
            "timeline": "4 weeks",
        }
        result = build_pricing_request(details)
        assert "estimate for:" in result
        assert "- Project: Dashboard" in result
        assert "- Tech: React, Node" in result
        assert "- Pages/Features: 5 pages, auth" in result
        assert "- Timeline: 4 weeks" in result

    def test_partial_details(self):
        details = {"project_name": "App"}
        result = build_pricing_request(details)
        assert "- Project: App" in result
        assert "Tech" not in result

    def test_empty_details(self):
        result = build_pricing_request({})
        assert result == "estimate for:"


class TestParsePricingResponse:
    def test_standard_format(self):
        raw = (
            "Estimate for Dashboard:\n"
            "- Frontend Development: $8,000\n"
            "- Backend/API: $6,000\n"
            "- Testing & QA: $1,500\n"
            "Total: $15,500"
        )
        result = parse_pricing_response(raw)
        assert len(result.line_items) == 3
        assert result.line_items[0] == ("Frontend Development", 8000.0)
        assert result.total == 15500.0

    def test_bullet_variants(self):
        raw = (
            "• Design: $2,000\n"
            "* Development: $5,000\n"
            "Total: $7,000"
        )
        result = parse_pricing_response(raw)
        assert len(result.line_items) == 2
        assert result.total == 7000.0

    def test_no_explicit_total_sums_items(self):
        raw = (
            "- Dev: $3,000\n"
            "- QA: $1,000\n"
        )
        result = parse_pricing_response(raw)
        assert result.total == 4000.0

    def test_amounts_without_dollar_sign(self):
        raw = (
            "- Dev: 5000\n"
            "Total: 5000"
        )
        result = parse_pricing_response(raw)
        assert result.line_items[0][1] == 5000.0

    def test_amounts_with_cents(self):
        raw = "- Consulting: $1,234.56\nTotal: $1,234.56"
        result = parse_pricing_response(raw)
        assert result.line_items[0][1] == 1234.56

    def test_unparseable_raises(self):
        with pytest.raises(PricingParseError):
            parse_pricing_response("No pricing info here at all.")

    def test_raw_text_preserved(self):
        raw = "- Dev: $1000\nTotal: $1000"
        result = parse_pricing_response(raw)
        assert result.raw_text == raw


@pytest.mark.asyncio
class TestRequestPricing:
    async def test_sends_mention_message(self, config):
        channel = MagicMock()
        channel.send = AsyncMock()
        await request_pricing(channel, config, {"project_name": "App"})
        channel.send.assert_called_once()
        sent = channel.send.call_args[0][0]
        assert f"<@{config.pricing_bot_id}>" in sent
        assert "Project: App" in sent


@pytest.mark.asyncio
class TestWaitForPricingResponse:
    async def test_returns_content_on_reply(self, config):
        bot = make_mock_bot()
        reply = MagicMock()
        reply.content = "- Dev: $5000\nTotal: $5000"
        bot.wait_for = AsyncMock(return_value=reply)

        result = await wait_for_pricing_response(bot, 123456789, config)
        assert result == "- Dev: $5000\nTotal: $5000"

    async def test_timeout_raises(self, config):
        bot = make_mock_bot()
        bot.wait_for = AsyncMock(side_effect=asyncio.TimeoutError)

        with pytest.raises(PricingTimeoutError):
            await wait_for_pricing_response(bot, 123456789, config)
