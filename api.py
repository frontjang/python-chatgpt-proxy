"""OpenAI-compatible API facade."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from fastapi import FastAPI
from pydantic import BaseModel

from settings import env_int, env_str, load_environment

app = FastAPI(title="python-chatgpt-proxy API")

load_environment()

API_HOST = env_str("API_HOST", "0.0.0.0")
API_PORT = env_int("API_PORT", 8001)


@dataclass
class Conversation:
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def reply(self) -> str:
        last = self.messages[-1]["content"] if self.messages else ""
        return f"Echo: {last}"


class ChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]
    metadata: Dict[str, str] | None = None


class ChatResponseChoice(BaseModel):
    index: int
    message: Dict[str, str]
    finish_reason: str = "stop"


class ChatResponse(BaseModel):
    id: str
    model: str
    choices: List[ChatResponseChoice]


_conversations: Dict[str, Conversation] = {}


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = None
    if request.metadata:
        session_id = request.metadata.get("session_id")
    session_id = session_id or "default"

    conversation = _conversations.setdefault(session_id, Conversation())
    for message in request.messages:
        conversation.add(message["role"], message["content"])
    reply = conversation.reply()
    conversation.add("assistant", reply)

    return ChatResponse(
        id=f"chatcmpl-{len(conversation.messages)}",
        model=request.model,
        choices=[
            ChatResponseChoice(
                index=0,
                message={"role": "assistant", "content": reply},
            )
        ],
    )


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=API_HOST, port=API_PORT)


if __name__ == "__main__":  # pragma: no cover
    run()
