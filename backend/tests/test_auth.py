from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app import app
from backend.core import task_object_prefix
from backend.db import User, get_session_factory, save_report


def login(client: TestClient, username: str, password: str) -> dict:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["user"]


def sample_report(name: str) -> dict:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "原始文件名": name,
        "委托日期": "2026-09-01",
        "任务开始时间": now,
        "完成时间": now,
        "原始记录数": 1,
        "最终输出记录数": 1,
        "阻断异常数量": 0,
        "审计记录": [],
    }


def test_user_object_prefix() -> None:
    assert task_object_prefix({"username": "alice", "id": "task123"}) == "housing-cleaner/users/alice/task123"


def test_first_login_and_report_isolation() -> None:
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/status").status_code == 401

    with TestClient(app) as admin:
        admin_user = login(admin, "admin", "test-admin-password")
        assert admin_user["role"] == "admin"
        alice_response = admin.post(
            "/api/users",
            json={"username": "alice", "name": "爱丽丝", "initialPassword": "alice-initial-123"},
        )
        bob_response = admin.post(
            "/api/users",
            json={"username": "bob", "name": "鲍勃", "initialPassword": "bob-initial-123"},
        )
        assert alice_response.status_code == bob_response.status_code == 200
        alice = alice_response.json()["user"]
        bob = bob_response.json()["user"]
        users = admin.get("/api/users").json()["items"]
        assert {item["username"] for item in users} >= {"admin", "alice", "bob"}
        assert all("password_hash" not in item and "password" not in item for item in users)

    Session = get_session_factory()
    with Session() as session:
        stored_alice = session.scalar(select(User).where(User.username == "alice"))
        assert stored_alice is not None and stored_alice.password_hash.startswith("$2")

    alice_report_id = save_report(alice["id"], "alice-task", "sale", sample_report("alice.xlsx"), None, 0)
    bob_report_id = save_report(bob["id"], "bob-task", "rent", sample_report("bob.xlsx"), None, 0)

    with TestClient(app) as alice_client:
        first_login = login(alice_client, "alice", "alice-initial-123")
        assert first_login["mustChangePassword"] is True
        assert alice_client.get("/api/status").status_code == 403
        changed = alice_client.post(
            "/api/auth/change-password",
            json={"currentPassword": "alice-initial-123", "newPassword": "alice-final-456"},
        )
        assert changed.status_code == 200, changed.text
        assert alice_client.get("/api/status").status_code == 200
        assert alice_client.get("/api/users").status_code == 403
        reports = alice_client.get("/api/reports").json()
        assert [item["id"] for item in reports["items"]] == [alice_report_id]
        searched_reports = alice_client.get("/api/reports", params={"ownerSearch": "bob"}).json()
        assert [item["id"] for item in searched_reports["items"]] == [alice_report_id]
        assert alice_client.get(f"/api/reports/{bob_report_id}").status_code == 404

    with TestClient(app) as bob_client:
        login(bob_client, "bob", "bob-initial-123")
        changed = bob_client.post(
            "/api/auth/change-password",
            json={"currentPassword": "bob-initial-123", "newPassword": "bob-final-456"},
        )
        assert changed.status_code == 200
        reports = bob_client.get("/api/reports").json()
        assert [item["id"] for item in reports["items"]] == [bob_report_id]

    with TestClient(app) as admin:
        login(admin, "admin", "test-admin-password")
        report_ids = {item["id"] for item in admin.get("/api/reports").json()["items"]}
        assert {alice_report_id, bob_report_id}.issubset(report_ids)
        by_username = admin.get("/api/reports", params={"ownerSearch": "ALI"}).json()
        assert [item["id"] for item in by_username["items"]] == [alice_report_id]
        by_name = admin.get("/api/reports", params={"ownerSearch": "鲍"}).json()
        assert [item["id"] for item in by_name["items"]] == [bob_report_id]
