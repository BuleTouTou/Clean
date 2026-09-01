from __future__ import annotations

import pytest

from backend.config import ROOT, resolve_env_file
from backend.db import get_database_connect_args, get_database_schema, get_database_url


def test_default_env_file_is_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENV_FILE", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    assert resolve_env_file() == ROOT / ".env.development"


def test_legacy_env_file_requires_explicit_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENV_FILE", ".env")

    assert resolve_env_file() == ROOT / ".env"


def test_postgresql_schema_is_added_to_search_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_SCHEMA", "clean")

    assert get_database_schema() == "clean"
    assert get_database_connect_args("postgresql+psycopg://user:password@db:5432/postgres") == {
        "options": "-csearch_path=clean,public"
    }


def test_database_schema_rejects_unsafe_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DB_SCHEMA", "clean,public")

    with pytest.raises(RuntimeError, match="DB_SCHEMA"):
        get_database_schema()


def test_production_database_does_not_fall_back_to_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        get_database_url()
