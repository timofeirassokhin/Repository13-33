from __future__ import annotations

import logging

from src.db.connection import Database

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

MIGRATIONS: dict[int, list[str]] = {
    1: [
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_user_id INTEGER PRIMARY KEY,
            google_access_token TEXT,
            google_refresh_token TEXT,
            google_token_expiry TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS notes_metadata (
            drive_file_id TEXT PRIMARY KEY,
            telegram_user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            snippet TEXT DEFAULT '',
            folder_path TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS sort_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            mime_patterns TEXT DEFAULT '[]',
            extension_patterns TEXT DEFAULT '[]',
            destination_folder_id TEXT NOT NULL,
            destination_folder_name TEXT DEFAULT '',
            FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY
        );
        """,
    ],
}


async def run_migrations(db: Database) -> None:
    conn = db.conn

    # Check if schema_version table exists
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    ) as cursor:
        table_exists = await cursor.fetchone()

    current_version = 0
    if table_exists:
        async with conn.execute("SELECT MAX(version) FROM schema_version") as cursor:
            row = await cursor.fetchone()
            if row and row[0] is not None:
                current_version = row[0]

    if current_version >= SCHEMA_VERSION:
        logger.info("Database schema is up to date (v%d)", current_version)
        return

    for version in range(current_version + 1, SCHEMA_VERSION + 1):
        if version not in MIGRATIONS:
            continue
        logger.info("Applying migration v%d...", version)
        for sql in MIGRATIONS[version]:
            await conn.execute(sql)
        await conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (version,),
        )
        await conn.commit()

    logger.info("Database migrated to v%d", SCHEMA_VERSION)
