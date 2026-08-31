import os
import shutil
import tempfile
from pathlib import Path

import pytest


TEST_ROOT = Path(tempfile.gettempdir()) / f"housing-cleaner-tests-{os.getpid()}"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_ROOT / 'test.sqlite3'}"
os.environ["WORK_DIR"] = str(TEST_ROOT / "work")


@pytest.fixture(scope="session", autouse=True)
def isolated_test_workspace():
    yield
    shutil.rmtree(TEST_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def disable_external_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试不触碰部署环境中的 MinIO，外部存储由专门的集成测试覆盖。"""
    monkeypatch.setenv("MINIO_ENABLED", "false")
