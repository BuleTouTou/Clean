from __future__ import annotations

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
from .db import get_report, list_reports
from .storage import get_storage


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


@app.get("/api/status", operation_id="getStatus")
def status() -> dict[str, Any]:
    return {"files": legacy.file_status(), "tasks": len(legacy.TASKS)}


@app.get("/api/reports", operation_id="listReports")
def reports(page: int = 1, pageSize: int = 20, kind: Literal["sale", "rent"] | None = None) -> dict[str, Any]:
    return list_reports(legacy.DB_FILE, page, pageSize, kind)


@app.get("/api/reports/{report_id}", operation_id="getReport")
def report_detail(report_id: int) -> dict[str, Any]:
    item = get_report(legacy.DB_FILE, report_id)
    if item is None:
        raise HTTPException(status_code=404, detail="历史报告不存在")
    return item


@app.post("/api/task", operation_id="createTask")
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


@app.post("/api/upload", operation_id="uploadSourceFile")
async def upload(request: Request) -> dict[str, Any]:
    try:
        task_id = request.headers.get("X-Task-Id", "")
        task = legacy.get_task(task_id)
        name = Path(unquote(request.headers.get("X-Filename", "source.xlsx"))).name
        ext = Path(name).suffix.lower()
        if ext not in (".csv", ".xls", ".xlsx"):
            raise ValueError("仅支持 CSV、XLS、XLSX")
        original_path = legacy.UPLOADS / f"{task_id}{ext}"
        original_path.write_bytes(await request.body())
        path, sheets = legacy.inspect_upload(original_path)
        source_artifact = None
        storage = get_storage()
        if storage is not None:
            source_artifact = storage.upload_file(original_path, f"housing-cleaner/{task_id}/source/{name}")
        task.update({"path": path, "source_path": original_path, "original_name": name, "sheets": sheets, "source_artifact": source_artifact})
        return {
            "sheets": sheets,
            "received": {"name": name, "size": path.stat().st_size, "sizeMB": round(path.stat().st_size / 1024 / 1024, 1)},
        }
    except Exception as exc:
        fail(exc)


@app.post("/api/select-sheet", operation_id="selectSheet")
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


@app.post("/api/mapping", operation_id="saveMapping")
def mapping(body: MappingRequest) -> dict[str, Any]:
    try:
        task = legacy.get_task(body.taskId)
        task["mapping"] = body.mapping
        reviews, errors = legacy.estate_review(task)
        return {"reviews": reviews, "errors": errors, "autoCount": len(task.get("estate_auto", {}))}
    except Exception as exc:
        fail(exc)


@app.post("/api/review", operation_id="reviewEstate")
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


@app.post("/api/building-review", operation_id="reviewBuilding")
def building_review(body: ReviewRequest) -> dict[str, Any]:
    try:
        task = legacy.get_task(body.taskId)
        return {"reviews": legacy.building_review(task, body.selected)}
    except Exception as exc:
        fail(exc)


@app.post("/api/building-confirm", operation_id="confirmBuilding")
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


@app.post("/api/export", operation_id="exportTask")
def export(body: ExportRequest) -> dict[str, Any]:
    try:
        return legacy.build_output(legacy.get_task(body.taskId), body.cleanOnly)
    except Exception as exc:
        fail(exc)


@app.get("/download/{token}", response_model=None, operation_id="downloadFile")
def download(token: str) -> FileResponse | RedirectResponse:
    path = legacy.resolve_download(token)
    if path is None or not path.exists() or legacy.ROOT.resolve() not in path.resolve().parents:
        return RedirectResponse(url="/?download=missing", status_code=302)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=path.name)


app.mount("/", StaticFiles(directory=legacy.STATIC, html=True), name="static")
