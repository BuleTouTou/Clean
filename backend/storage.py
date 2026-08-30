from __future__ import annotations

import mimetypes
import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

from dotenv import load_dotenv
from minio import Minio


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class StorageConfigError(RuntimeError):
    """MinIO 配置不完整或无效。"""


class MinioStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool, public_endpoint: str | None = None):
        parsed = urlsplit(endpoint if "://" in endpoint else f"http://{endpoint}")
        if not parsed.netloc:
            raise StorageConfigError("MINIO_ENDPOINT 配置无效")
        self.endpoint = urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))
        self.client = Minio(parsed.netloc, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = bucket
        self.public_endpoint = (public_endpoint or self.endpoint).rstrip("/")

    def upload_file(self, path: Path, object_key: str) -> dict[str, str | int | None]:
        if not path.is_file():
            raise FileNotFoundError(path)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        result = self.client.fput_object(self.bucket, object_key, str(path), content_type=content_type)
        return {
            "bucket": self.bucket,
            "objectKey": object_key,
            "url": f"{self.public_endpoint}/{quote(self.bucket)}/{quote(object_key, safe='/')}",
            "etag": result.etag,
            "size": path.stat().st_size,
            "contentType": content_type,
        }

    def presigned_get_url(self, object_key: str, expires_seconds: int = 3600) -> str:
        return self.client.presigned_get_object(
            self.bucket,
            object_key,
            expires=timedelta(seconds=expires_seconds),
        )


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def get_storage() -> MinioStorage | None:
    """按环境变量创建存储客户端；未启用时返回 None，便于本地测试。"""
    access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_USERNAME", "")
    secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_PASSWORD", "")
    bucket = os.getenv("MINIO_BUCKET", "").strip()
    enabled = _env_flag("MINIO_ENABLED", bool(access_key and secret_key and bucket))
    if not enabled:
        return None
    endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
    if not endpoint or not access_key or not secret_key or not bucket:
        raise StorageConfigError("MinIO 已启用，但 MINIO_ENDPOINT、MINIO_ACCESS_KEY、MINIO_SECRET_KEY、MINIO_BUCKET 未完整配置")
    secure = _env_flag("MINIO_SECURE", endpoint.startswith("https://"))
    return MinioStorage(endpoint, access_key, secret_key, bucket, secure, os.getenv("MINIO_PUBLIC_ENDPOINT"))
