"""Транскрибация аудио через локальный Whisper-сервис."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class TranscribeService:
    """Обёртка над whisper-asr-webservice (REST API на /asr)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.whisper_url.rstrip("/"),
                timeout=httpx.Timeout(120.0),  # модель может думать на длинных файлах
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def transcribe(self, file_path: Path, language: str = "ru") -> str:
        """Транскрибирует аудио-файл, возвращает text. Пустая строка если ничего не распозналось."""
        client = await self._ensure_client()
        with open(file_path, "rb") as f:
            files = {"audio_file": (file_path.name, f.read(), "audio/ogg")}
        try:
            r = await client.post(
                "/asr",
                params={"output": "json", "language": language, "task": "transcribe"},
                files=files,
            )
            r.raise_for_status()
            data = r.json()
            return (data.get("text") or "").strip()
        except httpx.HTTPError as e:
            logger.exception("Whisper transcribe failed")
            raise RuntimeError(f"Whisper error: {e}") from e
