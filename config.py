"""Konfiguracja - z .env, zero hardkodu."""
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    guild_id: int | None
    max_duration: int
    max_concurrency: int
    agent_token: str
    agents: list[tuple[str, str, int]] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Settings":
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise RuntimeError("Brak DISCORD_TOKEN w .env")
        guild = os.getenv("GUILD_ID", "").strip()
        agents: list[tuple[str, str, int]] = []
        for raw in os.getenv("AGENTS", "").split(";"):
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split("|")
            if len(parts) < 2:
                continue
            name, url = parts[0], parts[1]
            weight = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
            agents.append((name, url, weight))
        return cls(
            token=token,
            guild_id=int(guild) if guild.isdigit() else None,
            max_duration=_int("MAX_DURATION", 300),
            max_concurrency=_int("MAX_CONCURRENCY", 1000),
            agent_token=os.getenv("AGENT_TOKEN", ""),
            agents=agents,
        )
