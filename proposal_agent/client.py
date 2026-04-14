from __future__ import annotations

import logging

import discord

from proposal_agent.config import Config
from proposal_agent.handlers.conversation import ConversationHandler
from proposal_agent.services.claude import ClaudeService
from proposal_agent.utils.context import ContextStore

logger = logging.getLogger(__name__)


class ProposalBot(discord.Client):
    """Discord client wired to the proposal conversation handler."""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.config = config
        self._store = ContextStore()
        self._claude = ClaudeService(config)
        self._handler = ConversationHandler(
            bot=self,
            config=config,
            claude=self._claude,
            store=self._store,
        )

    async def on_ready(self) -> None:
        logger.info("Proposal bot logged in as %s (id=%s)", self.user, self.user.id)
        channel = self.get_channel(self.config.proposal_channel_id)
        if channel is None:
            logger.warning(
                "Could not find channel %s — the bot may not have access.",
                self.config.proposal_channel_id,
            )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.id == self.user.id:
            return

        if message.channel.id != self.config.proposal_channel_id:
            return

        # Allow pricing bot replies through (handled by wait_for),
        # but ignore all other bots.
        if message.author.bot and message.author.id != self.config.pricing_bot_id:
            return

        # Pricing bot messages are consumed by wait_for; don't feed them
        # into the conversation handler.
        if message.author.id == self.config.pricing_bot_id:
            return

        logger.debug(
            "Processing message from %s: %s",
            message.author,
            message.content[:80],
        )
        try:
            await self._handler.handle_message(message)
        except Exception:
            logger.exception("Unhandled error processing message")
            await message.channel.send(
                "Something went wrong on my end. Please try again."
            )
