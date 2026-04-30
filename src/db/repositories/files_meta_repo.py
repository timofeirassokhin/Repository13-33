from __future__ import annotations

import json
import logging

from src.db.connection import Database
from src.models.files import SortRule

logger = logging.getLogger(__name__)


class FilesMetaRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_rules(self, telegram_user_id: int) -> list[SortRule]:
        rules = []
        async with self._db.conn.execute(
            "SELECT * FROM sort_rules WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ) as cursor:
            async for row in cursor:
                row_dict = dict(row)
                rules.append(SortRule(
                    id=row_dict["id"],
                    name=row_dict["name"],
                    mime_patterns=json.loads(row_dict.get("mime_patterns", "[]")),
                    extension_patterns=json.loads(row_dict.get("extension_patterns", "[]")),
                    destination_folder_id=row_dict["destination_folder_id"],
                    destination_folder_name=row_dict.get("destination_folder_name", ""),
                ))
        return rules

    async def add_rule(self, telegram_user_id: int, rule: SortRule) -> int:
        cursor = await self._db.conn.execute(
            """
            INSERT INTO sort_rules
                (telegram_user_id, name, mime_patterns, extension_patterns,
                 destination_folder_id, destination_folder_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                telegram_user_id,
                rule.name,
                json.dumps(rule.mime_patterns),
                json.dumps(rule.extension_patterns),
                rule.destination_folder_id,
                rule.destination_folder_name,
            ),
        )
        await self._db.conn.commit()
        rule_id = cursor.lastrowid or 0
        logger.info("Sort rule added: %s for user %d", rule.name, telegram_user_id)
        return rule_id

    async def delete_rule(self, rule_id: int) -> None:
        await self._db.conn.execute(
            "DELETE FROM sort_rules WHERE id = ?",
            (rule_id,),
        )
        await self._db.conn.commit()
