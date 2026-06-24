"""Postgres connection (psycopg 3, sync pool).

DSN формируется из переменных окружения (приоритет — DSN целиком, иначе по частям):
  - GLUVEX_DB_DSN — полный postgresql://...
  - либо GLUVEX_DB_HOST (default: localhost), GLUVEX_DB_PORT (5432),
         GLUVEX_DB_NAME (gluvex_documents),
         GLUVEX_DB_USER (gluvex_app),
         GLUVEX_APP_PG_PASSWORD

Если ни DSN, ни пароля нет — `db_available()` возвращает False, и repos станут no-op.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

try:
    from psycopg_pool import ConnectionPool
    _HAS_PSYCOPG = True
except ImportError:  # psycopg не установлен
    _HAS_PSYCOPG = False
    ConnectionPool = None  # type: ignore


def _build_dsn() -> Optional[str]:
    dsn = os.environ.get("GLUVEX_DB_DSN")
    if dsn:
        return dsn
    pw = (os.environ.get("GLUVEX_APP_PG_PASSWORD")
          or os.environ.get("APP_DB_PASSWORD"))
    if not pw:
        return None
    host = os.environ.get("GLUVEX_DB_HOST", "localhost")
    port = os.environ.get("GLUVEX_DB_PORT", "5432")
    dbname = os.environ.get("GLUVEX_DB_NAME", "gluvex_documents")
    user = os.environ.get("GLUVEX_DB_USER", "gluvex_app")
    return f"postgresql://{user}:{pw}@{host}:{port}/{dbname}"


def db_available() -> bool:
    return _HAS_PSYCOPG and _build_dsn() is not None


@lru_cache(maxsize=1)
def get_pool():
    """Ленивая инициализация пула. Возвращает None если БД недоступна."""
    if not db_available():
        return None
    dsn = _build_dsn()
    return ConnectionPool(dsn, min_size=1, max_size=4, open=True, timeout=10)
