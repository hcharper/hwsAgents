from __future__ import annotations

import discord
import pytest

from proposal_agent.templates.proposal_embed import (
    EMBED_COLOR,
    FIELD_CHAR_LIMIT,
    _truncate,
    build_proposal_embed,
)
from proposal_agent.services.proposal import Proposal, PricingLineItem, TimelinePhase


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_long_string_truncated(self):
        long = "a" * 2000
        result = _truncate(long)
        assert len(result) == FIELD_CHAR_LIMIT
        assert result.endswith("...")

    def test_exact_limit_unchanged(self):
        exact = "x" * FIELD_CHAR_LIMIT
        assert _truncate(exact) == exact


class TestBuildProposalEmbed:
    def test_returns_embed(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        assert isinstance(embed, discord.Embed)

    def test_embed_title(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        assert sample_proposal.project_title in embed.title

    def test_embed_color(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        assert embed.color.value == EMBED_COLOR

    def test_embed_author(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        assert sample_proposal.client_name in embed.author.name

    def test_embed_has_expected_fields(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        field_names = [f.name for f in embed.fields]
        assert "Date" in field_names
        assert "Total" in field_names
        assert "Scope of Work" in field_names
        assert "Deliverables" in field_names
        assert "Timeline" in field_names
        assert "Pricing" in field_names

    def test_embed_footer(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        assert "PDF" in embed.footer.text

    def test_pricing_field_contains_total(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        pricing_field = next(f for f in embed.fields if f.name == "Pricing")
        assert sample_proposal.formatted_total in pricing_field.value

    def test_all_fields_within_char_limit(self, sample_proposal):
        embed = build_proposal_embed(sample_proposal)
        for f in embed.fields:
            assert len(f.value) <= FIELD_CHAR_LIMIT

    def test_long_scope_truncated(self):
        proposal = Proposal(
            client_name="X",
            project_title="Y",
            executive_summary="Z",
            scope_of_work=["Item " + str(i) + " " + "x" * 100 for i in range(50)],
            deliverables=["d"],
            timeline=[],
            pricing=[PricingLineItem("Dev", 1000)],
            terms_and_conditions="",
        )
        embed = build_proposal_embed(proposal)
        scope_field = next(f for f in embed.fields if f.name == "Scope of Work")
        assert len(scope_field.value) <= FIELD_CHAR_LIMIT
