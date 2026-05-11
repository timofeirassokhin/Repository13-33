"""MinIO storage helpers."""
from __future__ import annotations

import io

from minio import Minio

from catalog_crawler.settings import settings


def get_minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def check_minio() -> bool:
    try:
        client = get_minio()
        return client.bucket_exists(settings.minio_raw_bucket)
    except Exception as e:
        print(f"  minio error: {e}")
        return False


def put_object(bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = get_minio()
    client.put_object(
        bucket,
        key,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"{bucket}/{key}"
