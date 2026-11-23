"""Info + zarzadzanie agentami."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.format import human


class InfoCog(commands.Cog, name="Info"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Opóznienie bota")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"\U0001f3d3 {self.bot.latency * 1000:.0f} ms")

    @app_commands.command(name="agenci", description="Stan klastra")
    async def agenci(self, interaction: discord.Interaction) -> None:
        c = self.bot.cluster  # type: ignore[attr-defined]
        e = discord.Embed(
            title=f"Klaster \u2014 {len(c.online)}/{len(c.agents)} online",
            color=discord.Color.green() if c.online else discord.Color.red(),
        )
        for a in c.agents:
            icon = "\U0001f7e2" if a.alive else "\U0001f534"
            e.add_field(
                name=f"{icon} {a.name}",
                value=f"{a.url}\nwaga {a.weight} \u00b7 {a.latency_ms:.0f} ms",
                inline=True,
            )
        e.set_footer(text=f"Suma wag: {c.total_weight}")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="info", description="Informacje o bocie")
    async def info(self, interaction: discord.Interaction) -> None:
        c = self.bot.cluster  # type: ignore[attr-defined]
        e = discord.Embed(title="EP DDoS \u2014 klaster", color=discord.Color.blurple())
        e.add_field(name="Agenci", value=f"{len(c.online)} online", inline=True)
        e.add_field(name="Suma wag", value=str(c.total_weight), inline=True)
        e.add_field(name="Aktywne", value=str(len(self.bot.engine.active)), inline=True)  # type: ignore[attr-defined]
        e.set_footer(text="Rozproszony HTTP flood")
        await interaction.response.send_message(embed=e)

    @app_commands.command(name="pomoc", description="Jak uzywac")
    async def pomoc(self, interaction: discord.Interaction) -> None:
        e = discord.Embed(title="Pomoc", color=discord.Color.green())
        e.description = (
            "`/start url [czas] [watki] [metoda]` \u2014 start\n"
            "`/stop id` \u2014 stop\n`/status id` \u2014 podglad\n"
            "`/lista` \u2014 aktywne\n`/agenci` \u2014 klaster\n"
            "`/ping` `/info` \u2014 diagnostyka\n\n"
            "Watki sa rozdzielane miedzy agentow proporcjonalnie do wagi."
        )
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(InfoCog(bot))
