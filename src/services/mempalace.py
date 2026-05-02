"""HTTP-клиент к нашему server-side MemPalace (infra/mempalace/service.py)."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


WINGS = [
    "books",
    "articles",
    "13-33pubs",
    "13-33scenarios",
    "13-33interviews",
    "13-33main",
    "13-33drafts",
    "misc",
]


class MempalaceClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.mempalace_url.rstrip("/"),
                timeout=httpx.Timeout(60.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health(self) -> dict[str, Any]:
        c = await self._ensure_client()
        r = await c.get("/health")
        r.raise_for_status()
        return r.json()

    async def list_wings(self) -> list[dict[str, Any]]:
        c = await self._ensure_client()
        r = await c.get("/wings")
        r.raise_for_status()
        return r.json().get("wings", [])

    async def add_drawer(
        self,
        content: str,
        wing: str,
        room: str = "default",
        title: str | None = None,
        source_file: str | None = None,
        added_by: str = "telegram_bot",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        c = await self._ensure_client()
        payload: dict[str, Any] = {
            "content": content,
            "wing": wing,
            "room": room,
            "added_by": added_by,
        }
        if title:
            payload["title"] = title
        if source_file:
            payload["source_file"] = source_file
        if tags:
            payload["tags"] = tags
        r = await c.post("/drawer", json=payload)
        r.raise_for_status()
        return r.json()

    async def search(
        self,
        query: str,
        wing: str | None = None,
        room: str | None = None,
        n_results: int = 5,
        max_distance: float = 1.5,
    ) -> list[dict[str, Any]]:
        c = await self._ensure_client()
        payload: dict[str, Any] = {
            "query": query,
            "n_results": n_results,
            "max_distance": max_distance,
        }
        if wing:
            payload["wing"] = wing
        if room:
            payload["room"] = room
        r = await c.post("/search", json=payload)
        r.raise_for_status()
        raw = r.json().get("results", [])
        # Defensive normalization — некоторые версии mempalace возвращают строки,
        # новые — dict'и. Поддерживаем оба формата.
        normalized: list[dict[str, Any]] = []
        for res in raw:
            if isinstance(res, dict):
                normalized.append(res)
            elif isinstance(res, str):
                normalized.append({
                    "id": "",
                    "content": res,
                    "metadata": {},
                    "distance": 0.0,
                })
            # игнорируем остальное
        # Отфильтровать system_init placeholder'ы
        return [
            res for res in normalized
            if (res.get("metadata") or {}).get("added_by") != "system_init"
        ]

    async def get_drawer(self, drawer_id: str) -> dict[str, Any] | None:
        c = await self._ensure_client()
        r = await c.get(f"/drawer/{drawer_id}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
