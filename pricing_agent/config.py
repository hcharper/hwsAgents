"""Pricing agent configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pricing agent settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Discord
    pricing_bot_token: SecretStr = Field(..., description="Discord bot token for pricing agent")
    pricing_channel_ids: str = Field(..., description="Comma-separated channel IDs to listen in")

    # Cross-bot references (Discord user IDs of other bots)
    proposal_bot_id: int | None = Field(None, description="Proposal bot's Discord user ID for @mentions")

    # Anthropic
    anthropic_api_key: SecretStr = Field(..., description="Anthropic API key")
    anthropic_model: str = Field("claude-sonnet-4-5-20250929", description="Claude model ID")

    # App
    log_level: str = Field("INFO")
    data_dir: Path = Field(Path("data"), description="Path to shared YAML data files")
    max_history: int = Field(40, description="Max messages per channel in memory")

    @property
    def channel_ids(self) -> list[int]:
        return [int(x.strip()) for x in self.pricing_channel_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
