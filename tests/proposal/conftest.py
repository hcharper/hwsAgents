from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from proposal_agent.config import Config
from proposal_agent.services.proposal import (
    Proposal,
    PricingLineItem,
    TimelinePhase,
)
from proposal_agent.utils.context import ContextStore


@pytest.fixture
def config() -> Config:
    return Config(
        discord_bot_token="test-token",
        anthropic_api_key="test-key",
        proposal_channel_id=123456789,
        pricing_bot_id=987654321,
        claude_model="claude-sonnet-4-20250514",
        pricing_timeout_seconds=5,
    )


@pytest.fixture
def context_store() -> ContextStore:
    return ContextStore()


def make_mock_message(
    content: str = "hello",
    author_id: int = 111,
    channel_id: int = 123456789,
    bot: bool = False,
) -> MagicMock:
    """Create a fake ``discord.Message``."""
    msg = MagicMock()
    msg.content = content
    msg.author.id = author_id
    msg.author.bot = bot
    msg.channel.id = channel_id
    msg.channel.send = AsyncMock()
    return msg


def make_mock_bot(user_id: int = 999) -> MagicMock:
    """Create a fake ``discord.Client`` with a user attached."""
    client = MagicMock()
    client.user = MagicMock()
    client.user.id = user_id
    client.wait_for = AsyncMock()
    return client


@pytest.fixture
def sample_proposal() -> Proposal:
    return Proposal(
        client_name="Acme Corp",
        project_title="E-commerce Dashboard",
        executive_summary=(
            "This proposal outlines the development of a modern e-commerce "
            "dashboard for Acme Corp.\n\n"
            "The platform will provide real-time analytics, inventory "
            "management, and order processing capabilities."
        ),
        scope_of_work=[
            "Frontend development with React and TypeScript",
            "REST API with Node.js and Express",
            "PostgreSQL database design and implementation",
            "Authentication and role-based access control",
            "Payment gateway integration (Stripe)",
        ],
        deliverables=[
            "Deployed web application",
            "API documentation",
            "Admin dashboard",
            "Source code repository",
            "Deployment guide",
        ],
        timeline=[
            TimelinePhase(
                name="Discovery & Design",
                duration="2 weeks",
                description="Requirements gathering and UI/UX design",
            ),
            TimelinePhase(
                name="Core Development",
                duration="4 weeks",
                description="Frontend and backend implementation",
            ),
            TimelinePhase(
                name="Testing & Launch",
                duration="2 weeks",
                description="QA, bug fixes, and production deployment",
            ),
        ],
        pricing=[
            PricingLineItem(description="Frontend Development", amount=8000),
            PricingLineItem(description="Backend/API", amount=6000),
            PricingLineItem(description="Database & Auth", amount=3000),
            PricingLineItem(description="Payment Integration", amount=2500),
            PricingLineItem(description="Testing & QA", amount=1500),
        ],
        terms_and_conditions=(
            "Payment is due in three installments: 30% upfront, 40% at "
            "midpoint, and 30% on delivery. All source code is transferred "
            "to the client upon final payment."
        ),
        notes="Timeline assumes timely feedback from the client.",
        date="2026-04-14",
    )
