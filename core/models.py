"""Modele: cel, statystyki, atak."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class AttackState(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FINISHED = "finished"
    FAILED = "failed"


@dataclass(slots=True)
class Target:
    url: str
    method: str = "GET"
    host: str = ""
    port: int = 443
    scheme: str = "https"


@dataclass(slots=True)
class Stats:
    sent: int = 0
    ok: int = 0
    errors: int = 0
    bytes_in: int = 0
    codes: dict[int, int] = field(default_factory=dict)
    latencies: list[float] = field(default_factory=list)
    started_at: float = field(default_factory=time.monotonic)

    @property
    def elapsed(self) -> float:
        return max(time.monotonic() - self.started_at, 1e-6)

    @property
    def rps(self) -> float:
        return self.sent / self.elapsed

    @property
    def error_rate(self) -> float:
        return (self.errors / self.sent * 100) if self.sent else 0.0

    @property
    def avg_latency(self) -> float:
        return (sum(self.latencies) / len(self.latencies) * 1000) if self.latencies else 0.0

    def merge(self, sent: int, ok: int, errors: int, size: int, codes: dict[str, int]) -> None:
        self.sent += sent
        self.ok += ok
        self.errors += errors
        self.bytes_in += size
        for c, n in codes.items():
            code = int(c)
            self.codes[code] = self.codes.get(code, 0) + n


@dataclass(slots=True)
class Attack:
    id: str
    target: Target
    owner_id: int
    duration: int
    concurrency: int
    agents: int = 0
    agent_ids: dict[str, str] = field(default_factory=dict)
    state: AttackState = AttackState.RUNNING
    stats: Stats = field(default_factory=Stats)
