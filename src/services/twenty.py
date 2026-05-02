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
        # Сортируем по capturedAt desc, обрезаем до limit
        result.sort(key=lambda r: r.get("capturedAt") or "", reverse=True)
        return result[:limit]

    async def get_idea(self, idea_id: str) -> dict[str, Any] | None:
        """Достать Idea по UUID, со связанными Direction/Topic."""
        query = """
        query GetIdea($id: UUID!) {
          ideas(filter: { id: { eq: $id } }) {
            edges {
              node {
                id name description lifecycle source capturedAt
                topic { id name }
                direction { id name }
              }
            }
          }
        }
        """
        data = await self.gql(query, {"id": idea_id})
        edges = data["ideas"]["edges"]
        if not edges:
            return None
        return edges[0]["node"]

    async def list_channels(self, enabled_only: bool = True) -> list[dict[str, Any]]:
        """Все каналы (или только enabled=true)."""
        query = """
        query ListChannels {
          channels {
            edges {
              node { id name code channelType handle charLimit defaultTone enabled }
            }
          }
        }
        """
        data = await self.gql(query)
        result = [e["node"] for e in data["channels"]["edges"]]
        if enabled_only:
            result = [c for c in result if c.get("enabled")]
        return result

    async def get_channel_by_code(self, code: str) -> dict[str, Any] | None:
        for ch in await self.list_channels(enabled_only=False):
            if ch.get("code") == code:
                return ch
        return None

    async def create_draft(
        self,
        idea_id: str,
        channel_id: str,
        body: str,
        tone: str = "2",
        length: str = "medium",
        topic_id: str | None = None,
        author: str = "agent:producer_v1",
        llm_model: str = "creative",
    ) -> dict[str, Any]:
        """Создаёт Draft в Twenty, связанный с Idea и Channel."""
        first_line = body.strip().split("\n", 1)[0].strip()
        name = first_line[:80] + ("..." if len(first_line) > 80 else "")
        if not name:
            name = "(без заголовка)"

        data: dict[str, Any] = {
            "name": name,
            "body": body,
            "tone": tone,
            "length": length,
            "lifecycle": "review",
            "author": author,
            "llmModel": llm_model,
            "version": 1,
            "ideaId": idea_id,
            "channelId": channel_id,
        }
        if topic_id:
            data["topicId"] = topic_id

        query = """
        mutation CreateDraft($data: DraftCreateInput!) {
          createDraft(data: $data) {
            id name lifecycle channelId
          }
        }
        """
        res = await self.gql(query, {"data": data})
        return res["createDraft"]

    async def list_drafts(self, lifecycle: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        query = """
        query ListDrafts {
          drafts {
            edges {
              node {
                id name lifecycle author createdAt
                channel { id name code }
                idea { id name }
              }
            }
          }
        }
        """
        data = await self.gql(query)
        result = [e["node"] for e in data["drafts"]["edges"]]
        if lifecycle:
            result = [r for r in result if r.get("lifecycle") == lifecycle]
        result.sort(key=lambda r: r.get("createdAt") or "", reverse=True)
        return result[:limit]

    async def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        query = """
        query GetDraft($id: UUID!) {
          drafts(filter: { id: { eq: $id } }) {
            edges {
              node {
                id name body tone length lifecycle author llmModel version
                idea { id name description }
                topic { id name }
                channel { id name code handle channelType charLimit defaultTone }
              }
            }
          }
        }
        """
        data = await self.gql(query, {"id": draft_id})
        edges = data["drafts"]["edges"]
        if not edges:
            return None
        return edges[0]["node"]

    async def find_drafts_by_partial_id(self, partial_id: str) -> list[dict[str, Any]]:
        """Найти drafts по startswith UUID. Полезно для коротких ID в команд бота."""
        if len(partial_id) == 36:
            d = await self.get_draft(partial_id)
            return [d] if d else []
        all_drafts = await self.list_drafts(limit=100)
        return [d for d in all_drafts if d.get("id", "").startswith(partial_id)]

    async def update_idea_lifecycle(self, idea_id: str, lifecycle: str) -> None:
        query = """
        mutation UpdateIdea($id: UUID!, $data: IdeaUpdateInput!) {
          updateIdea(id: $id, data: $data) { id lifecycle }
        }
        """
        from datetime import datetime, timezone
        data: dict[str, Any] = {"lifecycle": lifecycle}
        if lifecycle == "processed":
            data["processedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        await self.gql(query, {"id": idea_id, "data": data})
