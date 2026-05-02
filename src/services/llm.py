"""Клиент к LiteLLM (роутеру моделей).

Два метода: cheap (Haiku, для рутины) и creative (Sonnet, для контента).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            key = self._settings.litellm_master_key.get_secret_value()
            self._client = httpx.AsyncClient(
                base_url=self._settings.litellm_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(120.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chat(
        self,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 800,
        temperature: float = 0.7,
    ) -> str:
        """Один-шотовый chat-completion. Возвращает text content."""
        client = await self._ensure_client()
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = await client.post("/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"LiteLLM error: {data['error']}")
        return data["choices"][0]["message"]["content"]

    async def cheap(self, system: str, user: str, max_tokens: int = 400) -> str:
        """Haiku — для рутины (классификация, парсинг, summary)."""
        return await self.chat("cheap", system, user, max_tokens=max_tokens, temperature=0.3)

    async def creative(self, system: str, user: str, max_tokens: int = 1500) -> str:
        """Sonnet — для контента (длинная проза, бренд-голос)."""
        return await self.chat("creative", system, user, max_tokens=max_tokens, temperature=0.7)

    async def premium(self, system: str, user: str, max_tokens: int = 2000) -> str:
        """Opus — для финальной итерации, особенно длинных и тонких текстов."""
        return await self.chat("premium", system, user, max_tokens=max_tokens, temperature=0.7)
