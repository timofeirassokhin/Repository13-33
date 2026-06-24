"""Распаковка тендерных zip-архивов с поддержкой вложенных архивов и кириллицы.

Реальные форматы tender package с zakupki.gov.ru / коммерческих площадок:

1. **Плоский** — doc/docx/pdf/xlsx/html лежат сразу в корне zip'а.
2. **Nested-zip** — каждый файл обёрнут в свой `<имя>.<ext>.zip` (вместе с подписью).
3. **Минимальный** — только извещение + один файл "Запрос цен.docx".

Все три формата встречаются. Кодировка имён внутри zip — обычно CP866 без
UTF-8 флага. Рекурсивно разворачиваем nested zips на месте.
"""
from __future__ import annotations

import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


# Префиксы файлов с электронной подписью — это копия оригинала + .sig/.sgn,
# для анализа специс'ов смысла не несут, пропускаем.
SIGNATURE_PREFIXES = ("EDS_",)

# Максимальная глубина рекурсии вложенных архивов
MAX_NESTED_DEPTH = 5


@dataclass
class UnpackResult:
    """Что вернула распаковка одного тендерного архива."""

    tender_id: str
    source_zip: Path
    output_dir: Path
    # Все извлечённые файлы (с учётом рекурсии)
    extracted_files: list[Path] = field(default_factory=list)
    # Подписанные копии (EDS_*) — извлечены отдельно, не для анализа
    signature_files: list[Path] = field(default_factory=list)
    # Файлы которые не удалось извлечь (битые zip и т.п.)
    failed_entries: list[str] = field(default_factory=list)
    nested_zips_unpacked: int = 0

    def primary_files(self) -> list[Path]:
        """Файлы для анализа — без подписей."""
        return self.extracted_files


def _decode_zip_name(raw: str) -> str:
    """Преобразовать имя файла внутри zip из CP866 в нормальный UTF-8.

    Стандартный zip без UTF-8 флага хранит имена в OEM-кодировке
    (для России это CP866). Python отдаёт их как латиница-1 (cp437) —
    нужно переэнкодить.
    """
    if not raw:
        return raw
    try:
        # zipfile отдал строку, декодированную как cp437. Перекодируем в cp866.
        return raw.encode("cp437").decode("cp866")
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Если файл уже был с UTF-8 флагом — возвращаем как есть
        return raw


def _safe_filename(name: str) -> str:
    """Заменить символы, которые ломают пути на Windows."""
    # Чистим только запрещённые символы Windows; кириллицу оставляем.
    forbidden = '<>:"/\\|?*\x00'
    cleaned = "".join("_" if c in forbidden else c for c in name)
    # Обрезаем длину на всякий случай (Windows MAX_PATH)
    if len(cleaned) > 200:
        stem, ext = os.path.splitext(cleaned)
        cleaned = stem[: 200 - len(ext)] + ext
    return cleaned.strip()


def _is_signature_file(name: str) -> bool:
    return any(name.startswith(p) for p in SIGNATURE_PREFIXES)


def _extract_zip(
    zip_path: Path,
    dest_dir: Path,
    result: UnpackResult,
    depth: int = 0,
) -> None:
    """Распаковать один zip в dest_dir, рекурсивно развернуть вложенные .zip."""
    if depth > MAX_NESTED_DEPTH:
        log.warning("max nested depth reached at %s", zip_path)
        return

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        result.failed_entries.append(str(zip_path))
        log.warning("bad zip: %s", zip_path)
        return

    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            decoded = _decode_zip_name(info.filename)
            safe = _safe_filename(os.path.basename(decoded))
            if not safe:
                continue
            target = dest_dir / safe

            # Защита от коллизий имён
            counter = 1
            while target.exists():
                stem, ext = os.path.splitext(safe)
                target = dest_dir / f"{stem}__{counter}{ext}"
                counter += 1

            try:
                with zf.open(info) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            except (OSError, zipfile.BadZipFile) as exc:
                result.failed_entries.append(f"{zip_path.name}::{decoded}: {exc}")
                log.warning("extract failed for %s: %s", decoded, exc)
                continue

            # Рекурсия для nested zip
            if target.suffix.lower() == ".zip":
                nested_dir = target.with_suffix("")  # отбрасываем .zip
                # Имя `4 Проект контракта.doc.zip` → подкаталог `4 Проект контракта.doc/`
                # но если двойное расширение `.doc` — финальный файл будет лежать там.
                nested_dir.mkdir(parents=True, exist_ok=True)
                result.nested_zips_unpacked += 1
                _extract_zip(target, nested_dir, result, depth + 1)
                # Сам nested zip удаляем после успешной распаковки
                try:
                    target.unlink()
                except OSError:
                    pass
            else:
                if _is_signature_file(safe):
                    result.signature_files.append(target)
                else:
                    result.extracted_files.append(target)


def unpack_tender_archive(
    archive_path: Path | str,
    output_root: Path | str,
    tender_id: str | None = None,
) -> UnpackResult:
    """Распаковать один тендерный zip-архив с рекурсивным разворачиванием nested zips.

    :param archive_path: путь к zip-архиву (типично `Z:\\tenders\\<topic>\\DDMMYY\\*.zip`)
    :param output_root: корневая папка для распаковки. Внутри будет создан подкаталог
                        с tender_id (или с именем архива, если id не передан).
    :param tender_id: глобальный ID тендера (`TL2530033598`). Если None — выводится
                       из имени архива по pattern `__TL<digits>.zip`.
    """
    archive_path = Path(archive_path)
    if not archive_path.exists():
        raise FileNotFoundError(archive_path)

    output_root = Path(output_root)

    # Вытащить tender_id из имени, если не передан
    if tender_id is None:
        stem = archive_path.stem  # без .zip
        if "__TL" in stem:
            tender_id = "TL" + stem.split("__TL", 1)[1]
        else:
            tender_id = stem

    output_dir = output_root / tender_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = UnpackResult(
        tender_id=tender_id,
        source_zip=archive_path,
        output_dir=output_dir,
    )

    _extract_zip(archive_path, output_dir, result, depth=0)

    log.info(
        "unpacked %s → %s: %d files (+ %d signatures, %d nested zips, %d errors)",
        archive_path.name,
        output_dir,
        len(result.extracted_files),
        len(result.signature_files),
        result.nested_zips_unpacked,
        len(result.failed_entries),
    )
    return result
