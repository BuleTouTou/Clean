from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


LEGACY_BEIJING_TIMEZONE = timezone(timedelta(hours=8))
UTC_TIMEZONE = timezone.utc


def _normalize_utc_iso(value: str, naive_timezone: timezone = LEGACY_BEIJING_TIMEZONE) -> str:
    """Normalize an ISO timestamp to a UTC value with a trailing ``Z``.

    Timestamps written by older versions had no timezone and represented Beijing
    local time, so those values are interpreted as Asia/Shanghai during migration.
    """
    raw = str(value or "").strip()
    if not raw:
        return raw
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=naive_timezone)
    return parsed.astimezone(UTC_TIMEZONE).isoformat(timespec="seconds").replace("+00:00", "Z")


def _migrate_report_timestamps(raw_report: str) -> str:
    try:
        report = json.loads(raw_report)
    except (TypeError, json.JSONDecodeError):
        return raw_report

    for key in ("任务开始时间", "完成时间"):
        if key in report:
            report[key] = _normalize_utc_iso(report[key])
    for entry in report.get("审计记录") or []:
        if isinstance(entry, dict) and "操作时间" in entry:
            entry["操作时间"] = _normalize_utc_iso(entry["操作时间"])
    return json.dumps(report, ensure_ascii=False)


def _migrate_legacy_timestamps(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        "SELECT id, started_at, completed_at, created_at, report_json FROM task_reports"
    ).fetchall()
    for row in rows:
        started_at = _normalize_utc_iso(row[1])
        completed_at = _normalize_utc_iso(row[2])
        created_at = _normalize_utc_iso(row[3], UTC_TIMEZONE)
        report_json = _migrate_report_timestamps(row[4])
        if (started_at, completed_at, created_at, report_json) != (row[1], row[2], row[3], row[4]):
            connection.execute(
                "UPDATE task_reports SET started_at = ?, completed_at = ?, created_at = ?, report_json = ? WHERE id = ?",
                (started_at, completed_at, created_at, report_json, row[0]),
            )


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS task_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                original_name TEXT NOT NULL,
                entrust_date TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT NOT NULL,
                input_rows INTEGER NOT NULL DEFAULT 0,
                output_rows INTEGER NOT NULL DEFAULT 0,
                blocking_count INTEGER NOT NULL DEFAULT 0,
                audit_count INTEGER NOT NULL DEFAULT 0,
                source_url TEXT,
                source_object_key TEXT,
                output_file TEXT,
                output_url TEXT,
                output_object_key TEXT,
                report_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(task_reports)")}
        for name, definition in {
            "source_url": "TEXT",
            "source_object_key": "TEXT",
            "output_url": "TEXT",
            "output_object_key": "TEXT",
        }.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE task_reports ADD COLUMN {name} {definition}")
        _migrate_legacy_timestamps(connection)


def save_report(
    path: Path,
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
    report_json = _migrate_report_timestamps(json.dumps(report, ensure_ascii=False))
    started_at = _normalize_utc_iso(report.get("任务开始时间", ""))
    completed_at = _normalize_utc_iso(report.get("完成时间", ""))
    created_at = datetime.now(UTC_TIMEZONE).isoformat(timespec="seconds").replace("+00:00", "Z")
    with connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO task_reports (
                task_id, kind, original_name, entrust_date, started_at, completed_at,
                input_rows, output_rows, blocking_count, audit_count, source_url, source_object_key, output_file, output_url, output_object_key, report_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                kind=excluded.kind,
                original_name=excluded.original_name,
                entrust_date=excluded.entrust_date,
                started_at=excluded.started_at,
                completed_at=excluded.completed_at,
                input_rows=excluded.input_rows,
                output_rows=excluded.output_rows,
                blocking_count=excluded.blocking_count,
                audit_count=excluded.audit_count,
                source_url=excluded.source_url,
                source_object_key=excluded.source_object_key,
                output_file=excluded.output_file,
                output_url=excluded.output_url,
                output_object_key=excluded.output_object_key,
                report_json=excluded.report_json
            RETURNING id
            """,
            (
                task_id,
                kind,
                str(report.get("原始文件名", "")),
                report.get("委托日期"),
                started_at,
                completed_at,
                int(report.get("原始记录数", 0)),
                int(report.get("最终输出记录数", 0)),
                int(report.get("阻断异常数量", 0)),
                int(audit_count),
                source_url,
                source_object_key,
                output_file,
                output_url,
                output_object_key,
                report_json,
                created_at,
            ),
        )
        return int(cursor.fetchone()[0])


def list_reports(path: Path, page: int = 1, page_size: int = 10, kind: str | None = None) -> dict[str, Any]:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    clauses: list[str] = []
    params: list[Any] = []
    if kind in ("sale", "rent"):
        clauses.append("kind = ?")
        params.append(kind)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with connect(path) as connection:
        total = int(connection.execute(f"SELECT COUNT(*) FROM task_reports{where}", params).fetchone()[0])
        rows = connection.execute(
            f"SELECT id, task_id, kind, original_name, entrust_date, started_at, completed_at, input_rows, output_rows, blocking_count, audit_count, source_url, source_object_key, output_file, output_url, output_object_key, report_json FROM task_reports{where} ORDER BY completed_at DESC, id DESC LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["report"] = json.loads(item.pop("report_json"))
        items.append(item)
    return {"items": items, "total": total, "page": page, "pageSize": page_size}


def get_report(path: Path, report_id: int) -> dict[str, Any] | None:
    with connect(path) as connection:
        row = connection.execute("SELECT * FROM task_reports WHERE id = ?", (report_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["report"] = json.loads(item.pop("report_json"))
    return item
