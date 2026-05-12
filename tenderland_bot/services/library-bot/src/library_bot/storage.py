"""MinIO PDF streaming для отдачи в Telegram."""
from __future__ import annotations

import io
from urllib.parse import quote

from minio import Minio

from .settings import Settings


class Storage:
    def __init__(self, settings: Settings):
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket_brochures

    def get_pdf(self, object_key: str) -> tuple[io.BytesIO, int, str]:
        """Скачивает объект из MinIO в память и возвращает поток + размер + filename.

        object_key может быть полной MinIO-локацией ('product-brochures/agilent/file.pdf')
        или относительной ('agilent/file.pdf') — обрабатываем оба случая.
        """
        key = object_key
        # strip leading bucket prefix if present: 'product-brochures/...'
        if key.startswith(self._bucket + "/"):
            key = key[len(self._bucket) + 1:]
        # also strip s3:// scheme if any
        if key.startswith("s3://"):
            key = key.split("/", 3)[-1]

        response = None
        try:
            response = self._client.get_object(self._bucket, key)
            data = response.read()
            size = len(data)
            filename = key.rsplit("/", 1)[-1]
            return io.BytesIO(data), size, filename
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    def stat(self, object_key: str) -> int | None:
        """Возвращает размер объекта или None если не найден."""
        key = object_key
        if key.startswith(self._bucket + "/"):
            key = key[len(self._bucket) + 1:]
        try:
            st = self._client.stat_object(self._bucket, key)
            return st.size
        except Exception:
            return None
