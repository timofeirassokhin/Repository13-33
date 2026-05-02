"""Bulk-uploader для MemPalace 13-33.

Структура `/uploads`:
  inbox/<wing>/file.pdf       — drop-zone
  processed/<wing>/file.pdf   — после успешной загрузки
  failed/<wing>/file.pdf      — что не удалось распарсить (+ file.error.log)
  markdown/<wing>/file.md     — конвертированный markdown (для прозрачности)

Wing определяется по имени родительской папки внутри inbox/.
Файлы прямо в inbox/ (без подпапки) уезжают в `misc`.

Команды:
  python uploader.py watch              — бесконечный цикл (poll каждые WATCH_INTERVAL сек)
  python uploader.py process-all        — обработать всё в inbox один раз и выйти
  python uploader.py process <path>     — обработать один файл или директорию
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from chunker import chunk_text
from parsers import PARSERS, parse_file


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("uploader")


MEMPALACE_URL = os.environ.get("MEMPALACE_URL", "http://mempalace:8080")
UPLOADS_PATH = Path(os.environ.get("UPLOADS_PATH", "/uploads"))
WATCH_INTERVAL = int(os.environ.get("WATCH_INTERVAL", "30"))

INBOX = UPLOADS_PATH / "inbox"
PROCESSED = UPLOADS_PATH / "processed"
FAILED = UPLOADS_PATH / "failed"
MARKDOWN = UPLOADS_PATH / "markdown"

KNOWN_WINGS = {
    "books", "articles",
    "13-33pubs", "13-33scenarios", "13-33interviews", "13-33main", "13-33drafts",
    "misc",
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def ensure_dirs() -> None:
    for p in (INBOX, PROCESSED, FAILED, MARKDOWN):
        p.mkdir(parents=True, exist_ok=True)


def detect_wing(path: Path) -> str:
    """Определить wing по родительской папке относительно inbox/."""
    try:
        rel = path.relative_to(INBOX)
    except ValueError:
        return "misc"
    parts = rel.parts
    if len(parts) <= 1:
        return "misc"
    candidate = parts[0]
    if candidate in KNOWN_WINGS:
        return candidate
    log.warning("Unknown wing folder %r — using 'misc'", candidate)
    return "misc"


def move_to(src: Path, dst_root: Path, wing: str) -> Path:
    """Переместить файл в dst_root/<wing>/ с сохранением исходного имени."""
    dst_dir = dst_root / wing
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    # Если такой файл уже есть — добавляем timestamp
    if dst.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_dir / f"{src.stem}_{ts}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst


def save_markdown(text: str, source_path: Path, wing: str) -> Path:
    md_dir = MARKDOWN / wing
    md_dir.mkdir(parents=True, exist_ok=True)
    md_path = md_dir / f"{source_path.stem}.md"
    md_path.write_text(text, encoding="utf-8")
    return md_path


def write_error_log(failed_path: Path, error_msg: str) -> None:
    log_path = failed_path.with_suffix(failed_path.suffix + ".error.log")
    log_path.write_text(
        f"timestamp: {datetime.now(timezone.utc).isoformat()}\nerror:\n{error_msg}\n",
        encoding="utf-8",
    )


# ----------------------------------------------------------------------------
# MemPalace upload
# ----------------------------------------------------------------------------

def upload_chunks(client: httpx.Client, chunks: list[str], wing: str, source_name: str, source_rel: str) -> int:
    """Грузим chunks в MemPalace. Возвращает количество успешно загруженных."""
    success = 0
    total = len(chunks)
    title_base = Path(source_name).stem
    for i, chunk in enumerate(chunks):
        title = f"{title_base} (часть {i + 1}/{total})" if total > 1 else title_base
        payload = {
            "content": chunk,
            "wing": wing,
            "room": title_base[:60],  # room = базовое имя файла как группировка чанков
            "title": title,
            "source_file": source_rel,
            "added_by": "bulk_uploader",
            "tags": [f"chunk_{i + 1}_of_{total}"],
        }
        r = client.post("/drawer", json=payload, timeout=60)
        if r.status_code == 200:
            success += 1
        else:
            log.warning("Drawer upload failed (status=%d): %s", r.status_code, r.text[:200])
    return success


# ----------------------------------------------------------------------------
# Pipeline для одного файла
# ----------------------------------------------------------------------------

def process_one(client: httpx.Client, file_path: Path) -> bool:
    """Обработать один файл. Возвращает True если успешно."""
    if file_path.is_dir():
        return False
    ext = file_path.suffix.lower()
    if ext not in PARSERS:
        log.info("Skip (unsupported ext): %s", file_path.name)
        return False

    wing = detect_wing(file_path)
    rel_for_meta = str(file_path.relative_to(UPLOADS_PATH))
    log.info("Processing: %s → wing=%s", rel_for_meta, wing)

    try:
        text = parse_file(file_path)
        if not text or len(text.strip()) < 50:
            raise ValueError(f"Parsed text too short ({len(text)} chars) — file may be empty or unparseable")

        # Сохранить markdown-копию (для прозрачности и быстрого доступа)
        md_path = save_markdown(text, file_path, wing)
        log.info("  parsed: %d chars → %s", len(text), md_path)

        # Чанкинг
        chunks = chunk_text(text, target_size=2000, overlap=200)
        log.info("  chunks: %d", len(chunks))

        # Загрузить в MemPalace
        success_count = upload_chunks(client, chunks, wing, file_path.name, rel_for_meta)
        log.info("  uploaded: %d/%d chunks to MemPalace", success_count, len(chunks))

        if success_count == 0:
            raise RuntimeError("Все chunks упали при загрузке в MemPalace")

        # Если хотя бы 80% успешно — считаем удачей
        if success_count < 0.8 * len(chunks):
            log.warning("  ⚠️ только %d/%d chunks загрузилось — но всё равно перемещаем в processed",
                        success_count, len(chunks))

        # Перемещаем оригинал в processed
        dst = move_to(file_path, PROCESSED, wing)
        log.info("  → processed/%s/%s", wing, dst.name)
        return True

    except Exception as e:
        log.exception("Failed to process: %s", file_path.name)
        try:
            dst = move_to(file_path, FAILED, wing)
            write_error_log(dst, str(e))
            log.info("  → failed/%s/%s", wing, dst.name)
        except Exception:
            log.exception("Also failed to move to failed/")
        return False


def find_pending_files() -> list[Path]:
    """Список всех файлов в inbox/, готовых к обработке."""
    if not INBOX.exists():
        return []
    files: list[Path] = []
    for path in INBOX.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in PARSERS:
            files.append(path)
    return sorted(files)


# ----------------------------------------------------------------------------
# Команды
# ----------------------------------------------------------------------------

def cmd_process_all(client: httpx.Client) -> int:
    """Обработать всё что есть в inbox. Возвращает количество обработанных."""
    files = find_pending_files()
    if not files:
        log.info("Нет файлов в inbox/")
        return 0
    log.info("Найдено %d файлов для обработки", len(files))
    processed = 0
    for f in files:
        if process_one(client, f):
            processed += 1
    log.info("Готово: успешно %d / всего %d", processed, len(files))
    return processed


def cmd_watch(client: httpx.Client) -> None:
    """Бесконечный цикл — poll inbox каждые WATCH_INTERVAL секунд."""
    log.info("Watch mode — poll каждые %d сек", WATCH_INTERVAL)
    while True:
        try:
            files = find_pending_files()
            if files:
                log.info("Найдено %d файлов для обработки", len(files))
                for f in files:
                    process_one(client, f)
        except Exception:
            log.exception("Watch iteration failed (продолжаем)")
        time.sleep(WATCH_INTERVAL)


def cmd_process(client: httpx.Client, path: Path) -> int:
    """Обработать конкретный путь — файл или директорию."""
    if not path.exists():
        log.error("Не существует: %s", path)
        return 0
    if path.is_file():
        return 1 if process_one(client, path) else 0
    files: list[Path] = []
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in PARSERS:
            files.append(f)
    log.info("Обрабатываю %d файлов в %s", len(files), path)
    success = sum(1 for f in files if process_one(client, f))
    log.info("Готово: %d/%d", success, len(files))
    return success


# ----------------------------------------------------------------------------

def main() -> int:
    ensure_dirs()
    log.info("MemPalace URL: %s", MEMPALACE_URL)
    log.info("Uploads path:  %s", UPLOADS_PATH)

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1

    cmd = args[0]
    with httpx.Client(base_url=MEMPALACE_URL, timeout=httpx.Timeout(120.0)) as client:
        # health check
        try:
            r = client.get("/health")
            if r.status_code != 200:
                log.error("MemPalace health=%d, прерываю", r.status_code)
                return 2
            log.info("MemPalace health: %s", r.json())
        except Exception:
            log.exception("Cannot reach MemPalace, прерываю")
            return 2

        if cmd == "watch":
            cmd_watch(client)
            return 0
        if cmd == "process-all":
            cmd_process_all(client)
            return 0
        if cmd == "process":
            if len(args) < 2:
                print("usage: uploader.py process <path>")
                return 1
            cmd_process(client, Path(args[1]))
            return 0
        print(f"unknown command: {cmd}")
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
