from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from sqlalchemy import delete, select

from .db import User, UserSession, get_session_factory


UTC = timezone.utc
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")


class AuthError(ValueError):
    pass


def normalize_username(value: str) -> str:
    username = str(value or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise AuthError("账号只能包含字母、数字、点、下划线或短横线，长度为 3–50 位")
    return username


def validate_password(value: str) -> str:
    password = str(value or "")
    if len(password) < 8:
        raise AuthError("密码至少需要 8 位")
    if len(password.encode("utf-8")) > 72:
        raise AuthError("密码过长，请控制在 72 个字节以内")
    return password


def hash_password(password: str) -> str:
    return bcrypt.hashpw(validate_password(password).encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except (ValueError, UnicodeError):
        return False


def serialize_user(user: User) -> dict[str, Any]:
    created_at = user.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "role": user.role,
        "mustChangePassword": user.must_change_password,
        "isActive": user.is_active,
        "createdAt": created_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def ensure_admin() -> None:
    username = normalize_username(os.getenv("ADMIN_USERNAME", "admin"))
    password = os.getenv("ADMIN_INITIAL_PASSWORD", "")
    name = os.getenv("ADMIN_NAME", "系统管理员").strip() or "系统管理员"
    if not password:
        raise RuntimeError("缺少 ADMIN_INITIAL_PASSWORD，无法初始化管理员账号")
    Session = get_session_factory()
    with Session.begin() as session:
        existing = session.scalar(select(User).where(User.username == username))
        if existing is None:
            session.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    name=name,
                    role="admin",
                    must_change_password=False,
                    is_active=True,
                )
            )


def authenticate(username: str, password: str) -> User | None:
    try:
        normalized = normalize_username(username)
    except AuthError:
        return None
    Session = get_session_factory()
    with Session() as session:
        user = session.scalar(select(User).where(User.username == normalized))
        if user is None or not user.is_active or not verify_password(password, user.password_hash):
            return None
        session.expunge(user)
        return user


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    days = max(1, min(30, int(os.getenv("SESSION_DAYS", "7"))))
    Session = get_session_factory()
    with Session.begin() as session:
        session.add(
            UserSession(
                user_id=user_id,
                token_hash=_token_hash(token),
                expires_at=datetime.now(UTC) + timedelta(days=days),
            )
        )
    return token


def user_from_session(token: str | None) -> User | None:
    if not token:
        return None
    Session = get_session_factory()
    with Session.begin() as session:
        result = session.execute(
            select(UserSession, User)
            .join(User, UserSession.user_id == User.id)
            .where(UserSession.token_hash == _token_hash(token))
        ).one_or_none()
        if result is None:
            return None
        user_session, user = result
        expires_at = user_session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= datetime.now(UTC) or not user.is_active:
            session.delete(user_session)
            return None
        session.expunge(user)
        return user


def revoke_session(token: str | None) -> None:
    if not token:
        return
    Session = get_session_factory()
    with Session.begin() as session:
        session.execute(delete(UserSession).where(UserSession.token_hash == _token_hash(token)))


def change_password(user_id: int, current_password: str, new_password: str) -> None:
    Session = get_session_factory()
    with Session.begin() as session:
        user = session.get(User, user_id)
        if user is None or not verify_password(current_password, user.password_hash):
            raise AuthError("当前密码不正确")
        if verify_password(new_password, user.password_hash):
            raise AuthError("新密码不能与当前密码相同")
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.updated_at = datetime.now(UTC)
        session.execute(delete(UserSession).where(UserSession.user_id == user_id))


def create_user(username: str, name: str, initial_password: str) -> dict[str, Any]:
    normalized = normalize_username(username)
    display_name = str(name or "").strip()
    if not display_name:
        raise AuthError("姓名不能为空")
    Session = get_session_factory()
    with Session.begin() as session:
        if session.scalar(select(User.id).where(User.username == normalized)) is not None:
            raise AuthError("该账号已存在")
        user = User(
            username=normalized,
            password_hash=hash_password(initial_password),
            name=display_name,
            role="user",
            must_change_password=True,
            is_active=True,
        )
        session.add(user)
        session.flush()
        return serialize_user(user)


def list_users() -> list[dict[str, Any]]:
    Session = get_session_factory()
    with Session() as session:
        users = session.scalars(select(User).order_by(User.id)).all()
        return [serialize_user(user) for user in users]


def reset_user_password(user_id: int, initial_password: str) -> dict[str, Any]:
    Session = get_session_factory()
    with Session.begin() as session:
        user = session.get(User, user_id)
        if user is None:
            raise AuthError("用户不存在")
        if user.role == "admin":
            raise AuthError("不能通过普通用户管理接口重置管理员密码")
        user.password_hash = hash_password(initial_password)
        user.must_change_password = True
        user.updated_at = datetime.now(UTC)
        session.execute(delete(UserSession).where(UserSession.user_id == user_id))
        session.flush()
        return serialize_user(user)
