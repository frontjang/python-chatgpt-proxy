"""Browser daemon that manages Playwright sessions.

The daemon exposes an HTTP API for creating and destroying browser sessions and
reports back the websocket debugger URLs so that other components (web UI, CLI,
or API) can attach to the running instance.
"""
from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:  # pragma: no cover - optional dependency
    from playwright.async_api import Browser, BrowserContext, async_playwright
except Exception:  # pragma: no cover - optional dependency
    Browser = BrowserContext = None  # type: ignore
    async_playwright = None

LOGGER = logging.getLogger("daemon")


@dataclass
class Session:
    session_id: str
    browser_type: str
    debug_url: str
    context: Optional[BrowserContext] = None


class SessionRequest(BaseModel):
    browser_type: str = "chromium"


class BrowserDaemon:
    def __init__(self) -> None:
        self._playwright = None
        self._browser_cache: Dict[str, Browser] = {}
        self._sessions: Dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def startup(self) -> None:
        if async_playwright is None:
            LOGGER.warning("Playwright is not available. Sessions will be simulated.")
            return
        self._playwright = await async_playwright().start()
        LOGGER.info("Playwright started")

    async def shutdown(self) -> None:
        async with self._lock:
            for session_id in list(self._sessions.keys()):
                await self.delete_session(session_id)
        if self._playwright is not None:
            await self._playwright.stop()
            LOGGER.info("Playwright stopped")

    async def _ensure_browser(self, browser_type: str) -> Browser | None:
        if async_playwright is None or self._playwright is None:
            return None
        if browser_type not in self._browser_cache:
            browser = await getattr(self._playwright, browser_type).launch(headless=True)
            self._browser_cache[browser_type] = browser
        return self._browser_cache[browser_type]

    async def create_session(self, browser_type: str = "chromium") -> Session:
        async with self._lock:
            session_id = secrets.token_hex(8)
            context = None
            debug_url = f"wss://example.invalid/{session_id}"
            if async_playwright is not None:
                browser = await self._ensure_browser(browser_type)
                if browser is not None:
                    context = await browser.new_context()
                    page = await context.new_page()
                    await page.goto("https://example.com")
                    connection = getattr(context, "_connection", None)
                    transport = getattr(connection, "_transport", None)
                    websocket = getattr(transport, "_ws", None)
                    debug_url = getattr(websocket, "url", debug_url)
            session = Session(session_id=session_id, browser_type=browser_type, debug_url=debug_url, context=context)
            self._sessions[session_id] = session
            LOGGER.info("Created session %s", session_id)
            return session

    async def delete_session(self, session_id: str) -> None:
        async with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                raise KeyError(session_id)
            if session.context is not None:
                await session.context.close()
            LOGGER.info("Closed session %s", session_id)

    async def list_sessions(self) -> Dict[str, Session]:
        async with self._lock:
            return dict(self._sessions)


daemon = BrowserDaemon()
app = FastAPI(title="python-chatgpt-proxy daemon")


@app.on_event("startup")
async def _startup() -> None:
    await daemon.startup()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await daemon.shutdown()


@app.post("/sessions")
async def create_session(request: SessionRequest) -> Dict[str, str]:
    session = await daemon.create_session(request.browser_type)
    return {"session_id": session.session_id, "debug_url": session.debug_url}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    try:
        await daemon.delete_session(session_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Session not found") from exc
    return {"status": "deleted", "session_id": session_id}


@app.get("/sessions")
async def list_sessions() -> Dict[str, Dict[str, str]]:
    sessions = await daemon.list_sessions()
    return {
        session_id: {
            "browser_type": session.browser_type,
            "debug_url": session.debug_url,
        }
        for session_id, session in sessions.items()
    }


def run() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8090)


if __name__ == "__main__":  # pragma: no cover
    run()
