"""Punkt wejscia: bot koordynator."""
from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from config import Settings
from core.cluster import Agent, Cluster
from core.engine import AttackEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
log = logging.getLogger("bot")

COGS = ("cogs.attack", "cogs.info")


class DDoSBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        self.settings = settings
        agents = [Agent(n, u, settings.agent_token, w) for n, u, w in settings.agents]
        self.cluster = Cluster(agents)
        self.engine = AttackEngine(settings, self.cluster)
        self.panels: dict[str, discord.ui.LayoutView] = {}
        self.history: dict[str, list[float]] = {}

    async def setup_hook(self) -> None:
        await self.cluster.start()
        for cog in COGS:
            await self.load_extension(cog)
        if self.settings.guild_id:
            g = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=g)
            await self.tree.sync(guild=g)
        else:
            await self.tree.sync()
        log.info("gotowe, agentow: %d", len(self.cluster.agents))

    async def on_ready(self) -> None:
        log.info("zalogowano %s", self.user)

    async def close(self) -> None:
        await self.cluster.close()
        await super().close()


async def main() -> None:
    s = Settings.load()
    async with DDoSBot(s) as bot:
        await bot.start(s.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
