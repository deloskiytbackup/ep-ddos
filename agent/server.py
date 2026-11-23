"""Serwer agenta: API HTTP dla koordynatora."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from aiohttp import web

from agent.engine import AgentEngine

log = logging.getLogger("agent")
TOKEN = os.getenv("AGENT_TOKEN", "")
PORT = int(os.getenv("AGENT_PORT", "8787"))


@web.middleware
async def auth(request: web.Request, handler: Any) -> web.StreamResponse:
    if TOKEN and request.headers.get("X-Agent-Token") != TOKEN:
        raise web.HTTPUnauthorized(text='{"error":"bad token"}', content_type="application/json")
    return await handler(request)


def json_ok(data: dict) -> web.Response:
    return web.json_response({"ok": True, **data})


async def health(request: web.Request) -> web.Response:
    eng: AgentEngine = request.app["engine"]
    return json_ok({"agent": request.app["name"], "active": eng.active_count()})


async def stats(request: web.Request) -> web.Response:
    eng: AgentEngine = request.app["engine"]
    return json_ok({"attacks": eng.stats()})


async def launch(request: web.Request) -> web.Response:
    body = await request.json()
    url = body.get("url", "")
    if not url:
        raise web.HTTPBadRequest(text='{"error":"missing url"}', content_type="application/json")
    eng: AgentEngine = request.app["engine"]
    try:
        aid = await eng.launch(
            url,
            body.get("method", "GET"),
            int(body.get("duration", 60)),
            int(body.get("concurrency", 50)),
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(text=f'{{"error":"{exc}"}}', content_type="application/json")
    return json_ok({"id": aid})


async def stop(request: web.Request) -> web.Response:
    aid = request.match_info["aid"]
    eng: AgentEngine = request.app["engine"]
    return json_ok({"stopped": await eng.stop(aid)})


async def make_app(name: str) -> web.Application:
    app = web.Application(middlewares=[auth])
    app["name"] = name
    engine = AgentEngine()
    await engine.start()
    app["engine"] = engine
    app.router.add_get("/health", health)
    app.router.add_get("/stats", stats)
    app.router.add_post("/launch", launch)
    app.router.add_post("/stop/{aid}", stop)
    app.on_shutdown.append(lambda _: engine.close())
    return app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    name = os.getenv("AGENT_NAME", "agent")
    log.info("start %s na :%s", name, PORT)
    web.run_app(make_app(name), port=PORT)


if __name__ == "__main__":
    main()
