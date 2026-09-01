import os
import shutil
import tempfile
from pathlib import Path

import pytest


TEST_ROOT = Path(tempfile.gettempdir()) / f"housing-cleaner-tests-{os.getpid()}"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.sqlite3'}"
os.environ["WORK_DIR"] = str(TEST_ROOT / "work")
os.environ["APP_ENV"] = "test"
os.environ["STORAGE_BACKEND"] = "disabled"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_INITIAL_PASSWORD"] = "test-admin-password"


@pytest.fixture(scope="session", autouse=True)
def isolated_test_workspace():
    yield
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def disable_external_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """单元测试不触碰 MinIO 或 CloudBase，外部存储由专门的集成测试覆盖。"""
    monkeypatch.setenv("STORAGE_BACKEND", "disabled")
    monkeypatch.setenv("MINIO_ENABLED", "false")
