from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


class ConfigError(Exception):
    """Raised when a required configuration value is missing."""


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    anthropic_api_key: str
    proposal_channel_id: int
    pricing_bot_id: int
    claude_model: str = "claude-sonnet-4-20250514"
    pricing_timeout_seconds: int = 60

    @classmethod
    def from_env(cls, env_path: str | None = None) -> Config:
        """Load configuration from environment variables.

        Parameters
        ----------
        env_path:
            Optional path to a ``.env`` file.  When *None* the default
            ``dotenv`` search is used.
        """
        load_dotenv(env_path)

        def _require(name: str) -> str:
            value = os.getenv(name)
            if not value:
                raise ConfigError(
                    f"Missing required environment variable: {name}"
                )
            return value

        return cls(
            discord_bot_token=_require("DISCORD_BOT_TOKEN"),
            anthropic_api_key=_require("ANTHROPIC_API_KEY"),
            proposal_channel_id=int(_require("PROPOSAL_CHANNEL_ID")),
            pricing_bot_id=int(_require("PRICING_BOT_ID")),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            pricing_timeout_seconds=int(
                os.getenv("PRICING_TIMEOUT_SECONDS", "60")
            ),
        )
