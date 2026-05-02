"""GraphQL-клиент к Twenty CRM (для интейка идей и в будущем — Draft/Publication)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class TwentyClient:
    """Лёгкая обёртка над Twenty GraphQL API.

    Соответствует Twenty 2.x: мутации `create<Singular>(data: <Singular>CreateInput)`,
    запросы `<plural> { edges { node { ... } } }`.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            api_key = self._settings.twenty_api_key.get_secret_value()
            if not api_key:
                raise RuntimeError("TWENTY_API_KEY не задан в окружении бота")
            self._client = httpx.AsyncClient(
                base_url=self._settings.twenty_api_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def gql(self, query: str, variables: dict | None = None) -> dict[str, Any]:
        client = await self._ensure_client()
        body: dict[str, Any] = {"query": query}
        if variables:
            body["variables"] = variables
        r = await client.post("/graphql", json=body)
        r.raise_for_status()
        data = r.json()
        if data.get("errors"):
            logger.error("Twenty GraphQL error: %s", data["errors"])
            raise RuntimeError(f"Twenty error: {data['errors']}")
        return data["data"]

    async def create_idea(
        self,
        description: str,
        telegram_user_id: int,
        source: str = "telegram_bot",
    ) -> dict[str, Any]:
        """Создаёт Idea в Twenty. name — авто из первой строки (80 chars cap)."""
        first_line = description.strip().split("\n", 1)[0].strip()
        name = first_line[:80] + ("..." if len(first_line) > 80 else "")
        if not name:
            name = "(без заголовка)"

        # Twenty требует формат "YYYY-MM-DDTHH:mm:ssZ" (без миллисекунд, Z вместо +00:00)
        captured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        query = """
        mutation CreateIdea($data: IdeaCreateInput!) {
          createIdea(data: $data) {
            id
            name
            description
            lifecycle
            createdAt
          }
        }
        """
        variables = {
            "data": {
                "name": name,
                "description": description,
                "source": source,
                "lifecycle": "raw",
                "createdByExternalId": str(telegram_user_id),
                "capturedAt": captured_at,
            }
        }
        data = await self.gql(query, variables)
        return data["createIdea"]

    async def list_ideas(self, status: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """Список Idea, опционально с фильтром по lifecycle."""
        query = """
        query ListIdeas {
          ideas {
            edges { node { id name description lifecycle source capturedAt } }
          }
        }
        """
        data = await self.gql(query)
        edges = data["ideas"]["edges"]
        result = [e["node"] for e in edges]
        if status:
            result = [r for r in result if r.get("lifecycle") == status]
        return result[:limit]
