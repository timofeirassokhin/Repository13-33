"""Synchronous Tenderland API client.

Covers what we need for the CLI:
  - GET  /Api/v1/User/GetStatistic
  - GET  /Api/v1/Dictionary/GetAutosearchList
  - GET  /Api/v1/Dictionary/GetFilterList                (filter catalog, 99 types)
  - GET  /Api/v1/Dictionary/GetFieldList                 (field catalog, 294 fields)
  - GET  /Api/v1/Search/GetAutosearch?autosearchId=X     (full JSON of one autosearch)
  - POST /Api/v1/Search/CreateAutosearch                 (create new autosearch, returns int id)
  - GET  /Api/v1/Export/Create
  - GET  /Api/v1/Export/Get  (paged)
  - GET  /Api/v1/File/GetAll (zip archive of all docs for a tender)

Endpoints NOT available on the Pro tier:
  - POST /Api/v1/Search/Find         (USER_DISABLE_API_MODULE)
  - POST /Api/v1/Search/UpdateAutosearch   (404)
  - POST /Api/v1/Search/DeleteAutosearch   (404)

For updates we use "Create-new-and-replace" workflow:
  1. read existing autosearch JSON
  2. patch include/exclude strings
  3. create new autosearch with same name + suffix
  4. user removes old one manually in UI (or we keep it as backup)

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

    # ---------- autosearch CRUD (partial: Create + Read, no Update/Delete on Pro tier) ----------

    def get_autosearch(self, autosearch_id: int) -> dict[str, Any]:
        """Read one autosearch as full JSON `{fields, filters, interval}`.

        Note: the parameter is called `autosearchId` (camelCase) — `id` returns 400.
        """
        return self._get_json(
            "/Api/v1/Search/GetAutosearch",
            {"autosearchId": autosearch_id},
        )

    def create_autosearch(
        self,
        name: str,
        parameters: dict[str, Any],
        *,
        mailing_days: list[Any] | None = None,
        mailing_times: list[Any] | None = None,
        delivery_fields: list[Any] | None = None,
        distribution_ids: list[Any] | None = None,
    ) -> int:
        """Create a new autosearch. Returns the new autosearch id (integer).

        :param name: Display name for the autosearch (must be unique-ish in UI).
        :param parameters: The same JSON shape that ``get_autosearch`` returns —
                           ``{"fields": [...], "filters": {"and": [...]}, "interval": [0, 1]}``.
        :param mailing_days/times: Email distribution schedule (empty = no email).
        :param delivery_fields/distribution_ids: Email payload config (empty = unused).

        Returns: integer autosearch id (response body is a bare int, not a JSON object).

        Raises ``TenderlandAPIError`` on 4xx with the Tenderland error shape.
        """
        url = self._url("/Api/v1/Search/CreateAutosearch")
        body = {
            "Name": name,
            "Parameters": parameters,
            "MailingDays": mailing_days or [],
            "MailingTimes": mailing_times or [],
            "DeliveryFields": delivery_fields or [],
            "DistributionIds": distribution_ids or [],
        }
        r = self._client.post(
            url,
            params={"apiKey": self.api_key, "format": "json"},
            json=body,
        )
        # Response body is a bare integer like `369536` (autosearch id).
        if r.status_code == 200:
            try:
                payload = r.json()
            except Exception:
                # Defensive: maybe it's plain text
                txt = r.text.strip()
                if txt.isdigit():
                    return int(txt)
                raise TenderlandAPIError(
                    code="UNKNOWN_RESPONSE",
                    description=f"Cannot parse Create response: {r.text[:200]!r}",
                    http_status=r.status_code,
                )
            if isinstance(payload, int):
                return payload
            if isinstance(payload, dict):
                for k in ("Id", "id", "autosearchId", "AutosearchId"):
                    if k in payload:
                        return int(payload[k])
            raise TenderlandAPIError(
                code="UNKNOWN_RESPONSE",
                description=f"Unexpected Create response shape: {payload!r}",
                http_status=r.status_code,
            )
        # 4xx — could be Tenderland error envelope or ASP.NET validation `{errors: {...}}`
        try:
            j = r.json()
            if isinstance(j, dict) and "errors" in j:
                # ASP.NET model validation failure
                errs = "; ".join(f"{k}: {v}" for k, v in j["errors"].items())
                raise TenderlandAPIError(
                    code="VALIDATION_FAILED",
                    description=errs,
                    http_status=r.status_code,
                )
            if isinstance(j, dict) and (j.get("Success") is False):
                raise TenderlandAPIError(
                    code=str(j.get("Code", "UNKNOWN")),
                    description=str(j.get("Description", "")),
                    http_status=r.status_code,
                )
        except TenderlandAPIError:
            raise
        except Exception:
            pass
        r.raise_for_status()
        raise TenderlandAPIError(
            code="UNKNOWN_ERROR",
            description=f"HTTP {r.status_code}: {r.text[:200]!r}",
            http_status=r.status_code,
        )

    # ---------- dictionary helpers (for payload validation) ----------

    def get_filter_list(self) -> list[dict[str, Any]]:
        """Return the catalog of available filter types (id, name, type, modules, ...)."""
        return self._get_json("/Api/v1/Dictionary/GetFilterList").get("items", [])

    def get_field_list(self) -> list[dict[str, Any]]:
        """Return the catalog of available fields for export."""
        return self._get_json("/Api/v1/Dictionary/GetFieldList").get("items", [])

    # ---------- file download ----------

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
