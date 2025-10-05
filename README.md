# python-chatgpt-proxy

A Python re-implementation of the "Simple ChatGPT Proxy" concept. This project
provides a collection of small services that collectively proxy requests to a
headless browser, expose an OpenAI-compatible API, and surface a management UI.

## Services

| Module  | Description |
| ------- | ----------- |
| `daemon.py` | Manages Playwright browser sessions and exposes an HTTP API on port 8090. |
| `webui.py` | FastAPI-based management UI for creating and removing browser sessions (port 8091). |
| `api.py` | OpenAI-compatible chat completions endpoint running on port 8001. |
| `mcp.py` | Minimal Model Context Protocol websocket server listening on port 9000. |
| `cli.py` | Simple Typer CLI for creating sessions and sending chat requests. |
| `main.py` | Supervisor CLI for starting/stopping the above services. |

The project is packaged with a `pyproject.toml` so it can be installed and used
as a standard Python application. Optional Playwright integration is available
by installing the `playwright` extra.

## Quick start

1. Install dependencies (ideally in a virtual environment):

   ```bash
   pip install -e .
   ```

   To enable Playwright support:

   ```bash
   pip install -e .[playwright]
   playwright install chromium
   ```

2. Start the service stack using the supervisor CLI:

   ```bash
   chatgpt-proxy start
   ```

   This will launch the daemon, web UI, API, and MCP server. You can check their
   status with:

   ```bash
   chatgpt-proxy status
   ```

3. Visit the management UI at [http://localhost:8091](http://localhost:8091) to
   create browser sessions, or use the CLI:

   ```bash
   chatgpt-proxy-cli create-session
   ```

4. Interact with the OpenAI-compatible API:

   ```bash
   curl -X POST http://localhost:8001/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [
         {"role": "user", "content": "Hello"}
       ]
     }'
   ```

## Development

The services are deliberately lightweight so they can be easily extended. Each
module exposes a `run()` function which is used by the supervisor; you can also
run them directly for debugging purposes:

```bash
python -m daemon
python -m webui
python -m api
python -m mcp
```

The CLI entry points `chatgpt-proxy` and `chatgpt-proxy-cli` are registered via
`pyproject.toml`.
