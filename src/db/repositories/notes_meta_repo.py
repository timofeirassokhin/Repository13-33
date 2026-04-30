from __future__ import annotations

import json
import logging
from datetime import datetime

from src.db.connection import Database
from src.models.notes import NoteMetadata, NoteSearchQuery

logger = logging.getLogger(__name__)


class NotesMetaRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert(
        self, telegram_user_id: int, drive_file_id: str, title: str,
        tags: list[str], snippet: str = "", folder_path: str = "",
    ) -> None:
        now = datetime.utcnow().isoformat()
        await self._db.conn.execute(
            """
            INSERT INTO notes_metadata
                (drive_file_id, telegram_user_id, title, tags, snippet, folder_path,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(drive_file_id) DO UPDATE SET
                title = excluded.title,
                tags = excluded.tags,
                snippet = excluded.snippet,
                folder_path = excluded.folder_path,
                updated_at = excluded.updated_at
            """,
            (drive_file_id, telegram_user_id, title, json.dumps(tags),
             snippet, folder_path, now, now),
        )
        await self._db.conn.commit()

    async def search(
        self, telegram_user_id: int, query: NoteSearchQuery
    ) -> list[NoteMetadata]:
        conditions = ["telegram_user_id = ?"]
        params: list = [telegram_user_id]

        if query.query:
            conditions.append("(title LIKE ? OR snippet LIKE ?)")
            like = f"%{query.query}%"
            params.extend([like, like])

        if query.tags:
            for tag in query.tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        if query.date_from:
            conditions.append("created_at >= ?")
            params.append(query.date_from.isoformat())

        if query.date_to:
            conditions.append("created_at <= ?")
            params.append(query.date_to.isoformat())

        where = " AND ".join(conditions)
        sql = f"""
            SELECT * FROM notes_metadata
            WHERE {where}
            ORDER BY updated_at DESC
            LIMIT ?
        """
        params.append(query.max_results)

        results = []
        async with self._db.conn.execute(sql, params) as cursor:
            async for row in cursor:
                row_dict = dict(row)
                tags = json.loads(row_dict.get("tags", "[]"))
                results.append(NoteMetadata(
                    drive_file_id=row_dict["drive_file_id"],
                    title=row_dict["title"],
                    tags=tags,
                    snippet=row_dict.get("snippet", ""),
                    created_at=datetime.fromisoformat(row_dict["created_at"]) if row_dict.get("created_at") else None,
                    updated_at=datetime.fromisoformat(row_dict["updated_at"]) if row_dict.get("updated_at") else None,
                    folder_path=row_dict.get("folder_path", ""),
                ))
        return results

    async def get_all(self, telegram_user_id: int, limit: int = 20) -> list[NoteMetadata]:
        return await self.search(telegram_user_id, NoteSearchQuery(max_results=limit))

    async def delete(self, drive_file_id: str) -> None:
        await self._db.conn.execute(
            "DELETE FROM notes_metadata WHERE drive_file_id = ?",
            (drive_file_id,),
        )
        await self._db.conn.commit()
