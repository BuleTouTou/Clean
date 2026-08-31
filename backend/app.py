from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 清洗算法集中在包内 core 模块。
from . import core as legacy
from .auth import (
    AuthError,
    authenticate,
    change_password,
    create_session,
    create_user,
    ensure_admin,
    list_users,
    reset_user_password,
    revoke_session,
    serialize_user,
    user_from_session,
)
from .db import User, get_report, list_reports
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


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str


class CreateUserRequest(BaseModel):
    username: str
    name: str
    initialPassword: str


class ResetPasswordRequest(BaseModel):
    initialPassword: str


SESSION_COOKIE = "cleaner_session"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_admin()
    yield


app = FastAPI(
    title="房源数据清洗工具",
    version="0.1.0",
    description="本地运行的北京房源数据清洗服务",
    lifespan=lifespan,
)


def fail(exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max(1, min(30, int(os.getenv("SESSION_DAYS", "7")))) * 86400,
        httponly=True,
        secure=os.getenv("SESSION_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"},
        samesite="lax",
        path="/",
    )


def current_user(request: Request) -> User:
    user = user_from_session(request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="请先登录")
    return user


def ready_user(user: User = Depends(current_user)) -> User:
    if user.must_change_password:
        raise HTTPException(status_code=403, detail="首次登录必须先修改密码")
    return user


def admin_user(user: User = Depends(ready_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可以执行此操作")
    return user


def owned_task(task_id: str, user: User) -> dict[str, Any]:
    task = legacy.get_task(task_id)
    if task.get("user_id") != user.id:
        raise HTTPException(status_code=404, detail="清洗任务不存在")
    return task


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    # 保持现有前端约定：错误字段名为 error，而不是 FastAPI 默认的 detail。
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": message})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "请求参数无效", "detail": exc.errors()})


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/api/auth/login", operation_id="login")
def login(body: LoginRequest, response: Response) -> dict[str, Any]:
    user = authenticate(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="账号或密码不正确")
    set_session_cookie(response, create_session(user.id))
    return {"user": serialize_user(user)}


@app.get("/api/auth/me", operation_id="getCurrentUser")
def me(user: User = Depends(current_user)) -> dict[str, Any]:
    return {"user": serialize_user(user)}


@app.post("/api/auth/change-password", operation_id="changeCurrentPassword")
def change_current_password(
    body: ChangePasswordRequest,
    response: Response,
    user: User = Depends(current_user),
) -> dict[str, Any]:
    try:
        change_password(user.id, body.currentPassword, body.newPassword)
        set_session_cookie(response, create_session(user.id))
        return {"ok": True, "user": {**serialize_user(user), "mustChangePassword": False}}
    except AuthError as exc:
        fail(exc)


@app.post("/api/auth/logout", operation_id="logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    revoke_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/users", operation_id="listUsers")
def users(_admin: User = Depends(admin_user)) -> dict[str, Any]:
    return {"items": list_users()}


@app.post("/api/users", operation_id="createUser")
def add_user(body: CreateUserRequest, _admin: User = Depends(admin_user)) -> dict[str, Any]:
    try:
        return {"user": create_user(body.username, body.name, body.initialPassword)}
    except AuthError as exc:
        fail(exc)


@app.post("/api/users/{user_id}/reset-password", operation_id="resetUserPassword")
def reset_password(user_id: int, body: ResetPasswordRequest, _admin: User = Depends(admin_user)) -> dict[str, Any]:
    try:
        return {"user": reset_user_password(user_id, body.initialPassword)}
    except AuthError as exc:
        fail(exc)


@app.get("/api/status", operation_id="getStatus")
def status(_user: User = Depends(ready_user)) -> dict[str, Any]:
    return {"files": legacy.file_status(), "tasks": len(legacy.TASKS)}


@app.get("/api/reports", operation_id="listReports")
def reports(
    page: int = 1,
    pageSize: int = 10,
    kind: Literal["sale", "rent"] | None = None,
    ownerSearch: str | None = None,
    user: User = Depends(ready_user),
) -> dict[str, Any]:
    return list_reports(
        page,
        pageSize,
        kind,
        None if user.role == "admin" else user.id,
        ownerSearch if user.role == "admin" else None,
    )


@app.get("/api/reports/{report_id}", operation_id="getReport")
def report_detail(report_id: int, user: User = Depends(ready_user)) -> dict[str, Any]:
    item = get_report(report_id, None if user.role == "admin" else user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="历史报告不存在")
    return item


@app.get("/api/reports/{report_id}/download", response_model=None, operation_id="downloadReport")
def download_report(report_id: int, user: User = Depends(ready_user)) -> FileResponse | StreamingResponse:
    item = get_report(report_id, None if user.role == "admin" else user.id)
    if item is None:
        raise HTTPException(status_code=404, detail="历史报告不存在")

    object_key = item.get("output_object_key")
    if object_key:
        storage = get_storage()
        if storage is None:
            raise HTTPException(status_code=503, detail="OSS 存储未启用")
        filename = Path(str(object_key)).name
        return StreamingResponse(
            storage.iter_object(str(object_key)),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
        )

    output_file = item.get("output_file")
    if output_file:
        path = (legacy.ROOT / str(output_file)).resolve()
        if not legacy.is_managed_path(path) or not path.is_file():
            raise HTTPException(status_code=404, detail="导出文件不存在")
        return FileResponse(
            path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=path.name,
        )

    raise HTTPException(status_code=404, detail="该报告没有可下载的文件")


@app.post("/api/task", operation_id="createTask")
def create_task(body: TaskRequest, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        missing = [item["name"] for item in legacy.file_status() if not item["exists"]]
        if missing:
            raise ValueError("缺少基础文件：" + "、".join(missing))
        info = legacy.template_info(body.kind)
        task_id = legacy.uuid.uuid4().hex[:12]
        legacy.TASKS[task_id] = {
            "id": task_id,
            "user_id": user.id,
            "username": user.username,
            "kind": body.kind,
            "started": legacy.utc_now_iso(),
            "entrust_date": str(date.today()),
            "template_signature": info["signature"],
        }
        return {"taskId": task_id, "headers": info["headers"]}
    except Exception as exc:
        fail(exc)


@app.post("/api/upload", operation_id="uploadSourceFile")
async def upload(request: Request, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        task_id = request.headers.get("X-Task-Id", "")
        task = owned_task(task_id, user)
        name = Path(unquote(request.headers.get("X-Filename", "source.xlsx"))).name
        ext = Path(name).suffix.lower()
        if ext not in (".csv", ".xls", ".xlsx"):
            raise ValueError("仅支持 CSV、XLS、XLSX")
        # Keep the original filename on disk while isolating each task in its
        # own directory to avoid collisions between uploads with the same name.
        task_upload_dir = legacy.UPLOADS / task_id
        task_upload_dir.mkdir(parents=True, exist_ok=True)
        original_path = task_upload_dir / name
        original_path.write_bytes(await request.body())
        path, sheets = legacy.inspect_upload(original_path)
        source_artifact = None
        storage = get_storage()
        if storage is not None:
            source_artifact = storage.upload_file(
                original_path,
                f"{legacy.task_object_prefix(task)}/source/{name}",
            )
        task.update({"path": path, "source_path": original_path, "original_name": name, "sheets": sheets, "source_artifact": source_artifact})
        return {
            "sheets": sheets,
            "received": {"name": name, "size": path.stat().st_size, "sizeMB": round(path.stat().st_size / 1024 / 1024, 1)},
        }
    except Exception as exc:
        fail(exc)


@app.post("/api/select-sheet", operation_id="selectSheet")
def select_sheet(body: SheetRequest, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        task = owned_task(body.taskId, user)
        headers, rows = legacy.read_table(task["path"], body.sheet, body.headerRow)
        source_key = legacy.hashlib.sha256("|".join(map(legacy.norm, headers)).encode()).hexdigest()
        task.update({"sheet": body.sheet, "header_row": body.headerRow, "headers": headers, "rows": rows, "source_key": source_key})
        targets = legacy.template_info(task["kind"])["headers"]
        return {"headers": headers, "rows": len(rows), "suggestions": legacy.mapping_suggestions(headers, targets, rows, source_key), "targets": targets}
    except Exception as exc:
        fail(exc)


@app.post("/api/mapping", operation_id="saveMapping")
def mapping(body: MappingRequest, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        task = owned_task(body.taskId, user)
        task["mapping"] = body.mapping
        reviews, errors = legacy.estate_review(task)
        return {"reviews": reviews, "errors": errors, "autoCount": len(task.get("estate_auto", {}))}
    except Exception as exc:
        fail(exc)


@app.post("/api/review", operation_id="reviewEstate")
def review(body: ReviewRequest, user: User = Depends(ready_user)) -> dict[str, bool]:
    try:
        task = owned_task(body.taskId, user)
        for item in task.get("estate_reviews", []):
            item["selected"] = body.selected.get(item.get("key", item["raw"]), body.selected.get(item["raw"], ""))
        task["entrust_date"] = body.entrustDate or task["entrust_date"]
        legacy.save_rules(task)
        return {"ok": True}
    except Exception as exc:
        fail(exc)


@app.post("/api/building-review", operation_id="reviewBuilding")
def building_review(body: ReviewRequest, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        task = owned_task(body.taskId, user)
        return {"reviews": legacy.building_review(task, body.selected)}
    except Exception as exc:
        fail(exc)


@app.post("/api/building-confirm", operation_id="confirmBuilding")
def building_confirm(body: ReviewRequest, user: User = Depends(ready_user)) -> dict[str, bool]:
    try:
        task = owned_task(body.taskId, user)
        for item in task.get("building_reviews", []):
            item["selected"] = body.selected.get(item["key"], "")
        task["entrust_date"] = body.entrustDate or task["entrust_date"]
        if body.persistRules:
            legacy.save_rules(task)
        return {"ok": True}
    except Exception as exc:
        fail(exc)


@app.post("/api/export", operation_id="exportTask")
def export(body: ExportRequest, user: User = Depends(ready_user)) -> dict[str, Any]:
    try:
        return legacy.build_output(owned_task(body.taskId, user), body.cleanOnly)
    except Exception as exc:
        fail(exc)


@app.get("/download/{token}", response_model=None, operation_id="downloadFile")
def download(token: str, _admin: User = Depends(admin_user)) -> FileResponse | RedirectResponse:
    path = legacy.resolve_download(token)
    if path is None or not path.exists() or not legacy.is_managed_path(path):
        return RedirectResponse(url="/?download=missing", status_code=302)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=path.name)


if legacy.STATIC.exists():
    app.mount("/", StaticFiles(directory=legacy.STATIC, html=True), name="static")
