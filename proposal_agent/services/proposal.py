from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any


@dataclass
class PricingLineItem:
    description: str
    amount: float

    def formatted_amount(self) -> str:
        return f"${self.amount:,.2f}"


@dataclass
class TimelinePhase:
    name: str
    duration: str
    description: str = ""


@dataclass
class Proposal:
    client_name: str
    project_title: str
    executive_summary: str
    scope_of_work: list[str]
    deliverables: list[str]
    timeline: list[TimelinePhase]
    pricing: list[PricingLineItem]
    terms_and_conditions: str
    notes: str = ""
    date: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def total_price(self) -> float:
        return sum(item.amount for item in self.pricing)

    @property
    def formatted_total(self) -> str:
        return f"${self.total_price:,.2f}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Proposal:
        data = dict(data)
        data["timeline"] = [
            TimelinePhase(**phase) if isinstance(phase, dict) else phase
            for phase in data.get("timeline", [])
        ]
        data["pricing"] = [
            PricingLineItem(**item) if isinstance(item, dict) else item
            for item in data.get("pricing", [])
        ]
        return cls(**data)

    @classmethod
    def from_json(cls, raw: str) -> Proposal:
        return cls.from_dict(json.loads(raw))
