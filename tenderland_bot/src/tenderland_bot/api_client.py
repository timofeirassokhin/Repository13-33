"""Synchronous Tenderland API client.

Covers what we need for the CLI:
  - GET /Api/v1/User/GetStatistic
  - GET /Api/v1/Dictionary/GetAutosearchList
  - GET /Api/v1/Export/Create
  - GET /Api/v1/Export/Get  (paged)
  - GET /Api/v1/File/GetAll (zip archive of all docs for a tender)

Limits to remember (free tier):
  - 1 unit per tender/lot returned
  - 1 unit per file inside the GetAll archive
  - 1000 requests + 1000 units per day on this key (paid tier)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urljoin

import httpx


@dataclass
class Autosearch:
    id: int
    name: str
    workspace_id: int
    workspace_name: str

    @classmethod
    def from_api(cls, item: dict[str, Any]) -> "Autosearch":
        return cls(
            id=item["Id"],
            name=item["Name"],
            workspace_id=item.get("WorkspaceId", 0),
            workspace_name=item.get("WorkspaceName", ""),
        )


@dataclass
class ExportTask:
    id: int
    total_count: int
    create_date: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "ExportTask":
        return cls(
            id=payload["Id"],
            total_count=int(payload.get("TotalCount", 0)),
            create_date=payload.get("CreateDate", ""),
        )


class TenderlandAPIError(RuntimeError):
    """Raised when Tenderland API returns an error response."""

    def __init__(self, code: str, description: str, http_status: int):
        self.code = code
        self.description = description
        self.http_status = http_status
        super().__init__(f"[{http_status}] {code}: {description}")


class TenderlandClient:
    def __init__(self, api_key: str, base_url: str = "https://tenderland.ru", timeout: int = 120):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TenderlandClient":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    # ---------- low-level ----------

    def _url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        params = dict(params or {})
        params["apiKey"] = self.api_key
        params.setdefault("format", "json")
        r = self._client.get(self._url(path), params=params)
        return self._handle_json(r)

    @staticmethod
    def _handle_json(r: httpx.Response) -> Any:
        # Tenderland returns errors as JSON with HTTP 4xx/5xx and {Code, Description, Success}.
        try:
            data = r.json()
        except Exception:
            r.raise_for_status()
            raise
        if isinstance(data, dict) and data.get("Success") is False and data.get("Code"):
            raise TenderlandAPIError(
                code=str(data.get("Code")),
                description=str(data.get("Description", "")),
                http_status=r.status_code,
            )
        if r.status_code >= 400:
            r.raise_for_status()
        return data

    # ---------- public methods ----------

    def get_statistic(self) -> dict[str, Any]:
        return self._get_json("/Api/v1/User/GetStatistic")

    def list_autosearches(self) -> list[Autosearch]:
        data = self._get_json("/Api/v1/Dictionary/GetAutosearchList")
        return [Autosearch.from_api(it) for it in data.get("items", [])]

    def create_export(
        self,
        autosearch_id: int,
        *,
        export_view_id: int | None = None,
        limit: int | None = None,
        batch_size: int = 100,
        order_by: str | None = "tender_sysPublishDate.desc",
    ) -> ExportTask:
        params: dict[str, Any] = {
            "autosearchId": autosearch_id,
            "batchSize": batch_size,
        }
        if export_view_id is not None:
            params["exportViewId"] = export_view_id
        if limit is not None:
            params["limit"] = limit
        if order_by:
            params["orderBy"] = order_by
        payload = self._get_json("/Api/v1/Export/Create", params)
        return ExportTask.from_api(payload)

    def read_export_page(self, export_id: int, offset: int) -> list[dict[str, Any]]:
        data = self._get_json("/Api/v1/Export/Get", {"exportId": export_id, "offset": offset})
        return data.get("items", [])

    def iter_export(self, export_id: int, total_count: int, batch_size: int = 100) -> Iterator[dict[str, Any]]:
        """Yield every item from an export task, page by page."""
        offset = 0
        seen = 0
        # Tenderland enforces "no parallel reads on same export id" — sequential is mandatory.
        while seen < total_count:
            page = self.read_export_page(export_id, offset)
            if not page:
                break
            for it in page:
                yield it
                seen += 1
            offset += len(page)
            # Be nice to API — small pause between pages.
            time.sleep(0.1)

    def download_all_files(self, entity_id: str, dest_path: Path, entity_type_id: int = 1) -> int:
        """Download zip archive with all docs for a tender. Returns bytes written.

        Each file inside the archive consumes 1 data unit from daily/monthly limits.
        """
        url = self._url("/Api/v1/File/GetAll")
        params = {
            "entityId": entity_id,
            "entityTypeId": entity_type_id,
            "apiKey": self.api_key,
        }
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with self._client.stream("GET", url, params=params) as r:
            if r.status_code >= 400:
                # Try to read error body as JSON
                body = r.read()
                try:
                    import json as _json

                    err = _json.loads(body.decode("utf-8", errors="replace"))
                    raise TenderlandAPIError(
                        code=str(err.get("Code", "UNKNOWN")),
                        description=str(err.get("Description", "")),
                        http_status=r.status_code,
                    )
                except TenderlandAPIError:
                    raise
                except Exception:
                    r.raise_for_status()
            written = 0
            with dest_path.open("wb") as f:
                for chunk in r.iter_bytes(chunk_size=64 * 1024):
                    f.write(chunk)
                    written += len(chunk)
            return written
