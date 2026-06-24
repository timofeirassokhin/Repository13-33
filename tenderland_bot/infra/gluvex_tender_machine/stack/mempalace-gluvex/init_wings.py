"""Идемпотентная инициализация Gluvex MemPalace через Qdrant backend.

Создаёт 5 wings и в каждом — placeholder-drawer (чтобы wing был виден в list_wings).
Безопасно перезапускать (placeholder перезаписывается).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


# 5 Gluvex-wings (master-data-architecture.md раздел 6)
WINGS = [
    ("gluvex-products",
     "Каталог продукции Gluvex: приборы, расходники, синонимы, совместимость, datasheet ссылки. "
     "Источник истины — 1С + product_brochures из MinIO. Используется product_manager и tender_analyzer."),

    ("gluvex-clients",
     "Клиенты Gluvex: история закупок, предпочтения, ключевые контакты, тон коммуникации. "
     "Источник истины — 1С + entity_links. Используется kp_agent и email_agent."),

    ("gluvex-tenders",
     "История тендеров: типовые формулировки ТЗ, скрытые брендовые требования, выигранные/проигранные кейсы, "
     "паттерны заказчиков. Используется tender_analyzer."),

    ("gluvex-kp",
     "База коммерческих предложений: шаблоны, удачные формулировки, скидочные правила, "
     "ходовые комплектации. Используется kp_agent."),

    ("gluvex-knowledge",
     "Общая корпоративная база: методики, SOP, регламенты, методические указания клиентов. "
     "Используется всеми агентами."),
]


def main() -> None:
    palace_path = Path(os.environ.get("MEMPALACE_PALACE_PATH", "/data/palace"))
    palace_path.mkdir(parents=True, exist_ok=True)

    print(f"[init] Palace at: {palace_path}")
    print(f"[init] Qdrant URL: {os.environ.get('QDRANT_URL', 'http://qdrant:6333')}")

    try:
        from qdrant_backend import QdrantBackend
    except ImportError as e:
        print(f"[init] ERROR: cannot import qdrant_backend: {e}")
        sys.exit(1)

    client = QdrantBackend.make_client(str(palace_path))
    col = client.get_or_create_collection("memories")

    now = datetime.now(timezone.utc).isoformat()

    for wing, description in WINGS:
        drawer_id = f"_init_{wing}"
        col.upsert(
            ids=[drawer_id],
            documents=[f"[Wing init] {description}"],
            metadatas=[{
                "wing": wing,
                "room": "_init",
                "source_file": "",
                "chunk_index": 0,
                "added_by": "system_init",
                "filed_at": now,
            }],
        )
        print(f"[init] wing ready: {wing}")

    total = col.count()
    print(f"[init] total drawers in palace: {total}")
    print("[init] done")


if __name__ == "__main__":
    main()
