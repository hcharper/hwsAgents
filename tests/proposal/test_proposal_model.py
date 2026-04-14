from __future__ import annotations

import json

import pytest

from proposal_agent.services.proposal import Proposal, PricingLineItem, TimelinePhase


class TestPricingLineItem:
    def test_formatted_amount(self):
        item = PricingLineItem(description="Dev", amount=8000)
        assert item.formatted_amount() == "$8,000.00"

    def test_formatted_amount_cents(self):
        item = PricingLineItem(description="Dev", amount=1234.56)
        assert item.formatted_amount() == "$1,234.56"


class TestProposal:
    def test_total_price(self, sample_proposal):
        assert sample_proposal.total_price == 21000.0

    def test_formatted_total(self, sample_proposal):
        assert sample_proposal.formatted_total == "$21,000.00"

    def test_to_dict_roundtrip(self, sample_proposal):
        d = sample_proposal.to_dict()
        restored = Proposal.from_dict(d)
        assert restored.client_name == sample_proposal.client_name
        assert restored.total_price == sample_proposal.total_price
        assert len(restored.pricing) == len(sample_proposal.pricing)
        assert len(restored.timeline) == len(sample_proposal.timeline)

    def test_to_json_roundtrip(self, sample_proposal):
        raw = sample_proposal.to_json()
        restored = Proposal.from_json(raw)
        assert restored.project_title == sample_proposal.project_title
        assert restored.total_price == sample_proposal.total_price

    def test_json_is_valid(self, sample_proposal):
        raw = sample_proposal.to_json()
        data = json.loads(raw)
        assert data["client_name"] == "Acme Corp"
        assert isinstance(data["pricing"], list)

    def test_from_dict_converts_nested_dicts(self):
        data = {
            "client_name": "Test",
            "project_title": "Test Project",
            "executive_summary": "Summary",
            "scope_of_work": ["item"],
            "deliverables": ["thing"],
            "timeline": [{"name": "Phase 1", "duration": "1 week", "description": "stuff"}],
            "pricing": [{"description": "Dev", "amount": 1000}],
            "terms_and_conditions": "Terms",
        }
        p = Proposal.from_dict(data)
        assert isinstance(p.timeline[0], TimelinePhase)
        assert isinstance(p.pricing[0], PricingLineItem)
        assert p.pricing[0].amount == 1000

    def test_empty_pricing_totals_zero(self):
        p = Proposal(
            client_name="X",
            project_title="Y",
            executive_summary="Z",
            scope_of_work=[],
            deliverables=[],
            timeline=[],
            pricing=[],
            terms_and_conditions="",
        )
        assert p.total_price == 0.0
        assert p.formatted_total == "$0.00"

    def test_date_default_is_today(self):
        p = Proposal(
            client_name="X",
            project_title="Y",
            executive_summary="Z",
            scope_of_work=[],
            deliverables=[],
            timeline=[],
            pricing=[],
            terms_and_conditions="",
        )
        assert len(p.date) == 10  # ISO format YYYY-MM-DD
