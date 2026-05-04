"""Идемпотентная инициализация палаты для 13-33.

Создаёт восемь wings и в каждом — placeholder-drawer, чтобы wing появился
в list_wings. Безопасно перезапускать (placeholder перезаписывает сам себя).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path


WINGS = [
    ("books", "Книги полным текстом — основной источник теоретического материала."),
    ("articles", "Научные статьи и исследования — внешние источники."),
    ("13-33pubs", "Опубликованные посты 13-33 — лента всех каналов."),
    ("13-33scenarios", "Сценарии — для видео, подкастов, выступлений."),
    ("13-33interviews", "Интервью с экспертами и расшифровки."),
    ("13-33main", "Проверенное временем ядро 13-33 — важные смыслы и опорные тексты."),
    ("13-33drafts", "Драфты в работе — параллельно с Twenty.Drafts."),
    ("misc", "Идеи, заметки, случайные тексты — inbox для несортированного."),
    # tr-com (timofeirassokhin.com)
    ("tr-publications", "Опубликованные посты с timofeirassokhin.com — лента блога."),
    ("tr-drafts", "Черновики постов tr-com — параллельно с Twenty B.Drafts."),
    ("tr-trainings", "Материалы тренингов: программы, скрипты сессий, методички."),
    ("voice-tr", "Корпус голоса автора (расшифровки, посты, голосовые) — общий для 13-33 и tr-com."),
]


def main() -> None:
    palace_path = Path(os.environ.get("MEMPALACE_PALACE_PATH", "/data/palace"))
    palace_path.mkdir(parents=True, exist_ok=True)

    print(f"[init] Palace at: {palace_path}")

    try:
        from mempalace.backends.chroma import ChromaBackend  # type: ignore[import-not-found]
    except ImportError as e:
        print(f"[init] ERROR: cannot import mempalace: {e}")
        sys.exit(1)

    client = ChromaBackend.make_client(str(palace_path))
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
