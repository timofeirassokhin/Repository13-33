from __future__ import annotations

import logging

from src.db.connection import Database

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_user(self, telegram_user_id: int) -> dict | None:
        async with self._db.conn.execute(
            "SELECT * FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def upsert_tokens(
        self,
        telegram_user_id: int,
        access_token: str,
        refresh_token: str,
        expiry: str,
    ) -> None:
        await self._db.conn.execute(
            """
            INSERT INTO users (telegram_user_id, google_access_token,
                               google_refresh_token, google_token_expiry)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_user_id) DO UPDATE SET
                google_access_token = excluded.google_access_token,
                google_refresh_token = excluded.google_refresh_token,
                google_token_expiry = excluded.google_token_expiry,
                updated_at = datetime('now')
            """,
            (telegram_user_id, access_token, refresh_token, expiry),
        )
        await self._db.conn.commit()
        logger.info("Tokens saved for user %d", telegram_user_id)

    async def delete_user(self, telegram_user_id: int) -> None:
        await self._db.conn.execute(
            "DELETE FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        )
        await self._db.conn.commit()
        logger.info("User %d deleted", telegram_user_id)

    async def is_authenticated(self, telegram_user_id: int) -> bool:
        user = await self.get_user(telegram_user_id)
        return user is not None and user["google_refresh_token"] is not None
