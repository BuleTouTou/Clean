from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent


def _profile_name(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"prod", "production"}:
        return "production"
    if normalized in {"dev", "development", "local", "test", "testing"}:
        return "development"
    return normalized


def resolve_env_file() -> Path | None:
    """Resolve an optional dotenv file without overriding platform variables."""
    explicit = os.getenv("ENV_FILE", "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_absolute() else ROOT / path

    app_env = os.getenv("APP_ENV", "").strip()
    if app_env:
        return ROOT / f".env.{_profile_name(app_env)}"

    return ROOT / ".env.development"


def load_environment() -> Path | None:
    path = resolve_env_file()
    if path is not None and path.is_file():
        load_dotenv(path, override=False)
        return path
    return None


LOADED_ENV_FILE = load_environment()
