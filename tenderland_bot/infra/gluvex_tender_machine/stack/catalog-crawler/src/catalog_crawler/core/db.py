"""DB helpers — async connection + insertion."""
from __future__ import annotations

import asyncpg

from catalog_crawler.settings import settings


async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(settings.pg_dsn)


async def check_pg() -> bool:
    try:
        conn = await get_conn()
        v = await conn.fetchval("SELECT 1")
        await conn.close()
        return v == 1
    except Exception as e:
        print(f"  pg error: {e}")
        return False


async def audit_event(action: str, payload: dict, actor_type: str = "system", actor_id: str | None = None) -> None:
    """Запись в audit_events (append-only)."""
    conn = await get_conn()
    try:
        await conn.execute(
            """
            INSERT INTO audit_events (entity_type, actor_type, action, context)
            VALUES ($1, $2, $3, $4::jsonb)
            """,
            "catalog_crawler",
            actor_type,
            action,
            __import__("json").dumps(payload),
        )
    finally:
        await conn.close()
