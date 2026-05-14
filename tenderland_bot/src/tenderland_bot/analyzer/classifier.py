"""Классификация файлов внутри распакованного тендера.

Идея проста: имена файлов в РФ-тендерах сильно типизированы (ФЗ-44 / 223-ФЗ /
коммерческие площадки). Сначала прогоняем эвристику по имени, потом по
расширению, потом фолбэк — `unknown` (можно отдать LLM при необходимости).
"""
from __future__ import annotations

import enum
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


class FileCategory(str, enum.Enum):
    """Типы файлов в tender package."""

    TZ = "tz"                       # техническое задание / описание объекта закупки
    PRICE_CALC = "price_calc"       # расчёт/обоснование НМЦК (ОНМЦК)
    CONTRACT = "contract"           # проект контракта / договора
    NOTIFICATION = "notification"   # извещение (печатная форма)
    APPLICATION_FORM = "application_form"  # требования к заявке / форма заявки
    QUOTATION_REQUEST = "quotation_request"  # "Запрос цен" — совмещает ТЗ + НМЦК для small tenders
    SIGNATURE = "signature"         # EDS_*.sig / .sgn — отдельная категория, не для анализа
    UNKNOWN = "unknown"

    @property
    def is_analyzable(self) -> bool:
        """Категории по которым extractor будет работать."""
        return self in (
            FileCategory.TZ,
            FileCategory.QUOTATION_REQUEST,
            FileCategory.CONTRACT,           # иногда ТЗ зашито в приложение к контракту
            FileCategory.PRICE_CALC,         # цены полезны для проверки бюджета
            FileCategory.NOTIFICATION,       # на коммерческих площадках вся спецификация в HTML
        )


# Регулярки — case-insensitive, по нормализованному имени (lower, без двойных пробелов)
# Порядок важен: более специфичные паттерны идут первыми.
_RULES: list[tuple[FileCategory, re.Pattern[str]]] = [
    # ТЗ — самый важный класс
    (FileCategory.TZ, re.compile(
        r"(описание\s+объекта\s+закупки"
        r"|техническ(ое|их)\s+задани"
        r"|техзадан"
        r"|\bтз\b"
        r"|описание\s+товара"
        r"|спецификац"
        r"|характеристики)",
        re.IGNORECASE,
    )),
    # Запрос цен — частая форма в малобюджетных тендерах (совмещает ТЗ + НМЦК)
    (FileCategory.QUOTATION_REQUEST, re.compile(
        r"запрос\s+цен", re.IGNORECASE,
    )),
    # Извещение
    (FileCategory.NOTIFICATION, re.compile(
        r"(печатн\w*\s+форма\s+извещени"
        r"|^извещени"
        r"|общи(е|х)\s+услови(я|й)\s+закупки)",
        re.IGNORECASE,
    )),
    # НМЦК / расчёт цены
    (FileCategory.PRICE_CALC, re.compile(
        r"(онмцк"
        r"|нмцк"
        r"|расч[её]т.*цен"
        r"|обоснован\w*\s+(нмцк|цен|начальн))",
        re.IGNORECASE,
    )),
    # Контракт / договор
    (FileCategory.CONTRACT, re.compile(
        r"(проект\s+контракт"
        r"|проект\s+договор"
        r"|\bконтракт\b"
        r"|\bдоговор\b)",
        re.IGNORECASE,
    )),
    # Требования к заявке / форма заявки
    (FileCategory.APPLICATION_FORM, re.compile(
        r"(требовани\w*\s+к\s+заявк"
        r"|инструкц\w*\s+по.*заполнен"
        r"|форма\s+заявки)",
        re.IGNORECASE,
    )),
    # Подписи (на случай если попали в analyzable файлы)
    (FileCategory.SIGNATURE, re.compile(
        r"^(eds_|.+\.sig$|.+\.sgn$)", re.IGNORECASE,
    )),
]


# Расширения которые точно не имеет смысла анализировать
_BINARY_EXTS = {".sig", ".sgn", ".p7s", ".pdf.sig"}


@dataclass
class ClassifiedItem:
    """Один файл после классификации."""

    path: Path
    category: FileCategory
    matched_rule: str  # для отладки: какое регулярное выражение сработало
    size_bytes: int

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def ext(self) -> str:
        return self.path.suffix.lower()


def _normalize_name(name: str) -> str:
    """Удалить ведущие цифры/префиксы типа `1 ` `4 ` `ЭА `."""
    # Не убираем — наоборот пусть остаются для контекста.
    return name.strip().lower()


def classify_file(path: Path) -> ClassifiedItem:
    """Определить категорию одного файла по имени."""
    name = path.name
    normalized = _normalize_name(name)

    # Подписи по расширению
    if path.suffix.lower() in _BINARY_EXTS:
        return ClassifiedItem(
            path=path,
            category=FileCategory.SIGNATURE,
            matched_rule="binary_ext",
            size_bytes=path.stat().st_size if path.exists() else 0,
        )

    for category, pattern in _RULES:
        if pattern.search(normalized):
            return ClassifiedItem(
                path=path,
                category=category,
                matched_rule=pattern.pattern,
                size_bytes=path.stat().st_size if path.exists() else 0,
            )

    return ClassifiedItem(
        path=path,
        category=FileCategory.UNKNOWN,
        matched_rule="",
        size_bytes=path.stat().st_size if path.exists() else 0,
    )


def classify_files(files: list[Path]) -> dict[FileCategory, list[ClassifiedItem]]:
    """Классифицировать список файлов и сгруппировать по категориям."""
    result: dict[FileCategory, list[ClassifiedItem]] = defaultdict(list)
    for f in files:
        item = classify_file(f)
        result[item.category].append(item)
    return dict(result)
