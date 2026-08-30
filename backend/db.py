from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    with connect(path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO task_reports (
                task_id, kind, original_name, entrust_date, started_at, completed_at,
                input_rows, output_rows, blocking_count, audit_count, source_url, source_object_key, output_file, output_url, output_object_key, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                str(report.get("任务开始时间", "")),
                str(report.get("完成时间", "")),
                int(report.get("原始记录数", 0)),
                int(report.get("最终输出记录数", 0)),
                int(report.get("阻断异常数量", 0)),
                int(audit_count),
                source_url,
                source_object_key,
                output_file,
                output_url,
                output_object_key,
                json.dumps(report, ensure_ascii=False),
            ),
        )
        return int(cursor.fetchone()[0])


def list_reports(path: Path, page: int = 1, page_size: int = 20, kind: str | None = None) -> dict[str, Any]:
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
