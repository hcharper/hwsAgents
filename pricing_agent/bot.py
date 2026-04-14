"""Pricing agent Discord bot."""

from datetime import datetime, timezone

import discord
from loguru import logger

from pricing_agent.handler import PricingHandler


class PricingBot(discord.Client):
    """Discord bot for the pricing agent."""

    def __init__(self, channel_ids: list[int], handler: PricingHandler):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

        self.channel_ids = set(channel_ids)
        self.handler = handler
        self._ready_at: datetime | None = None

    async def on_ready(self) -> None:
        self._ready_at = datetime.now(timezone.utc)
        logger.info("Pricing bot logged in as {} ({})", self.user.name, self.user.id)
        logger.info("Listening in channels: {}", self.channel_ids)

        # Ensure each channel has a pinned welcome message
        for ch_id in self.channel_ids:
            channel = self.get_channel(ch_id)
            if channel:
                await self._ensure_pinned_welcome(channel)

    async def _ensure_pinned_welcome(self, channel: discord.TextChannel) -> None:
        """Pin a welcome message if one doesn't already exist."""
        try:
            pins = await channel.pins()
            if any(p.author == self.user for p in pins):
                return

            msg = await channel.send(
                "**HWS Pricing Agent**\n"
                "Describe your client's needs and answer any follow-up questions to receive a quote.\n\n"
                "**Commands:**\n"
                "`/clear` — wipe all messages and start fresh"
            )
            await msg.pin()
            # Delete the "pinned a message" system notification
            async for m in channel.history(limit=3):
                if m.type == discord.MessageType.pins_add:
                    await m.delete()
                    break
            logger.info("Pinned welcome message in #{}", channel.name)
        except Exception:
            logger.exception("Failed to pin welcome message")

    async def on_message(self, message: discord.Message) -> None:
        # Ignore own messages and other bots
        if message.author == self.user or message.author.bot:
            return

        # Ignore messages sent before bot was ready (backlog on reconnect)
        if self._ready_at and message.created_at < self._ready_at:
            return

        if message.channel.id in self.channel_ids:
            await self.handler.handle(message)
