"""Utility helpers for configuration via environment variables."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

_ENV_LOADED = False


def _candidate_paths(explicit: Path | None) -> Iterable[Path]:
    if explicit is not None:
        yield explicit
        return
    cwd = Path.cwd()
    for parent in (cwd, *cwd.parents):
        candidate = parent / ".env"
        if candidate.exists():
            yield candidate
            break
    module_dir = Path(__file__).resolve().parent
    fallback = module_dir / ".env"
    if fallback.exists():
        yield fallback


def load_environment(dotenv_path: Path | None = None) -> None:
    """Load environment variables from a ``.env`` file if present."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    for path in _candidate_paths(dotenv_path):
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
        except OSError:
            continue
        else:
            break
    _ENV_LOADED = True


def env_str(name: str, default: str) -> str:
    """Return a string environment variable with a default."""
    return os.getenv(name, default)


def env_int(name: str, default: int) -> int:
    """Return an integer environment variable with a default."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_path(name: str, default: Path) -> Path:
    """Return a path environment variable with a default."""
    value = os.getenv(name)
    if value is None:
        return default
    return Path(value).expanduser().resolve()
