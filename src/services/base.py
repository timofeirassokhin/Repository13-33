from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Settings
    from src.db.connection import Database


class BaseService:
    def __init__(self, db: Database, settings: Settings) -> None:
        self._db = db
        self._settings = settings
        self._logger = logging.getLogger(self.__class__.__qualname__)
