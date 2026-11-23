"""Klient klastra: wysyla ataki na agentow i agreguje statystyki."""
from __future__ import annotations

import asyncio
import logging

import aiohttp

log = logging.getLogger("cluster")


class Agent:
    def __init__(self, name: str, url: str, token: str, weight: int = 1) -> None:
        self.name = name
        self.url = url.rstrip("/")
        self.token = token
        self.weight = max(1, weight)
        self.alive = False
        self.latency_ms = 0.0

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Agent-Token": self.token}


class Cluster:
    """Zarzadza agentami: health-check, rozdzielanie ruchu, agregacja."""

    def __init__(self, agents: list[Agent], timeout: float = 5.0) -> None:
        self.agents = agents
        self._timeout = timeout
        self._session: aiohttp.ClientSession | None = None
        self._health_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._timeout)
        )
        self._health_task = asyncio.create_task(self._health_loop())

    async def close(self) -> None:
        if self._health_task:
            self._health_task.cancel()
        if self._session:
            await self._session.close()

    @property
    def online(self) -> list[Agent]:
        return [a for a in self.agents if a.alive]

    @property
    def total_weight(self) -> int:
        return sum(a.weight for a in self.online)

    async def _health_loop(self) -> None:
        while True:
            await asyncio.gather(*(self._check(a) for a in self.agents), return_exceptions=True)
            await asyncio.sleep(10)

    async def _check(self, agent: Agent) -> None:
        assert self._session is not None
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        try:
            async with self._session.get(f"{agent.url}/health", headers=agent.headers) as r:
                agent.alive = r.status == 200
                agent.latency_ms = (loop.time() - t0) * 1000
        except Exception:
            agent.alive = False
            agent.latency_ms = 0.0

    def split(self, concurrency: int) -> dict[Agent, int]:
        """Dzieli watki proporcjonalnie do wagi agentow."""
        online = self.online
        if not online:
            return {}
        total = sum(a.weight for a in online)
        plan: dict[Agent, int] = {}
        for a in online:
            share = max(1, round(concurrency * a.weight / total))
            plan[a] = share
        return plan

    async def launch(self, url: str, method: str, duration: int, concurrency: int) -> dict[str, str]:
        """Startuje atak na wszystkich agentach. Zwraca mape agent->id."""
        assert self._session is not None
        plan = self.split(concurrency)
        if not plan:
            raise RuntimeError("brak zywych agentow")
        started: dict[str, str] = {}

        async def one(agent: Agent, conc: int) -> None:
            payload = {"url": url, "method": method, "duration": duration, "concurrency": conc}
            try:
                async with self._session.post(f"{agent.url}/launch", json=payload, headers=agent.headers) as r:
                    data = await r.json()
                    if data.get("ok"):
                        started[agent.name] = data["id"]
                    else:
                        log.warning("%s odrzucil: %s", agent.name, data)
            except Exception as exc:
                log.warning("%s blad: %s", agent.name, exc)

        await asyncio.gather(*(one(a, c) for a, c in plan.items()))
        if not started:
            raise RuntimeError("zaden agent nie przyjal ataku")
        return started

    async def stop(self, ids: dict[str, str]) -> None:
        assert self._session is not None
        by_name = {a.name: a for a in self.agents}

        async def one(name: str, aid: str) -> None:
            agent = by_name.get(name)
            if not agent:
                return
            try:
                async with self._session.post(f"{agent.url}/stop/{aid}", headers=agent.headers):
                    pass
            except Exception:
                pass

        await asyncio.gather(*(one(n, i) for n, i in ids.items()))

    async def collect(self) -> dict[str, dict]:
        """Zbiera statystyki ze wszystkich agentow."""
        assert self._session is not None
        out: dict[str, dict] = {}

        async def one(agent: Agent) -> None:
            try:
                async with self._session.get(f"{agent.url}/stats", headers=agent.headers) as r:
                    data = await r.json()
                    out[agent.name] = data.get("attacks", {})
            except Exception:
                pass

        await asyncio.gather(*(one(a) for a in self.online))
        return out
