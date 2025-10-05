"""Simple CLI utility for interacting with the proxy stack."""
from __future__ import annotations

import json
import requests
import typer

from settings import env_str, load_environment

load_environment()

DAEMON_URL = env_str("DAEMON_URL", "http://127.0.0.1:8090")
API_URL = env_str("API_URL", "http://127.0.0.1:8001")

app = typer.Typer(add_completion=False, help="Test CLI for python-chatgpt-proxy")


@app.command()
def create_session(browser: str = typer.Option("chromium", help="Playwright browser type")) -> None:
    response = requests.post(f"{DAEMON_URL}/sessions", json={"browser_type": browser}, timeout=10)
    response.raise_for_status()
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def list_sessions() -> None:
    response = requests.get(f"{DAEMON_URL}/sessions", timeout=10)
    response.raise_for_status()
    typer.echo(json.dumps(response.json(), indent=2))


@app.command()
def chat(
    session: str = typer.Option(..., "--session", "-s", help="Session identifier"),
    message: str = typer.Argument(..., help="User prompt"),
) -> None:
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message},
        ],
        "metadata": {"session_id": session},
    }
    response = requests.post(f"{API_URL}/v1/chat/completions", json=payload, timeout=10)
    response.raise_for_status()
    typer.echo(json.dumps(response.json(), indent=2))


def entrypoint() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    entrypoint()
