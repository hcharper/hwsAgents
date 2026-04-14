from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from proposal_agent.config import Config, ConfigError


VALID_ENV = {
    "DISCORD_BOT_TOKEN": "test-token-abc",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "PROPOSAL_CHANNEL_ID": "123456789",
    "PRICING_BOT_ID": "987654321",
}


class TestConfigFromEnv:
    @patch.dict(os.environ, VALID_ENV, clear=True)
    def test_loads_all_required_vars(self):
        cfg = Config.from_env(env_path="/dev/null")
        assert cfg.discord_bot_token == "test-token-abc"
        assert cfg.anthropic_api_key == "sk-ant-test"
        assert cfg.proposal_channel_id == 123456789
        assert cfg.pricing_bot_id == 987654321

    @patch.dict(os.environ, VALID_ENV, clear=True)
    def test_default_claude_model(self):
        cfg = Config.from_env(env_path="/dev/null")
        assert cfg.claude_model == "claude-sonnet-4-20250514"

    @patch.dict(os.environ, VALID_ENV, clear=True)
    def test_default_pricing_timeout(self):
        cfg = Config.from_env(env_path="/dev/null")
        assert cfg.pricing_timeout_seconds == 60

    @patch.dict(
        os.environ,
        {**VALID_ENV, "CLAUDE_MODEL": "claude-opus-latest", "PRICING_TIMEOUT_SECONDS": "120"},
        clear=True,
    )
    def test_custom_optional_values(self):
        cfg = Config.from_env(env_path="/dev/null")
        assert cfg.claude_model == "claude-opus-latest"
        assert cfg.pricing_timeout_seconds == 120

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_discord_token_raises(self):
        with pytest.raises(ConfigError, match="DISCORD_BOT_TOKEN"):
            Config.from_env(env_path="/dev/null")

    @patch.dict(
        os.environ,
        {"DISCORD_BOT_TOKEN": "tok"},
        clear=True,
    )
    def test_missing_anthropic_key_raises(self):
        with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
            Config.from_env(env_path="/dev/null")

    @patch.dict(
        os.environ,
        {"DISCORD_BOT_TOKEN": "tok", "ANTHROPIC_API_KEY": "key"},
        clear=True,
    )
    def test_missing_channel_id_raises(self):
        with pytest.raises(ConfigError, match="PROPOSAL_CHANNEL_ID"):
            Config.from_env(env_path="/dev/null")

    @patch.dict(
        os.environ,
        {
            "DISCORD_BOT_TOKEN": "tok",
            "ANTHROPIC_API_KEY": "key",
            "PROPOSAL_CHANNEL_ID": "123",
        },
        clear=True,
    )
    def test_missing_pricing_bot_id_raises(self):
        with pytest.raises(ConfigError, match="PRICING_BOT_ID"):
            Config.from_env(env_path="/dev/null")

    @patch.dict(os.environ, VALID_ENV, clear=True)
    def test_config_is_frozen(self):
        cfg = Config.from_env(env_path="/dev/null")
        with pytest.raises(AttributeError):
            cfg.discord_bot_token = "changed"
