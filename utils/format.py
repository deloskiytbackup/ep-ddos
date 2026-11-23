"""Formatowanie: embedy, paski, wykresy, liczby."""
from __future__ import annotations

import discord

BAR_FULL = "\u2588"
BAR_EMPTY = "\u2591"
SPARK = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


COLORS = {
    "running": discord.Color.from_rgb(46, 204, 113),
    "stopped": discord.Color.from_rgb(230, 126, 34),
    "finished": discord.Color.from_rgb(52, 152, 219),
    "failed": discord.Color.from_rgb(231, 76, 60),
}


def bar(percent: float, width: int = 20) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = round(width * percent / 100)
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


def spark(values: list[float]) -> str:
    if not values:
        return ""
    peak = max(values) or 1
    return "".join(SPARK[min(len(SPARK) - 1, int(v / peak * (len(SPARK) - 1)))] for v in values)


def human(n: float) -> str:
    n = float(n)
    for unit in ("", "k", "M", "G"):
        if abs(n) < 999.95:
            return (f"{n:.1f}" if n % 1 else f"{n:.0f}") + unit
        n /= 1000
    return f"{n:.1f}T"


def bytes_h(n: float) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def duration_h(sec: float) -> str:
    sec = int(sec)
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m {sec % 60}s"
    return f"{sec // 3600}h {(sec % 3600) // 60}m"
