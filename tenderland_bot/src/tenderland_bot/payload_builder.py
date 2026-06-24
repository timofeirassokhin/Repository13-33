"""Сборка `Parameters` JSON для CreateAutosearch по шаблону id=96700 ('Оборудование').

Эталонный шейп (из реального дампа `GET /Api/v1/Search/GetAutosearch?autosearchId=96700`):

  {
    "fields":  [12 export-полей],
    "filters": {
      "and": [
        {"or": [                                # одна OR-группа из 2 фильтров
           {"id": 101, "name": "tender_files",  "type": "text", "include": ..., "exclude": ..., "isEnable": True, ...},
           {"id": 100, "name": "tender_name",   "type": "text", "include": ..., "exclude": ..., "isEnable": True, ...}
        ]},
        {"id": 115, "name": "tender_status", "type": "value", "value": 1, "isEnable": True}   # только активные
      ]
    },
    "interval": [0, 1]
  }

Смысл: каждое ключевое слово ищется И в `tender_name` И в `tender_files` (полнотекст
по документации тендера) — лот пройдёт хотя бы по одному из них (OR между двумя filters).
EXCLUDE применяется к обоим. `tender_status=1` — только активные тендеры.

Расширения которые я добавил:
- Дополнительные `tender_publishDate` (id=110) range "от N дней назад" — раскоментировать
  при необходимости. Без него возвращаются все тендеры, включая старые. Я НЕ ставлю по умолчанию,
  потому что у заказчика автопоиски конфигурятся через UI с датой, а fetcher CLI скачивает свежие
  через `Export/Create` + сортировку `tender_sysPublishDate.desc`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# === стандартные поля экспорта (12 полей из шаблона 96700) ===

DEFAULT_EXPORT_FIELDS: list[str] = [
    "tender_regNumber",
    "tender_name",
    "tender_beginPrice",
    "tender_lotCustomerShortName",
    "tender_publishDate",
    "tender_endDate",
    "tender_region",
    "tender_typeName",
    "tender_lotCategories",
    "tender_files",
    "tender_module",
    "tender_etpLink",
]


# === ID-словарь фильтров (из /Api/v1/Dictionary/GetFilterList) ===

FILTER_ID_TENDER_NAME = 100             # tender_name — поиск по названию (текст)
FILTER_ID_TENDER_FILES = 101            # tender_files — поиск по документации (текст)
FILTER_ID_TENDER_PUBLISH_DATE = 110     # tender_publishDate (range)
FILTER_ID_TENDER_END_DATE = 111         # tender_endDate (range) — не подтверждено,
                                        # см. ARCHITECTURE.md (Q2). Если не сработает — снимем.
FILTER_ID_TENDER_STATUS = 115           # tender_status — value: 1=активные
FILTER_ID_KEYWORDS_INCLUDE = 136        # tender_keywords_include — глобальный keyword фильтр
FILTER_ID_KEYWORDS_EXCLUDE = 137        # tender_keywords_exclude — глобальный keyword фильтр

# Тут есть нюанс: в шаблоне 96700 используются `id=100 tender_name` и `id=101 tender_files`
# в OR-группе, а НЕ глобальные 136/137 keywords. По факту это даёт **тот же результат**,
# но позволяет иметь отдельный INCLUDE/EXCLUDE на каждое поле (мы используем одинаковые).


@dataclass
class AutosearchParameters:
    """Структурированный билдер для `Parameters` JSON."""

    include_text: str
    exclude_text: str = ""
    export_fields: list[str] | None = None
    only_active_tenders: bool = True        # добавляет фильтр tender_status=1
    interval: tuple[int, int] = (0, 1)

    def to_dict(self) -> dict[str, Any]:
        """Собрать финальный JSON для отправки в CreateAutosearch."""
        fields = self.export_fields or DEFAULT_EXPORT_FIELDS.copy()

        # OR-группа: матч хотя бы по tender_name ИЛИ по tender_files
        or_filters: list[dict[str, Any]] = [
            {
                "id": FILTER_ID_TENDER_FILES,
                "name": "tender_files",
                "text": "По документации",
                "type": "text",
                "exclude": self.exclude_text,
                "include": self.include_text,
                "isEnable": True,
                "isVisible": True,
                "ordinalNumber": 4,
                "ordinalNumberLite": 5,
                "groupOrdinalNumber": 0,
            },
            {
                "id": FILTER_ID_TENDER_NAME,
                "name": "tender_name",
                "text": "Название тендера",
                "type": "text",
                "exclude": self.exclude_text,
                "include": self.include_text,
                "isEnable": True,
                "isVisible": True,
                "ordinalNumber": 2,
                "transliteration": False,
                "ordinalNumberLite": 3,
                "groupOrdinalNumber": 0,
            },
        ]

        and_groups: list[dict[str, Any]] = [{"or": or_filters}]

        if self.only_active_tenders:
            and_groups.append({
                "id": FILTER_ID_TENDER_STATUS,
                "name": "tender_status",
                "text": "Статус тендера",
                "type": "value",
                # CRITICAL: must be a STRING "1", not int 1.
                # Tenderland's ASP.NET deserializer crashes when listing autosearches
                # (GetAutosearchList → HTTP 500) if `value` is int — which is what broke
                # ids 369536 and 369543 on 2026-05-14. Bug discovered by comparing the
                # payload shape against reference autosearch id=96700.
                "value": "1",
                "isEnable": True,
            })

        return {
            "fields": fields,
            "filters": {"and": and_groups},
            "interval": list(self.interval),
        }


def build_parameters_from_topic(
    include_text: str,
    exclude_text: str = "",
    *,
    export_fields: list[str] | None = None,
    only_active_tenders: bool = True,
) -> dict[str, Any]:
    """Удобная функция-фасад: одна вызов → готовый Parameters dict."""
    return AutosearchParameters(
        include_text=include_text,
        exclude_text=exclude_text,
        export_fields=export_fields,
        only_active_tenders=only_active_tenders,
    ).to_dict()


# === небольшие хелперы для отображения ===

def parameters_summary(params: dict[str, Any]) -> str:
    """Краткое описание payload'а — для логов/CLI вывода."""
    fields = params.get("fields", [])
    and_groups = params.get("filters", {}).get("and", [])
    lines = [
        f"  fields: {len(fields)} ({', '.join(fields[:4])}, ...)",
        f"  filter groups: {len(and_groups)}",
    ]
    for i, grp in enumerate(and_groups):
        if "or" in grp:
            for sf in grp["or"]:
                inc_len = len(sf.get("include") or "")
                exc_len = len(sf.get("exclude") or "")
                lines.append(
                    f"    [{i}.or.{sf.get('name')}] include={inc_len}ch exclude={exc_len}ch"
                )
        else:
            lines.append(
                f"    [{i}] id={grp.get('id')} name={grp.get('name')} value={grp.get('value')}"
            )
    lines.append(f"  interval: {params.get('interval')}")
    return "\n".join(lines)
