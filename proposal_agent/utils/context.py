from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ConversationState(enum.Enum):
    IDLE = "idle"
    GATHERING = "gathering"
    WAITING_FOR_PRICING = "waiting_for_pricing"
    DRAFTING = "drafting"
    REVIEW = "review"
    FINALIZED = "finalized"


@dataclass
class Message:
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ConversationContext:
    channel_id: int
    state: ConversationState = ConversationState.IDLE
    history: list[Message] = field(default_factory=list)
    project_details: dict[str, Any] = field(default_factory=dict)
    pricing_data: str | None = None
    proposal_json: str | None = None

    def add_user_message(self, content: str) -> None:
        self.history.append(Message(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        self.history.append(Message(role="assistant", content=content))

    def get_messages_for_api(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.history]

    def reset(self) -> None:
        self.state = ConversationState.IDLE
        self.history.clear()
        self.project_details.clear()
        self.pricing_data = None
        self.proposal_json = None


class ContextStore:
    """In-memory store keyed by channel / thread ID."""

    def __init__(self) -> None:
        self._store: dict[int, ConversationContext] = {}

    def get(self, channel_id: int) -> ConversationContext:
        if channel_id not in self._store:
            self._store[channel_id] = ConversationContext(
                channel_id=channel_id
            )
        return self._store[channel_id]

    def remove(self, channel_id: int) -> None:
        self._store.pop(channel_id, None)
