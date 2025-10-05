"""Minimal MCP (Model Context Protocol) websocket server."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import httpx
import websockets
from websockets.server import WebSocketServerProtocol

from settings import env_int, env_str, load_environment

load_environment()

API_BASE_URL = env_str("API_URL", "http://127.0.0.1:8001")
API_COMPLETIONS_URL = env_str(
    "API_COMPLETIONS_URL", f"{API_BASE_URL.rstrip('/')}/v1/chat/completions"
)
MCP_HOST = env_str("MCP_HOST", "0.0.0.0")
MCP_PORT = env_int("MCP_PORT", 9000)


class MCPServer:
    def __init__(self, host: str = MCP_HOST, port: int = MCP_PORT) -> None:
        self.host = host
        self.port = port

    async def handle(self, websocket: WebSocketServerProtocol) -> None:
        await websocket.send(json.dumps({"type": "welcome", "message": "MCP server ready"}))
        async for message in websocket:
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue
            response = await self._forward(payload)
            await websocket.send(json.dumps(response))

    async def _forward(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            api_response = await client.post(API_COMPLETIONS_URL, json=payload)
            api_response.raise_for_status()
            return {"type": "response", "data": api_response.json()}

    async def serve(self) -> None:
        async with websockets.serve(self.handle, self.host, self.port):
            await asyncio.Future()


def run() -> None:
    asyncio.run(MCPServer().serve())


if __name__ == "__main__":  # pragma: no cover
    run()
