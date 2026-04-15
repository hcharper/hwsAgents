"""Pricing agent entrypoint."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(level: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> - {message}",
    )


def main() -> None:
    from pricing_agent.config import get_settings

    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting HWS Pricing Agent")

    # Resolve data dir
    data_dir = settings.data_dir
    if not data_dir.is_absolute():
        data_dir = Path(__file__).parent.parent / data_dir

    from shared.data_manager import DataManager
    dm = DataManager(data_dir)
    dm.load()

    # Set up usage tracker
    from shared.usage_tracker import UsageTracker
    from shared.llm import set_tracker
    set_tracker(UsageTracker(data_dir / "usage.json"))

    from shared.llm import create_client
    client = create_client(settings.anthropic_api_key.get_secret_value())

    from shared.memory import ChannelMemory
    memory = ChannelMemory(max_messages=settings.max_history)

    from pricing_agent.handler import PricingHandler
    handler = PricingHandler(
        client=client,
        model=settings.anthropic_model,
        memory=memory,
        data_manager=dm,
        proposal_bot_id=settings.proposal_bot_id,
    )

    from pricing_agent.bot import PricingBot
    bot = PricingBot(
        channel_ids=settings.channel_ids,
        handler=handler,
    )

    logger.info("Connecting to Discord...")
    bot.run(settings.pricing_bot_token.get_secret_value(), log_handler=None)


if __name__ == "__main__":
    main()
