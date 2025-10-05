# python-chatgpt-proxy

A Python re-implementation of the "Simple ChatGPT Proxy" concept. This project
provides a collection of small services that collectively proxy requests to a
headless browser, expose an OpenAI-compatible API, and surface a management UI.

## Services

| Module  | Description |
| ------- | ----------- |
| `daemon.py` | Manages Playwright browser sessions and exposes an HTTP API (default port 8090). |
| `webui.py` | FastAPI-based management UI for creating and removing browser sessions (default port 8091). |
| `api.py` | OpenAI-compatible chat completions endpoint (default port 8001). |
| `mcp.py` | Minimal Model Context Protocol websocket server (default port 9000). |
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

## Configuration

Service ports and connection details are controlled through environment
variables. A `.env` file is included with sensible defaults:

```
DAEMON_PORT=8090
WEBUI_PORT=8091
API_PORT=8001
MCP_PORT=9000
```

Any values defined in the environment take precedence. The supervisor stores
PID files and consolidated service logs under `~/.chatgpt-proxy` by default; you
can override this path with the `CHATGPT_PROXY_RUNTIME` variable. Each managed
service logs stdout and stderr to a file inside the runtime directory (for
example `~/.chatgpt-proxy/logs/daemon.log`) so that startup issues and runtime
errors are easy to inspect.
