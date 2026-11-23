"""Widoki: panel ataku, wybor agentow, potwierdzenia."""
from __future__ import annotations

import discord

from utils.format import bar, bytes_h, duration_h, human, spark


class AttackPanel(discord.ui.LayoutView):
    """Glowny panel ataku - komponenty v2."""

    def __init__(self, attack, history: list[float]) -> None:
        super().__init__(timeout=None)
        self.attack = attack
        self.history = history
        self._build()

    def _build(self) -> None:
        a = self.attack
        s = a.stats
        progress = min(s.elapsed / a.duration * 100, 100)
        color = {"running": 0x2ECC71, "stopped": 0xE67E22,
                 "finished": 0x3498DB, "failed": 0xE74C3C}.get(a.state, 0x95A5A6)

        container = discord.ui.Container(accent_color=discord.Color(color))
        container.add_item(discord.ui.TextDisplay(
            f"## {a.state.upper()}  \u00b7  `{a.id}`\n"
            f"**Cel:** `{a.target.url}`\n"
            f"**Metoda:** `{a.target.method}`  \u00b7  **Watki:** {a.concurrency}  \u00b7  **Agenci:** {a.agents}"
        ))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(
            f"`{bar(progress)}` **{progress:.0f}%**  \u00b7  {duration_h(s.elapsed)} / {duration_h(a.duration)}"
        ))
        if self.history:
            container.add_item(discord.ui.TextDisplay(f"RPS: `{spark(self.history)}`"))
        container.add_item(discord.ui.Separator())

        row = discord.ui.ActionRow()
        row.add_item(_Stat(f"Wyslane\n{human(s.sent)}"))
        row.add_item(_Stat(f"RPS\n{human(s.rps)}"))
        row.add_item(_Stat(f"Bledy\n{s.error_rate:.1f}%"))
        row.add_item(_Stat(f"Latencja\n{s.avg_latency:.0f}ms"))
        row.add_item(_Stat(f"Pobrano\n{bytes_h(s.bytes_in)}"))
        container.add_item(row)

        if s.codes:
            top = "  ".join(f"`{c}`\u00d7{n}" for c, n in sorted(s.codes.items(), key=lambda x: -x[1])[:6])
            container.add_item(discord.ui.TextDisplay(f"**Kody:** {top}"))

        container.add_item(discord.ui.Separator())
        btns = discord.ui.ActionRow()
        btns.add_item(_StopButton(a.id))
        btns.add_item(_RefreshButton(a.id))
        container.add_item(btns)

        self.add_item(container)


class _Stat(discord.ui.TextDisplay):
    def __init__(self, text: str) -> None:
        super().__init__(text)


class _StopButton(discord.ui.Button):
    def __init__(self, attack_id: str) -> None:
        super().__init__(label="Stop", emoji="\u23f9", style=discord.ButtonStyle.danger, custom_id=f"stop:{attack_id}")

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        await bot.engine.stop(self.custom_id.split(":", 1)[1])
        await interaction.response.send_message("\u23f9 Zatrzymano", ephemeral=True)


class _RefreshButton(discord.ui.Button):
    def __init__(self, attack_id: str) -> None:
        super().__init__(label="Odswiez", emoji="\U0001f504", style=discord.ButtonStyle.secondary, custom_id=f"ref:{attack_id}")

    async def callback(self, interaction: discord.Interaction) -> None:
        bot = interaction.client
        attack = bot.engine.get(self.custom_id.split(":", 1)[1])
        if not attack:
            await interaction.response.send_message("Atak zakonczony", ephemeral=True)
            return
        await interaction.response.edit_message(
            view=AttackPanel(attack, bot.history.get(attack.id, []))
        )
