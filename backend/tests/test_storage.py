from __future__ import annotations

from pathlib import Path

import pytest

from backend.storage import CloudBaseStorage, StorageConfigError, get_storage


class FakeBody:
    def __init__(self, content: bytes):
        self.content = content
        self.offset = 0
        self.closed = False

    def get_raw_stream(self):
        return self

    def read(self, size: int) -> bytes:
        chunk = self.content[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk

    def close(self) -> None:
        self.closed = True


class FakeCosClient:
    def __init__(self):
        self.upload: dict[str, object] | None = None
        self.download: dict[str, object] | None = None
        self.body = FakeBody(b"abcdef")

    def upload_file(self, **kwargs):
        self.upload = kwargs
        return {"ETag": '"abc123"'}

    def get_object(self, **kwargs):
        self.download = kwargs
        return {"Body": self.body}


def test_cloudbase_storage_applies_clean_prefix(tmp_path: Path) -> None:
    source = tmp_path / "report.xlsx"
    source.write_bytes(b"xlsx")
    client = FakeCosClient()
    storage = CloudBaseStorage(
        region="ap-shanghai",
        secret_id="test-id",
        secret_key="test-key",
        bucket="example-123",
        prefix="clean",
        client=client,
    )

    uploaded = storage.upload_file(source, "housing-cleaner/users/admin/task/report.xlsx")

    assert uploaded["objectKey"] == "clean/housing-cleaner/users/admin/task/report.xlsx"
    assert uploaded["url"] == "cos://example-123/clean/housing-cleaner/users/admin/task/report.xlsx"
    assert uploaded["etag"] == "abc123"
    assert client.upload is not None
    assert client.upload["Key"] == uploaded["objectKey"]


def test_cloudbase_storage_streams_prefixed_object() -> None:
    client = FakeCosClient()
    storage = CloudBaseStorage(
        region="ap-shanghai",
        secret_id="test-id",
        secret_key="test-key",
        bucket="example-123",
        prefix="clean",
        client=client,
    )

    assert b"".join(storage.iter_object("clean/reports/a.xlsx", chunk_size=2)) == b"abcdef"
    assert client.download == {"Bucket": "example-123", "Key": "clean/reports/a.xlsx"}
    assert client.body.closed is True


def test_cloudbase_backend_requires_server_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "cloudbase")
    monkeypatch.setenv("CLOUDBASE_STORAGE_BUCKET", "example-123")
    monkeypatch.delenv("TENCENTCLOUD_SECRETID", raising=False)
    monkeypatch.delenv("TENCENTCLOUD_SECRETKEY", raising=False)

    with pytest.raises(StorageConfigError, match="CloudBase 存储配置不完整"):
        get_storage()
