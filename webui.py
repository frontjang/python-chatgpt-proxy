"""Management web UI for the ChatGPT proxy stack."""
from __future__ import annotations

from typing import Dict

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from settings import env_int, env_str, load_environment

load_environment()

DAEMON_URL = env_str("DAEMON_URL", "http://127.0.0.1:8090")
WEBUI_HOST = env_str("WEBUI_HOST", "0.0.0.0")
WEBUI_PORT = env_int("WEBUI_PORT", 8091)

app = FastAPI(title="python-chatgpt-proxy webui")


def _render_index(sessions: Dict[str, Dict[str, str]]) -> str:
    session_rows = "".join(
        f"<tr><td>{session_id}</td><td>{data['browser_type']}</td><td>{data['debug_url']}</td>"
        f"<td><button hx-delete='/sessions/{session_id}'>Delete</button></td></tr>"
        for session_id, data in sessions.items()
    )
    return f"""<!doctype html>
    <html>
    <head>
        <title>python-chatgpt-proxy</title>
        <style>
            body {{ font-family: sans-serif; margin: 2rem; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 0.5rem; }}
        </style>
    </head>
    <body>
        <h1>Browser Sessions</h1>
        <form method=\"post\" action=\"/sessions\">
            <label>Browser type: <input name=\"browser_type\" value=\"chromium\"></label>
            <button type=\"submit\">Create session</button>
        </form>
        <table>
            <thead><tr><th>Session</th><th>Browser</th><th>Debugger URL</th><th></th></tr></thead>
            <tbody>{session_rows}</tbody>
        </table>
    </body>
    </html>"""


async def fetch_sessions() -> Dict[str, Dict[str, str]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DAEMON_URL}/sessions")
        response.raise_for_status()
        return response.json()


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    sessions = await fetch_sessions()
    return _render_index(sessions)


@app.post("/sessions", response_class=HTMLResponse)
async def create_session(request: Request) -> str:
    form = await request.form()
    browser_type = form.get("browser_type", "chromium")
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{DAEMON_URL}/sessions", json={"browser_type": browser_type})
        response.raise_for_status()
    sessions = await fetch_sessions()
    return _render_index(sessions)


@app.delete("/sessions/{session_id}", response_class=HTMLResponse)
async def delete_session(session_id: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{DAEMON_URL}/sessions/{session_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Session not found")
        response.raise_for_status()
    sessions = await fetch_sessions()
    return _render_index(sessions)


@app.websocket("/sessions/{session_id}/ws")
async def session_proxy(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{DAEMON_URL}/sessions")
        response.raise_for_status()
        sessions = response.json()
    session = sessions.get(session_id)
    if not session:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close(code=4004)
        return

    debug_url = session.get("debug_url")
    await websocket.send_json({"info": f"Proxying to {debug_url}"})
    # Real-time proxying is outside scope; we simply keep the connection alive.
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=WEBUI_HOST, port=WEBUI_PORT)


if __name__ == "__main__":  # pragma: no cover
    run()
