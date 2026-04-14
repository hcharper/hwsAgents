"""Pricing agent Discord bot."""

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

    async def on_ready(self) -> None:
        logger.info("Pricing bot logged in as {} ({})", self.user.name, self.user.id)
        logger.info("Listening in channels: {}", self.channel_ids)

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        if message.channel.id in self.channel_ids:
            await self.handler.handle(message)
