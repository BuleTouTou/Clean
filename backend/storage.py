from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

from minio import Minio

from .config import load_environment


load_environment()


class StorageConfigError(RuntimeError):
    """Object storage configuration is incomplete or invalid."""


class ObjectStorage(Protocol):
    def upload_file(self, path: Path, object_key: str) -> dict[str, str | int | None]: ...

    def iter_object(self, object_key: str, chunk_size: int = 1024 * 1024): ...


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

    def iter_object(self, object_key: str, chunk_size: int = 1024 * 1024):
        """Stream a private object through the application without exposing an internal MinIO hostname."""
        response = self.client.get_object(self.bucket, object_key)
        try:
            while chunk := response.read(chunk_size):
                yield chunk
        finally:
            response.close()
            response.release_conn()


class CloudBaseStorage:
    """Store objects in the COS bucket attached to the CloudBase environment."""

    def __init__(
        self,
        region: str,
        secret_id: str,
        secret_key: str,
        bucket: str,
        prefix: str = "",
        token: str | None = None,
        client: Any | None = None,
    ):
        self.region = region
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        if client is None:
            try:
                from qcloud_cos import CosConfig, CosS3Client
            except ImportError as exc:  # pragma: no cover - deployment dependency guard
                raise StorageConfigError("CloudBase 存储需要安装 cos-python-sdk-v5") from exc
            config = CosConfig(
                Region=region,
                SecretId=secret_id,
                SecretKey=secret_key,
                Token=token or None,
                Scheme="https",
            )
            client = CosS3Client(config)
        self.client = client

    def _object_key(self, object_key: str) -> str:
        normalized = object_key.strip().lstrip("/")
        if not normalized or any(part in {".", ".."} for part in normalized.split("/")):
            raise StorageConfigError("对象路径无效")
        if self.prefix and normalized != self.prefix and not normalized.startswith(f"{self.prefix}/"):
            return f"{self.prefix}/{normalized}"
        return normalized

    def upload_file(self, path: Path, object_key: str) -> dict[str, str | int | None]:
        if not path.is_file():
            raise FileNotFoundError(path)
        key = self._object_key(object_key)
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        result = self.client.upload_file(
            Bucket=self.bucket,
            LocalFilePath=str(path),
            Key=key,
            ContentType=content_type,
        )
        etag = str(result.get("ETag", "")).strip('"') or None
        return {
            "bucket": self.bucket,
            "objectKey": key,
            "url": f"cos://{self.bucket}/{quote(key, safe='/')}",
            "etag": etag,
            "size": path.stat().st_size,
            "contentType": content_type,
        }

    def iter_object(self, object_key: str, chunk_size: int = 1024 * 1024):
        key = self._object_key(object_key)
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"]
        stream = body.get_raw_stream()
        try:
            while chunk := stream.read(chunk_size):
                yield chunk
        finally:
            close = getattr(body, "close", None)
            if callable(close):
                close()


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _storage_backend() -> str:
    configured = os.getenv("STORAGE_BACKEND", "").strip().lower()
    if configured:
        return configured
    access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_USERNAME", "")
    secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_PASSWORD", "")
    bucket = os.getenv("MINIO_BUCKET", "").strip()
    return "minio" if _env_flag("MINIO_ENABLED", bool(access_key and secret_key and bucket)) else "disabled"


def get_storage() -> ObjectStorage | None:
    """Select MinIO for development/test and CloudBase COS for production."""
    backend = _storage_backend()
    if backend in {"", "disabled", "none", "off"}:
        return None

    if backend == "minio":
        access_key = os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_USERNAME", "")
        secret_key = os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_PASSWORD", "")
        bucket = os.getenv("MINIO_BUCKET", "").strip()
        endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
        if not endpoint or not access_key or not secret_key or not bucket:
            raise StorageConfigError(
                "MinIO 已启用，但 MINIO_ENDPOINT、MINIO_ACCESS_KEY、MINIO_SECRET_KEY、MINIO_BUCKET 未完整配置"
            )
        secure = _env_flag("MINIO_SECURE", endpoint.startswith("https://"))
        return MinioStorage(endpoint, access_key, secret_key, bucket, secure, os.getenv("MINIO_PUBLIC_ENDPOINT"))

    if backend in {"cloudbase", "cos"}:
        region = os.getenv("CLOUDBASE_STORAGE_REGION", "ap-shanghai").strip()
        bucket = os.getenv("CLOUDBASE_STORAGE_BUCKET", "").strip()
        prefix = os.getenv("CLOUDBASE_STORAGE_PREFIX", "clean").strip()
        secret_id = os.getenv("TENCENTCLOUD_SECRETID", "").strip()
        secret_key = os.getenv("TENCENTCLOUD_SECRETKEY", "").strip()
        token = os.getenv("TENCENTCLOUD_SESSIONTOKEN", "").strip() or None
        if not region or not bucket or not secret_id or not secret_key:
            raise StorageConfigError(
                "CloudBase 存储配置不完整：需要 CLOUDBASE_STORAGE_REGION、CLOUDBASE_STORAGE_BUCKET、"
                "TENCENTCLOUD_SECRETID、TENCENTCLOUD_SECRETKEY"
            )
        return CloudBaseStorage(region, secret_id, secret_key, bucket, prefix, token)

    raise StorageConfigError(f"不支持的 STORAGE_BACKEND：{backend}")
