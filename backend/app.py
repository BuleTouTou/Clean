from __future__ import annotations

import os
import threading
import webbrowser
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 清洗算法集中在包内 core 模块。
from . import core as legacy


class TaskRequest(BaseModel):
    kind: Literal["sale", "rent"]


class TaskBody(BaseModel):
    taskId: str


class SheetRequest(TaskBody):
    sheet: str
    headerRow: int = Field(ge=1)


class MappingRequest(TaskBody):
    mapping: dict[str, str | list[str]]


class ReviewRequest(TaskBody):
    selected: dict[str, str] = Field(default_factory=dict)
    entrustDate: str | None = None
    persistRules: bool = True


class ExportRequest(TaskBody):
    cleanOnly: bool = False


app = FastAPI(
    title="房源数据清洗工具",
    version="0.1.0",
    description="本地运行的北京房源数据清洗服务",
)


def fail(exc: Exception) -> None:
    raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    # 保持现有前端约定：错误字段名为 error，而不是 FastAPI 默认的 detail。
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "请求参数无效", "detail": exc.errors()})


@app.on_event("startup")
def on_startup() -> None:
    port = int(os.environ.get("HOUSING_CLEANER_PORT", "8765"))
    url = f"http://127.0.0.1:{port}"
    print(f"房源数据清洗工具已启动：{url}")
    if os.environ.get("HOUSING_CLEANER_OPEN_BROWSER", "1") == "1":
        threading.Timer(1, lambda: webbrowser.open(url)).start()


@app.get("/api/status")
def status() -> dict[str, Any]:
    return {"files": legacy.file_status(), "tasks": len(legacy.TASKS)}


@app.post("/api/task")
def create_task(body: TaskRequest) -> dict[str, Any]:
    try:
        missing = [item["name"] for item in legacy.file_status() if not item["exists"]]
        if missing:
            raise ValueError("缺少基础文件：" + "、".join(missing))
        info = legacy.template_info(body.kind)
        task_id = legacy.uuid.uuid4().hex[:12]
        legacy.TASKS[task_id] = {
            "id": task_id,
            "kind": body.kind,
            "started": legacy.datetime.now().isoformat(timespec="seconds"),
            "entrust_date": str(date.today()),
            "template_signature": info["signature"],
        }
        return {"taskId": task_id, "headers": info["headers"]}
    except Exception as exc:
        fail(exc)


@app.post("/api/upload")
async def upload(request: Request) -> dict[str, Any]:
    try:
        task_id = request.headers.get("X-Task-Id", "")
        task = legacy.get_task(task_id)
        name = Path(unquote(request.headers.get("X-Filename", "source.xlsx"))).name
        ext = Path(name).suffix.lower()
        if ext not in (".csv", ".xls", ".xlsx"):
            raise ValueError("仅支持 CSV、XLS、XLSX")
        path = legacy.UPLOADS / f"{task_id}{ext}"
        path.write_bytes(await request.body())
        path, sheets = legacy.inspect_upload(path)
        task.update({"path": path, "original_name": name, "sheets": sheets})
        return {
            "sheets": sheets,
            "received": {"name": name, "size": path.stat().st_size, "sizeMB": round(path.stat().st_size / 1024 / 1024, 1)},
        }
    except Exception as exc:
        fail(exc)


@app.post("/api/select-sheet")
def select_sheet(body: SheetRequest) -> dict[str, Any]:
    try:
        task = legacy.get_task(body.taskId)
        headers, rows = legacy.read_table(task["path"], body.sheet, body.headerRow)
        source_key = legacy.hashlib.sha256("|".join(map(legacy.norm, headers)).encode()).hexdigest()
        task.update({"sheet": body.sheet, "header_row": body.headerRow, "headers": headers, "rows": rows, "source_key": source_key})
        targets = legacy.template_info(task["kind"])["headers"]
        return {"headers": headers, "rows": len(rows), "suggestions": legacy.mapping_suggestions(headers, targets, rows, source_key), "targets": targets}
    except Exception as exc:
        fail(exc)


@app.post("/api/mapping")
def mapping(body: MappingRequest) -> dict[str, Any]:
    try:
        task = legacy.get_task(body.taskId)
        task["mapping"] = body.mapping
        reviews, errors = legacy.estate_review(task)
        return {"reviews": reviews, "errors": errors, "autoCount": len(task.get("estate_auto", {}))}
    except Exception as exc:
        fail(exc)


@app.post("/api/review")
def review(body: ReviewRequest) -> dict[str, bool]:
    try:
        task = legacy.get_task(body.taskId)
        for item in task.get("estate_reviews", []):
            item["selected"] = body.selected.get(item.get("key", item["raw"]), body.selected.get(item["raw"], ""))
        task["entrust_date"] = body.entrustDate or task["entrust_date"]
        legacy.save_rules(task)
        return {"ok": True}
    except Exception as exc:
        fail(exc)


@app.post("/api/building-review")
def building_review(body: ReviewRequest) -> dict[str, Any]:
    try:
        task = legacy.get_task(body.taskId)
        return {"reviews": legacy.building_review(task, body.selected)}
    except Exception as exc:
        fail(exc)


@app.post("/api/building-confirm")
def building_confirm(body: ReviewRequest) -> dict[str, bool]:
    try:
        task = legacy.get_task(body.taskId)
        for item in task.get("building_reviews", []):
            item["selected"] = body.selected.get(item["key"], "")
        task["entrust_date"] = body.entrustDate or task["entrust_date"]
        if body.persistRules:
            legacy.save_rules(task)
        return {"ok": True}
    except Exception as exc:
        fail(exc)


@app.post("/api/export")
def export(body: ExportRequest) -> dict[str, Any]:
    try:
        return legacy.build_output(legacy.get_task(body.taskId), body.cleanOnly)
    except Exception as exc:
        fail(exc)


@app.get("/download/{token}", response_model=None)
def download(token: str) -> FileResponse | RedirectResponse:
    path = legacy.resolve_download(token)
    if path is None or not path.exists() or legacy.ROOT.resolve() not in path.resolve().parents:
        return RedirectResponse(url="/?download=missing", status_code=302)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=path.name)


app.mount("/", StaticFiles(directory=legacy.STATIC, html=True), name="static")
