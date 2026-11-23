"""Lokalny silnik agenta: aiohttp, pula workerow."""
from __future__ import annotations

import asyncio
import ssl
import time
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse

import aiohttp


@dataclass(slots=True)
class LocalStats:
    sent: int = 0
    ok: int = 0
    errors: int = 0
    bytes_in: int = 0
    codes: dict[int, int] = field(default_factory=dict)
    started: float = field(default_factory=time.monotonic)

    @property
    def elapsed(self) -> float:
        return max(time.monotonic() - self.started, 1e-6)

    @property
    def rps(self) -> float:
        return self.sent / self.elapsed

    def snapshot(self) -> dict:
        return {
            "sent": self.sent,
            "ok": self.ok,
            "errors": self.errors,
            "bytes": self.bytes_in,
            "rps": round(self.rps, 1),
            "codes": {str(k): v for k, v in self.codes.items()},
            "elapsed": round(self.elapsed, 1),
        }


@dataclass(slots=True)
class LocalAttack:
    id: str
    url: str
    method: str
    duration: int
    concurrency: int
    stats: LocalStats = field(default_factory=LocalStats)
    running: bool = True


class AgentEngine:
    def __init__(self, timeout: float = 20.0, verify: bool = True) -> None:
        self._timeout = timeout
        self._verify = verify
        self._attacks: dict[str, LocalAttack] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        ctx = ssl.create_default_context()
        if not self._verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        conn = aiohttp.TCPConnector(limit=0, ssl=ctx, ttl_dns_cache=300)
        self._session = aiohttp.ClientSession(
            connector=conn,
            timeout=aiohttp.ClientTimeout(total=self._timeout),
            headers={"User-Agent": "EP-Agent/1.0", "Accept": "*/*"},
        )

    async def close(self) -> None:
        for t in list(self._tasks.values()):
            t.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        if self._session:
            await self._session.close()

    def stats(self) -> dict:
        return {aid: a.stats.snapshot() for aid, a in self._attacks.items()}

    def active_count(self) -> int:
        return len(self._attacks)

    async def launch(self, url: str, method: str, duration: int, concurrency: int) -> str:
        p = urlparse(url if url.startswith("http") else "https://" + url)
        if not p.hostname:
            raise ValueError("bad url")
        aid = uuid.uuid4().hex[:8]
        attack = LocalAttack(
            id=aid, url=url, method=method.upper(),
            duration=duration, concurrency=max(1, min(concurrency, 300)),
        )
        self._attacks[aid] = attack
        self._tasks[aid] = asyncio.create_task(self._run(attack))
        return aid

    async def stop(self, aid: str) -> bool:
        a = self._attacks.get(aid)
        if not a or not a.running:
            return False
        a.running = False
        t = self._tasks.get(aid)
        if t:
            t.cancel()
        return True

    async def _run(self, attack: LocalAttack) -> None:
        deadline = time.monotonic() + attack.duration
        try:
            async with asyncio.TaskGroup() as tg:
                for _ in range(attack.concurrency):
                    tg.create_task(self._worker(attack, deadline))
        except asyncio.CancelledError:
            pass
        finally:
            attack.running = False

    async def _worker(self, attack: LocalAttack, deadline: float) -> None:
        assert self._session is not None
        while time.monotonic() < deadline and attack.running:
            try:
                async with self._session.request(attack.method, attack.url) as r:
                    body = await r.read()
                    attack.stats.sent += 1
                    attack.stats.bytes_in += len(body)
                    if 200 <= r.status < 400:
                        attack.stats.ok += 1
                    else:
                        attack.stats.errors += 1
                    attack.stats.codes[r.status] = attack.stats.codes.get(r.status, 0) + 1
            except asyncio.CancelledError:
                raise
            except Exception:
                attack.stats.sent += 1
                attack.stats.errors += 1
