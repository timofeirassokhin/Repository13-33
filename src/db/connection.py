from __future__ import annotations

import logging
import os

import aiosqlite

from src.config import Settings

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, settings: Settings) -> None:
        self._db_path = settings.db_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._connection = await aiosqlite.connect(self._db_path)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL;")
        await self._connection.execute("PRAGMA foreign_keys=ON;")
        logger.info("Database connected: %s", self._db_path)

    async def disconnect(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database disconnected")

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection
