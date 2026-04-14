from __future__ import annotations

import logging
import sys

from proposal_agent.client import ProposalBot
from proposal_agent.config import Config, ConfigError


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        config = Config.from_env()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    bot = ProposalBot(config)
    logger.info("Starting Proposal Bot (model=%s)...", config.claude_model)
    bot.run(config.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
