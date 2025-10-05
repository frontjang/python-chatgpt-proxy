"""Command-line entry point for controlling proxy services.

This module provides a lightweight service manager that can start, stop,
restart, and report the status of the various processes that make up the
ChatGPT proxy stack. Each service is defined by a Python module containing a
``run`` function; the manager spawns those modules in independent interpreter
processes so they can be restarted or upgraded without affecting the rest of the
stack.
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable

from settings import env_path, load_environment

load_environment()

SERVICE_DEFINITIONS: Dict[str, str] = {
    "daemon": "daemon",
    "webui": "webui",
    "api": "api",
    "mcp": "mcp",
}


@dataclass
class Service:
    """Configuration for a managed service."""

    name: str
    module: str
    pidfile: Path
    logfile: Path

    def is_running(self) -> bool:
        if not self.pidfile.exists():
            return False
        try:
            pid = int(self.pidfile.read_text().strip())
        except (OSError, ValueError):
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def start(self) -> None:
        if self.is_running():
            print(f"{self.name} is already running")
            return
        self.logfile.parent.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        with self.logfile.open("a", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                [sys.executable, "-m", self.module],
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=env,
            )
        self.pidfile.write_text(str(process.pid))
        print(f"Started {self.name} (pid={process.pid}) - logs: {self.logfile}")

    def stop(self) -> None:
        if not self.pidfile.exists():
            print(f"{self.name} is not running")
            return
        try:
            pid = int(self.pidfile.read_text().strip())
        except (OSError, ValueError):
            self.pidfile.unlink(missing_ok=True)
            print(f"Removed stale pidfile for {self.name}")
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            print(f"Process {pid} for {self.name} not found")
        else:
            print(f"Stopped {self.name} (pid={pid})")
        self.pidfile.unlink(missing_ok=True)

    def restart(self) -> None:
        self.stop()
        self.start()

    def status(self) -> str:
        return "running" if self.is_running() else "stopped"


class ServiceManager:
    """Manage the lifecycle of multiple services."""

    def __init__(self, runtime_dir: Path) -> None:
        self.runtime_dir = runtime_dir
        self.services: Dict[str, Service] = {}
        self._load_services()

    def _load_services(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        log_dir = self.runtime_dir / "logs"
        for name, module in SERVICE_DEFINITIONS.items():
            pidfile = self.runtime_dir / f"{name}.pid"
            logfile = log_dir / f"{name}.log"
            self.services[name] = Service(name=name, module=module, pidfile=pidfile, logfile=logfile)

    def _iter_services(self, names: Iterable[str] | None) -> Iterable[Service]:
        if not names:
            yield from self.services.values()
            return
        for name in names:
            try:
                yield self.services[name]
            except KeyError:
                raise SystemExit(f"Unknown service: {name}")

    def start(self, names: Iterable[str] | None = None) -> None:
        for service in self._iter_services(names):
            service.start()

    def stop(self, names: Iterable[str] | None = None) -> None:
        for service in self._iter_services(names):
            service.stop()

    def restart(self, names: Iterable[str] | None = None) -> None:
        for service in self._iter_services(names):
            service.restart()

    def status(self, names: Iterable[str] | None = None) -> None:
        for service in self._iter_services(names):
            print(f"{service.name}: {service.status()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage python-chatgpt-proxy services")
    parser.add_argument("command", choices=["start", "stop", "restart", "status"], help="Action to perform")
    parser.add_argument("services", nargs="*", help="Services to target (default: all)")
    parser.add_argument(
        "--runtime-dir",
        default=env_path("CHATGPT_PROXY_RUNTIME", Path.home() / ".chatgpt-proxy"),
        type=Path,
        help="Directory for pid files",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    manager = ServiceManager(runtime_dir=args.runtime_dir)

    command = getattr(manager, args.command)
    command(args.services)


def entrypoint() -> None:
    main()


if __name__ == "__main__":  # pragma: no cover - manual execution
    entrypoint()
