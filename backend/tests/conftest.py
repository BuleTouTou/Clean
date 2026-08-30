import pytest


@pytest.fixture(autouse=True)
def disable_external_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试不触碰部署环境中的 MinIO，外部存储由专门的集成测试覆盖。"""
    monkeypatch.setenv("MINIO_ENABLED", "false")
