from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from proposal_agent.services.claude import ClaudeService, ClaudeServiceError


def _make_api_response(text: str) -> MagicMock:
    resp = MagicMock()
    block = MagicMock()
    block.text = text
    resp.content = [block]
    return resp


@pytest.fixture
def claude_service(config):
    with patch("proposal_agent.services.claude.anthropic.Anthropic") as mock_cls:
        svc = ClaudeService(config)
        svc._client = mock_cls.return_value
        yield svc


class TestGatherInfo:
    @pytest.mark.asyncio
    async def test_returns_assistant_text(self, claude_service):
        claude_service._client.messages.create.return_value = _make_api_response(
            "What tech stack are you considering?"
        )
        result = await claude_service.gather_info(
            [{"role": "user", "content": "I need an e-commerce site"}]
        )
        assert "tech stack" in result.lower()

    @pytest.mark.asyncio
    async def test_ready_sentinel_in_response(self, claude_service):
        claude_service._client.messages.create.return_value = _make_api_response(
            "Great, I have enough info. [READY_FOR_PRICING]"
        )
        result = await claude_service.gather_info(
            [{"role": "user", "content": "React, Node, 4 weeks"}]
        )
        assert "[READY_FOR_PRICING]" in result


class TestGenerateProposal:
    @pytest.mark.asyncio
    async def test_parses_proposal_json(self, claude_service):
        proposal_json = json.dumps(
            {
                "client_name": "Test Co",
                "project_title": "Test App",
                "executive_summary": "A test proposal.",
                "scope_of_work": ["Build thing"],
                "deliverables": ["The thing"],
                "timeline": [
                    {"name": "Phase 1", "duration": "2 weeks", "description": "Build"}
                ],
                "pricing": [{"description": "Dev", "amount": 5000}],
                "terms_and_conditions": "Standard terms",
                "notes": "",
            }
        )
        claude_service._client.messages.create.return_value = _make_api_response(
            f"Here is the proposal:\n```json\n{proposal_json}\n```"
        )
        proposal = await claude_service.generate_proposal(
            [{"role": "user", "content": "details"}],
            "- Dev: $5000\nTotal: $5000",
        )
        assert proposal.client_name == "Test Co"
        assert proposal.total_price == 5000.0

    @pytest.mark.asyncio
    async def test_missing_json_block_raises(self, claude_service):
        claude_service._client.messages.create.return_value = _make_api_response(
            "Here is the proposal but I forgot the JSON."
        )
        with pytest.raises(ClaudeServiceError, match="JSON code block"):
            await claude_service.generate_proposal(
                [{"role": "user", "content": "details"}],
                "- Dev: $5000",
            )

    @pytest.mark.asyncio
    async def test_invalid_json_raises(self, claude_service):
        claude_service._client.messages.create.return_value = _make_api_response(
            "```json\n{invalid json}\n```"
        )
        with pytest.raises(ClaudeServiceError, match="Invalid JSON"):
            await claude_service.generate_proposal(
                [{"role": "user", "content": "details"}],
                "- Dev: $5000",
            )


class TestReviseProposal:
    @pytest.mark.asyncio
    async def test_returns_updated_proposal(self, claude_service):
        updated = json.dumps(
            {
                "client_name": "Test Co",
                "project_title": "Test App v2",
                "executive_summary": "Updated summary.",
                "scope_of_work": ["Build thing", "Extra thing"],
                "deliverables": ["The thing"],
                "timeline": [
                    {"name": "Phase 1", "duration": "3 weeks", "description": "Build more"}
                ],
                "pricing": [{"description": "Dev", "amount": 7000}],
                "terms_and_conditions": "Standard terms",
                "notes": "",
            }
        )
        claude_service._client.messages.create.return_value = _make_api_response(
            f"```json\n{updated}\n```"
        )
        proposal = await claude_service.revise_proposal(
            [{"role": "user", "content": "details"}],
            "Make the timeline longer",
            '{"old": "proposal"}',
        )
        assert proposal.project_title == "Test App v2"
        assert proposal.total_price == 7000.0


class TestApiError:
    @pytest.mark.asyncio
    async def test_api_error_wrapped(self, claude_service):
        import anthropic

        claude_service._client.messages.create.side_effect = anthropic.APIError(
            message="rate limit", request=MagicMock(), body=None
        )
        with pytest.raises(ClaudeServiceError):
            await claude_service.gather_info(
                [{"role": "user", "content": "hello"}]
            )


class TestHistoryTrimming:
    @pytest.mark.asyncio
    async def test_long_history_is_trimmed(self, claude_service):
        claude_service._client.messages.create.return_value = _make_api_response("ok")
        long_history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"}
            for i in range(100)
        ]
        await claude_service.gather_info(long_history)
        call_args = claude_service._client.messages.create.call_args
        sent_messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert len(sent_messages) <= 40
