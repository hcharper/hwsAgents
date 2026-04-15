"""Tracks API token usage and cost per agent."""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from loguru import logger

# Pricing per million tokens (as of 2026-04)
# https://docs.anthropic.com/en/docs/about-claude/models
MODEL_PRICING = {
    "claude-sonnet-4-5-20250929": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4-5-20251001": {
        "input": 0.80,
        "output": 4.00,
        "cache_write": 1.00,
        "cache_read": 0.08,
    },
}

# Fallback for unknown models
DEFAULT_PRICING = {
    "input": 3.00,
    "output": 15.00,
    "cache_write": 3.75,
    "cache_read": 0.30,
}


class UsageTracker:
    """Accumulates token usage per agent and calculates cost."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = Lock()
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                with open(self.path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load usage data, starting fresh")
        return {"agents": {}}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2)

    def record(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> None:
        """Record a single API call's token usage."""
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")

        with self._lock:
            agents = self._data.setdefault("agents", {})
            agent_data = agents.setdefault(agent, {})
            month = agent_data.setdefault(month_key, {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "model": model,
            })

            month["requests"] += 1
            month["input_tokens"] += input_tokens
            month["output_tokens"] += output_tokens
            month["cache_creation_tokens"] += cache_creation_tokens
            month["cache_read_tokens"] += cache_read_tokens
            month["model"] = model

            self._save()

        logger.debug(
            "Usage: agent={} in={} out={} cache_write={} cache_read={}",
            agent, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens,
        )

    def get_summary(self, month: str | None = None) -> dict:
        """Get usage summary for a specific month (default: current month).

        Returns dict with per-agent breakdown and totals.
        """
        if month is None:
            month = datetime.now(timezone.utc).strftime("%Y-%m")

        summary = {"month": month, "agents": {}, "total_cost": 0.0, "total_requests": 0}

        for agent_name, agent_data in self._data.get("agents", {}).items():
            if month not in agent_data:
                continue

            m = agent_data[month]
            pricing = MODEL_PRICING.get(m.get("model", ""), DEFAULT_PRICING)

            input_cost = (m["input_tokens"] / 1_000_000) * pricing["input"]
            output_cost = (m["output_tokens"] / 1_000_000) * pricing["output"]
            cache_write_cost = (m["cache_creation_tokens"] / 1_000_000) * pricing["cache_write"]
            cache_read_cost = (m["cache_read_tokens"] / 1_000_000) * pricing["cache_read"]
            total_cost = input_cost + output_cost + cache_write_cost + cache_read_cost

            summary["agents"][agent_name] = {
                "requests": m["requests"],
                "input_tokens": m["input_tokens"],
                "output_tokens": m["output_tokens"],
                "cache_creation_tokens": m["cache_creation_tokens"],
                "cache_read_tokens": m["cache_read_tokens"],
                "cost": round(total_cost, 4),
                "model": m.get("model", "unknown"),
            }
            summary["total_cost"] += total_cost
            summary["total_requests"] += m["requests"]

        summary["total_cost"] = round(summary["total_cost"], 4)
        return summary

    def format_summary(self, month: str | None = None) -> str:
        """Format usage summary as Discord markdown."""
        s = self.get_summary(month)

        if not s["agents"]:
            return f"No usage data for {s['month']}."

        lines = [f"**API Usage — {s['month']}**\n"]

        for agent, data in s["agents"].items():
            lines.append(
                f"**{agent}** ({data['model']})\n"
                f"  Requests: {data['requests']:,}\n"
                f"  Tokens: {data['input_tokens']:,} in / {data['output_tokens']:,} out\n"
                f"  Cache: {data['cache_read_tokens']:,} read / {data['cache_creation_tokens']:,} write\n"
                f"  Cost: **${data['cost']:.2f}**\n"
            )

        lines.append(f"**Total: ${s['total_cost']:.2f}** across {s['total_requests']:,} requests")
        return "\n".join(lines)
