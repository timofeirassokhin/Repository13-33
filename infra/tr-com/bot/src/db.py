"""Локальная SQLite — пока Twenty/Listmonk не готовы как backend.

Хранит:
- users: каждый кто запустил бота — tg_id, username, имя, язык, email (если оставил)
- messages: все входящие сообщения — для контекста и истории
- bookings: заявки на консультацию через /book

Когда настроим SMTP в Listmonk — добавим команду /sync чтобы синкнуть users в подписчиков.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    tg_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT,
    email TEXT,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    is_subscribed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    text TEXT,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (tg_id) REFERENCES users(tg_id)
);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER NOT NULL,
    topic TEXT,
    when_pref TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at INTEGER NOT NULL,
    FOREIGN KEY (tg_id) REFERENCES users(tg_id)
);
CREATE INDEX IF NOT EXISTS idx_messages_tg_id ON messages(tg_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
"""


class DB:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._conn: aiosqlite.Connection | None = None

    async def open(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn, "DB not opened"
        return self._conn

    async def upsert_user(
        self,
        tg_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        language_code: Optional[str],
    ) -> None:
        now = int(time.time())
        await self.conn.execute(
            """
            INSERT INTO users (tg_id, username, first_name, last_name, language_code, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tg_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                language_code = excluded.language_code,
                last_seen = excluded.last_seen
            """,
            (tg_id, username, first_name, last_name, language_code, now, now),
        )
        await self.conn.commit()

    async def set_email(self, tg_id: int, email: str) -> None:
        await self.conn.execute(
            "UPDATE users SET email = ?, is_subscribed = 1 WHERE tg_id = ?",
            (email, tg_id),
        )
        await self.conn.commit()

    async def log_message(
        self, tg_id: int, chat_id: int, message_id: int, kind: str, text: Optional[str]
    ) -> None:
        await self.conn.execute(
            "INSERT INTO messages (tg_id, chat_id, message_id, kind, text, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, chat_id, message_id, kind, text, int(time.time())),
        )
        await self.conn.commit()

    async def add_booking(self, tg_id: int, topic: str, when_pref: str) -> int:
        cur = await self.conn.execute(
            "INSERT INTO bookings (tg_id, topic, when_pref, created_at) VALUES (?, ?, ?, ?)",
            (tg_id, topic, when_pref, int(time.time())),
        )
        await self.conn.commit()
        return cur.lastrowid or 0

    async def list_recent_users(self, limit: int = 20) -> list[dict]:
        async with self.conn.execute(
            """
            SELECT tg_id, username, first_name, last_name, email, is_subscribed, last_seen
            FROM users
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [
            {
                "tg_id": r[0], "username": r[1], "first_name": r[2], "last_name": r[3],
                "email": r[4], "is_subscribed": bool(r[5]), "last_seen": r[6],
            }
            for r in rows
        ]

    async def list_pending_bookings(self) -> list[dict]:
        async with self.conn.execute(
            """
            SELECT b.id, b.tg_id, u.username, u.first_name, b.topic, b.when_pref, b.created_at
            FROM bookings b LEFT JOIN users u USING (tg_id)
            WHERE b.status = 'new'
            ORDER BY b.created_at DESC
            """,
        ) as cur:
            rows = await cur.fetchall()
        return [
            {
                "id": r[0], "tg_id": r[1], "username": r[2], "first_name": r[3],
                "topic": r[4], "when_pref": r[5], "created_at": r[6],
            }
            for r in rows
        ]

    async def list_subscribers(self) -> list[dict]:
        """Список тех кто оставил email — пуш в Listmonk когда подключим SMTP."""
        async with self.conn.execute(
            """
            SELECT tg_id, email, first_name, last_name, language_code
            FROM users
            WHERE is_subscribed = 1 AND email IS NOT NULL
            ORDER BY last_seen DESC
            """
        ) as cur:
            rows = await cur.fetchall()
        return [
            {
                "tg_id": r[0], "email": r[1], "first_name": r[2],
                "last_name": r[3], "language_code": r[4],
            }
            for r in rows
        ]
