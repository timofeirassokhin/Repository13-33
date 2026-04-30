from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from src.db.repositories.notes_meta_repo import NotesMetaRepository
from src.models.common import ServiceResult
from src.models.notes import Note, NoteMetadata, NoteSearchQuery
from src.services.base import BaseService

if TYPE_CHECKING:
    from src.config import Settings
    from src.db.connection import Database
    from src.services.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)


class NotesService(BaseService):
    def __init__(
        self, db: Database, settings: Settings, auth: GoogleAuthService
    ) -> None:
        super().__init__(db, settings)
        self._auth = auth
        self._meta_repo = NotesMetaRepository(db)

    async def create_note(
        self, telegram_user_id: int, note: Note
    ) -> ServiceResult[Note]:
        try:
            drive = await self._auth.build_service("drive", "v3", telegram_user_id)

            folder_id = note.folder_id or self._settings.notes_folder_id
            file_metadata: dict = {
                "name": note.title,
                "mimeType": "application/vnd.google-apps.document",
            }
            if folder_id:
                file_metadata["parents"] = [folder_id]

            created = await asyncio.to_thread(
                drive.files().create(body=file_metadata, fields="id").execute
            )
            note.id = created["id"]

            # Write content if provided
            if note.content:
                docs = await self._auth.build_service("docs", "v1", telegram_user_id)
                await asyncio.to_thread(
                    docs.documents()
                    .batchUpdate(
                        documentId=note.id,
                        body={
                            "requests": [
                                {
                                    "insertText": {
                                        "location": {"index": 1},
                                        "text": note.content,
                                    }
                                }
                            ]
                        },
                    )
                    .execute
                )

            # Cache metadata locally
            await self._meta_repo.upsert(
                telegram_user_id=telegram_user_id,
                drive_file_id=note.id,
                title=note.title,
                tags=note.tags,
                snippet=note.content[:200] if note.content else "",
            )

            logger.info("Note created: %s for user %d", note.id, telegram_user_id)
            return ServiceResult(success=True, data=note)
        except Exception as e:
            logger.exception("Failed to create note")
            return ServiceResult(success=False, error=str(e))

    async def search_notes(
        self, telegram_user_id: int, query: NoteSearchQuery
    ) -> ServiceResult[list[NoteMetadata]]:
        try:
            # Search local cache first
            results = await self._meta_repo.search(telegram_user_id, query)

            # If not enough results, try Drive API
            if len(results) < query.max_results and query.query:
                drive = await self._auth.build_service("drive", "v3", telegram_user_id)
                drive_query = f"fullText contains '{query.query}' and mimeType = 'application/vnd.google-apps.document'"
                drive_results = await asyncio.to_thread(
                    drive.files()
                    .list(
                        q=drive_query,
                        fields="files(id, name, createdTime, modifiedTime)",
                        pageSize=query.max_results,
                    )
                    .execute
                )
                existing_ids = {r.drive_file_id for r in results}
                for item in drive_results.get("files", []):
                    if item["id"] not in existing_ids:
                        from datetime import datetime
                        results.append(NoteMetadata(
                            drive_file_id=item["id"],
                            title=item.get("name", ""),
                            created_at=datetime.fromisoformat(item["createdTime"].rstrip("Z")) if item.get("createdTime") else None,
                            updated_at=datetime.fromisoformat(item["modifiedTime"].rstrip("Z")) if item.get("modifiedTime") else None,
                        ))

            return ServiceResult(success=True, data=results)
        except Exception as e:
            logger.exception("Failed to search notes")
            return ServiceResult(success=False, error=str(e))

    async def list_notes(
        self, telegram_user_id: int
    ) -> ServiceResult[list[NoteMetadata]]:
        try:
            results = await self._meta_repo.get_all(telegram_user_id)
            return ServiceResult(success=True, data=results)
        except Exception as e:
            logger.exception("Failed to list notes")
            return ServiceResult(success=False, error=str(e))

    async def delete_note(
        self, telegram_user_id: int, note_id: str
    ) -> ServiceResult[None]:
        try:
            drive = await self._auth.build_service("drive", "v3", telegram_user_id)
            await asyncio.to_thread(
                drive.files().delete(fileId=note_id).execute
            )
            await self._meta_repo.delete(note_id)
            logger.info("Note deleted: %s for user %d", note_id, telegram_user_id)
            return ServiceResult(success=True)
        except Exception as e:
            logger.exception("Failed to delete note")
            return ServiceResult(success=False, error=str(e))
