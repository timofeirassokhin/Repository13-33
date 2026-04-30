from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from src.db.repositories.files_meta_repo import FilesMetaRepository
from src.models.common import ServiceResult
from src.models.files import FileEntry, SortResult, SortRule, SortStrategy
from src.services.base import BaseService

if TYPE_CHECKING:
    from src.config import Settings
    from src.db.connection import Database
    from src.services.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)

# Default MIME type prefix -> folder name
DEFAULT_TYPE_MAP: dict[str, str] = {
    "image/": "Images",
    "video/": "Videos",
    "audio/": "Audio",
    "application/pdf": "Documents/PDF",
    "application/vnd.google-apps.spreadsheet": "Spreadsheets",
    "application/vnd.google-apps.document": "Documents",
    "application/vnd.google-apps.presentation": "Presentations",
    "application/zip": "Archives",
    "application/x-rar": "Archives",
    "text/": "TextFiles",
}


class FileSorterService(BaseService):
    def __init__(
        self, db: Database, settings: Settings, auth: GoogleAuthService
    ) -> None:
        super().__init__(db, settings)
        self._auth = auth
        self._files_repo = FilesMetaRepository(db)

    async def sort_folder(
        self, telegram_user_id: int, folder_id: str,
        strategy: SortStrategy = SortStrategy.BY_TYPE,
    ) -> ServiceResult[SortResult]:
        try:
            drive = await self._auth.build_service("drive", "v3", telegram_user_id)

            # List files in folder
            files = await self._list_files(drive, folder_id)
            if not files:
                return ServiceResult(
                    success=True,
                    data=SortResult(skipped=["Папка пуста"]),
                )

            # Load user rules or use defaults
            user_rules = await self._files_repo.get_rules(telegram_user_id)

            result = SortResult()
            # Cache for created folders: folder_name -> folder_id
            folder_cache: dict[str, str] = {}

            for file_entry in files:
                dest_name = self._classify_file(file_entry, user_rules, strategy)
                if not dest_name:
                    result.skipped.append(file_entry.name)
                    continue

                try:
                    dest_id = folder_cache.get(dest_name)
                    if not dest_id:
                        dest_id = await self._ensure_folder(
                            drive, dest_name, folder_id
                        )
                        folder_cache[dest_name] = dest_id

                    await asyncio.to_thread(
                        drive.files()
                        .update(
                            fileId=file_entry.id,
                            addParents=dest_id,
                            removeParents=file_entry.parent_folder_id or folder_id,
                            fields="id, parents",
                        )
                        .execute
                    )
                    result.moved.append((file_entry.name, dest_name))
                except Exception as e:
                    result.errors.append(f"{file_entry.name}: {e}")

            logger.info(
                "Sorted %d files for user %d (%d moved, %d skipped, %d errors)",
                len(files), telegram_user_id,
                len(result.moved), len(result.skipped), len(result.errors),
            )
            return ServiceResult(success=True, data=result)
        except Exception as e:
            logger.exception("Failed to sort folder")
            return ServiceResult(success=False, error=str(e))

    async def add_rule(
        self, telegram_user_id: int, rule: SortRule
    ) -> ServiceResult[SortRule]:
        try:
            rule_id = await self._files_repo.add_rule(telegram_user_id, rule)
            rule.id = rule_id
            return ServiceResult(success=True, data=rule)
        except Exception as e:
            logger.exception("Failed to add rule")
            return ServiceResult(success=False, error=str(e))

    async def list_rules(
        self, telegram_user_id: int
    ) -> ServiceResult[list[SortRule]]:
        try:
            rules = await self._files_repo.get_rules(telegram_user_id)
            return ServiceResult(success=True, data=rules)
        except Exception as e:
            logger.exception("Failed to list rules")
            return ServiceResult(success=False, error=str(e))

    async def _list_files(self, drive: Any, folder_id: str) -> list[FileEntry]:
        result = await asyncio.to_thread(
            drive.files()
            .list(
                q=f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'",
                fields="files(id, name, mimeType, size, createdTime, parents)",
                pageSize=100,
            )
            .execute
        )
        files = []
        for item in result.get("files", []):
            parents = item.get("parents", [])
            files.append(FileEntry(
                id=item["id"],
                name=item["name"],
                mime_type=item.get("mimeType", ""),
                size=int(item.get("size", 0)),
                parent_folder_id=parents[0] if parents else None,
            ))
        return files

    def _classify_file(
        self, file: FileEntry, user_rules: list[SortRule],
        strategy: SortStrategy,
    ) -> str | None:
        # Check user rules first
        for rule in user_rules:
            for pattern in rule.extension_patterns:
                if file.name.lower().endswith(pattern.lower()):
                    return rule.destination_folder_name or rule.name
            for pattern in rule.mime_patterns:
                if file.mime_type.startswith(pattern):
                    return rule.destination_folder_name or rule.name

        # Fall back to default type map
        if strategy == SortStrategy.BY_TYPE:
            for prefix, folder_name in DEFAULT_TYPE_MAP.items():
                if file.mime_type.startswith(prefix):
                    return folder_name

        return None

    async def _ensure_folder(
        self, drive: Any, folder_name: str, parent_id: str
    ) -> str:
        # Check if folder already exists
        result = await asyncio.to_thread(
            drive.files()
            .list(
                q=(
                    f"name = '{folder_name}' and "
                    f"'{parent_id}' in parents and "
                    f"mimeType = 'application/vnd.google-apps.folder'"
                ),
                fields="files(id)",
                pageSize=1,
            )
            .execute
        )
        existing = result.get("files", [])
        if existing:
            return existing[0]["id"]

        # Create folder
        metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        created = await asyncio.to_thread(
            drive.files().create(body=metadata, fields="id").execute
        )
        return created["id"]
