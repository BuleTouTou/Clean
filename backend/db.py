from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint, create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


ROOT = Path(__file__).resolve().parent.parent
LEGACY_BEIJING_TIMEZONE = timezone(timedelta(hours=8))
UTC_TIMEZONE = timezone.utc


def get_database_url() -> str:
    """Use PostgreSQL when configured, with SQLite only as a local/test fallback."""
    return os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'housing_cleaner.sqlite3'}")


class Base(DeclarativeBase):
    pass


json_type = JSON().with_variant(JSONB(), "postgresql")


class TaskReport(Base):
    __tablename__ = "task_reports"
    __table_args__ = (UniqueConstraint("task_id", name="uq_task_reports_task_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    entrust_date: Mapped[str | None] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocking_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_object_key: Mapped[str | None] = mapped_column(Text)
    output_file: Mapped[str | None] = mapped_column(Text)
    output_url: Mapped[str | None] = mapped_column(Text)
    output_object_key: Mapped[str | None] = mapped_column(Text)
    report_json: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC_TIMEZONE)
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC_TIMEZONE),
        onupdate=lambda: datetime.now(UTC_TIMEZONE),
    )


_engine = None
_engine_url: str | None = None


def get_engine():
    global _engine, _engine_url
    url = get_database_url()
    if _engine is None or _engine_url != url:
        if _engine is not None:
            _engine.dispose()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        _engine_url = url
    return _engine


def get_session_factory():
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_db() -> None:
    """Create missing tables for tests/direct runs; containers use Alembic."""
    if get_database_url().startswith("sqlite"):
        (ROOT / "data").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(get_engine())


def _normalize_datetime(value: str | datetime, naive_timezone: timezone = LEGACY_BEIJING_TIMEZONE) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC_TIMEZONE)


def _utc_iso(value: datetime | str | None) -> str:
    if value is None:
        return ""
    return _normalize_datetime(value, UTC_TIMEZONE).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_report(report: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(report, ensure_ascii=False, default=str))
    for key in ("任务开始时间", "完成时间"):
        if normalized.get(key):
            normalized[key] = _utc_iso(normalized[key])
    for entry in normalized.get("审计记录") or []:
        if isinstance(entry, dict) and entry.get("操作时间"):
            entry["操作时间"] = _utc_iso(entry["操作时间"])
    return normalized


def _report_dict(row: TaskReport) -> dict[str, Any]:
    return {
        "id": row.id,
        "task_id": row.task_id,
        "kind": row.kind,
        "original_name": row.original_name,
        "entrust_date": row.entrust_date,
        "started_at": _utc_iso(row.started_at),
        "completed_at": _utc_iso(row.completed_at),
        "input_rows": row.input_rows,
        "output_rows": row.output_rows,
        "blocking_count": row.blocking_count,
        "audit_count": row.audit_count,
        "source_url": row.source_url,
        "source_object_key": row.source_object_key,
        "output_file": row.output_file,
        "output_url": row.output_url,
        "output_object_key": row.output_object_key,
        "report": row.report_json,
    }


def save_report(
    task_id: str,
    kind: str,
    report: dict[str, Any],
    output_file: str | None,
    audit_count: int,
    source_url: str | None = None,
    source_object_key: str | None = None,
    output_url: str | None = None,
    output_object_key: str | None = None,
) -> int:
    normalized = _normalize_report(report)
    Session = get_session_factory()
    with Session.begin() as session:
        row = session.scalar(select(TaskReport).where(TaskReport.task_id == task_id))
        if row is None:
            row = TaskReport(task_id=task_id)
            session.add(row)
        row.kind = kind
        row.original_name = str(normalized.get("原始文件名", ""))
        row.entrust_date = normalized.get("委托日期")
        row.started_at = _normalize_datetime(normalized["任务开始时间"])
        row.completed_at = _normalize_datetime(normalized["完成时间"])
        row.input_rows = int(normalized.get("原始记录数", 0))
        row.output_rows = int(normalized.get("最终输出记录数", 0))
        row.blocking_count = int(normalized.get("阻断异常数量", 0))
        row.audit_count = int(audit_count)
        row.source_url = source_url
        row.source_object_key = source_object_key
        row.output_file = output_file
        row.output_url = output_url
        row.output_object_key = output_object_key
        row.report_json = normalized
        session.flush()
        return row.id


def list_reports(page: int = 1, page_size: int = 10, kind: str | None = None) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    filters = [TaskReport.kind == kind] if kind in ("sale", "rent") else []
    Session = get_session_factory()
    with Session() as session:
        total = int(session.scalar(select(func.count()).select_from(TaskReport).where(*filters)) or 0)
        rows = session.scalars(
            select(TaskReport)
            .where(*filters)
            .order_by(TaskReport.completed_at.desc(), TaskReport.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        ).all()
        return {"items": [_report_dict(row) for row in rows], "total": total, "page": page, "pageSize": page_size}


def get_report(report_id: int) -> dict[str, Any] | None:
    Session = get_session_factory()
    with Session() as session:
        row = session.get(TaskReport, report_id)
        return _report_dict(row) if row is not None else None


def load_setting(key: str, default: dict[str, Any]) -> dict[str, Any]:
    Session = get_session_factory()
    with Session() as session:
        row = session.get(AppSetting, key)
        return json.loads(json.dumps(row.value if row is not None else default))


def save_setting(key: str, value: dict[str, Any]) -> None:
    Session = get_session_factory()
    with Session.begin() as session:
        row = session.get(AppSetting, key)
        if row is None:
            session.add(AppSetting(key=key, value=value))
        else:
            row.value = value
            row.updated_at = datetime.now(UTC_TIMEZONE)
