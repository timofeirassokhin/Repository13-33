"""Storage layer: Postgres (tenderland_* tables) + MinIO (tender archives).

Простой sync-API на psycopg 3. Используется и в CLI, и в pipeline-orchestrator.

Если переменные подключения не заданы — методы no-op (silent fallback на файлы),
чтобы локальные прогоны без БД продолжали работать.
"""
from .db import get_pool, db_available
from .repos import (
    TenderRepo, RunRepo, Tier2Repo, Tier3Repo, ArchiveRepo,
    save_run_decisions,
)

__all__ = [
    "get_pool", "db_available",
    "TenderRepo", "RunRepo", "Tier2Repo", "Tier3Repo", "ArchiveRepo",
    "save_run_decisions",
]
