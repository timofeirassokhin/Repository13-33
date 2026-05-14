"""Matcher: сравнение extracted specs из тендера с каталогом продукции.

Архитектура (см. `docs/data-layers-architecture.md` раздел 4.3):

  extracted_specs (LAYER 3 part B)        product.base_specs (LAYER 2)
        ↓                                            ↓
        └─────────────→ matcher ←─────────────────────┘
                          ↓
                  list[MatchCandidate] (top-N продуктов)
                          ↓
                  decision.py → pass / review / fail

Алгоритм:
  1. Сужение кандидатов
       a. По ОКПД2 → category (через mapping table)
       b. По brand-hint (из product_name тендера, через synonyms / brand fuzzy)
       c. По category (broad — все приборы данного типа)
  2. Per-candidate: матчим каждый extracted spec против product.base_specs
       - normalize требование через value_parser.parse_value
       - найти соответствующий spec в product.base_specs (по name / synonyms)
       - проверить через value_parser.satisfies
  3. Score:
       - 100% если все required specs прошли
       - -20% за каждый required spec который не прошёл
       - -10% за каждый non-required который не прошёл
       - -5% за каждый требуемый spec missing в product (no data)
  4. Sort by score, return top-N
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from .extractor import ExtractedSpec
from .value_parser import NormalizedValue, parse_value, satisfies

log = logging.getLogger(__name__)


# ============================================================================
# Mapping ОКПД2 → product_category_t
# (минимальный набор — расширяется по мере появления тендеров)
# ============================================================================

OKPD2_TO_CATEGORIES: dict[str, list[str]] = {
    # хроматография
    "26.51.66.140": ["hplc_system", "gc_system", "mass_spectrometer"],
    "26.51.53.110": ["hplc_system", "gc_system", "mass_spectrometer", "icp_ms", "icp_oes"],
    "26.51.53.130": ["hplc_system", "gc_system"],
    # секвенаторы
    "26.60.12.119": ["sequencer_platform"],
    "26.51.53.141": ["sequencer_platform"],  # Sanger CE
    # общелаб
    "32.50.50.190-00000839": ["incubator", "drying_oven", "climate_chamber"],
    "32.50.50.190-00000840": ["incubator"],
    "32.50.50.190-00000841": ["incubator"],
    "26.51.66.190-00000128": ["centrifuge"],  # на самом деле sterilizer, но в ОКПД2 пересекается
    "27.51.21.190": ["drying_oven", "climate_chamber"],
    "28.93.17.190": ["incubator", "drying_oven", "climate_chamber"],
    # центрифуги
    "28.29.41.110": ["centrifuge"],
    "28.29.41.190": ["centrifuge"],
    # стерилизаторы / автоклавы (если будут отдельные category — добавим)
    # реагенты / расходники
    "21.20.23.110": ["ngs_library_prep_kit", "ngs_target_capture_panel", "pcr_kit", "consumable"],
    "21.20.23.111": ["ngs_library_prep_kit", "ngs_target_capture_panel"],
}


def categories_for_okpd2(code: str) -> list[str]:
    """Вернёт product_category_t значения по ОКПД2-коду; пусто если не известен."""
    if not code:
        return []
    if code in OKPD2_TO_CATEGORIES:
        return OKPD2_TO_CATEGORIES[code]
    # fallback: попробовать сократить до префикса
    for length in (15, 13, 10, 8, 6):
        if len(code) >= length:
            prefix = code[:length]
            if prefix in OKPD2_TO_CATEGORIES:
                return OKPD2_TO_CATEGORIES[prefix]
    return []


# ============================================================================
# Mapping: ru-имя характеристики из ТЗ → ключ product.base_specs
# (мы строим это по мере появления реальных кейсов; LLM-fallback покрывает unknown)
# ============================================================================

# Каноническое представление: lowercase, без пунктуации
SPEC_NAME_ALIASES: dict[str, list[str]] = {
    # для термостатов / инкубаторов
    "internal_volume_l": [
        "объем", "объём", "вместимость", "полезный объем",
        "объем рабочей камеры", "объем камеры",
    ],
    "temperature_range_c": [
        "рабочий диапазон температур", "температурный диапазон",
        "диапазон рабочей температуры", "диапазон температур",
    ],
    "temperature_accuracy_c": [
        "максимальное отклонение температуры", "точность поддержания",
        "погрешность поддержания температуры", "стабильность температуры",
    ],
    "temperature_uniformity_c": [
        "равномерность температуры", "пространственная неоднородность",
    ],
    "co2_control": [
        "автоматическая регуляция co2", "co2-контроль", "содержание co2",
    ],
    "humidity_control": [
        "влажность", "регуляция влажности",
    ],
    # для HPLC
    "max_pressure_bar": [
        "максимальное давление", "рабочее давление", "предельное давление",
    ],
    "flow_rate_range_ml_min": [
        "диапазон скорости потока", "скорость потока",
    ],
    # для центрифуг
    "max_rcf_g": [
        "максимальная скорость вращения", "максимальное rcf", "максимальное ускорение",
    ],
    "max_rpm": [
        "максимальная скорость вращения об/мин", "максимальная скорость",
    ],
    "max_volume_ml": [
        "максимальный объем пробы", "вместимость ротора",
    ],
    # для секвенаторов
    "max_output_gb_per_run": [
        "максимальный выход данных", "общий объем данных",
    ],
    "read_lengths_supported": [
        "длина прочтения", "длина чтения", "паттерн чтения",
    ],
    # общие
    "power_w": [
        "потребляемая мощность", "мощность",
    ],
    "voltage_v": [
        "напряжение электропитания", "напряжение питания",
    ],
}


def _normalize_spec_name(name: str) -> str:
    """Lowercase + удалить пунктуацию + схлопнуть пробелы."""
    n = (name or "").lower().strip()
    n = re.sub(r"[,\.;:()\[\]/\\]", " ", n)
    n = re.sub(r"\s+", " ", n)
    return n


def find_catalog_key(tender_spec_name: str) -> str | None:
    """Найти canonical key product.base_specs для имени характеристики из ТЗ."""
    norm = _normalize_spec_name(tender_spec_name)
    for canonical, aliases in SPEC_NAME_ALIASES.items():
        for alias in aliases:
            if alias in norm or norm in alias:
                return canonical
    return None


# ============================================================================
# Структуры данных
# ============================================================================

@dataclass
class SpecMatch:
    """Результат сравнения одного требования с одним полем каталога."""

    tender_spec_name: str
    catalog_spec_key: str | None
    requirement: NormalizedValue
    catalog_value: Any = None
    passes: bool = False
    reason: str = ""
    required: bool | None = None     # is this required by tender? (из ExtractedSpec.required)
    status: str = "unknown"          # "pass" | "fail" | "missing_in_catalog" | "unmapped" | "low_confidence"


@dataclass
class MatchCandidate:
    """Один кандидат — продукт из каталога + анализ соответствия."""

    product_id: str                              # UUID как строка
    brand: str
    model: str
    category: str
    score: float = 0.0                            # 0..100
    matched_count: int = 0
    failed_count: int = 0
    missing_count: int = 0
    unmapped_count: int = 0
    spec_matches: list[SpecMatch] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_id": self.product_id,
            "brand": self.brand,
            "model": self.model,
            "category": self.category,
            "score": self.score,
            "matched_count": self.matched_count,
            "failed_count": self.failed_count,
            "missing_count": self.missing_count,
            "unmapped_count": self.unmapped_count,
            "reasoning": self.reasoning,
            "spec_matches": [
                {
                    "tender": sm.tender_spec_name,
                    "catalog_key": sm.catalog_spec_key,
                    "req": sm.requirement.to_dict() if sm.requirement else None,
                    "catalog_value": sm.catalog_value,
                    "passes": sm.passes,
                    "required": sm.required,
                    "status": sm.status,
                    "reason": sm.reason,
                }
                for sm in self.spec_matches
            ],
        }


# ============================================================================
# Главная функция матчинга
# ============================================================================

def match_one_candidate(
    product: dict[str, Any],
    tender_specs: list[ExtractedSpec],
) -> MatchCandidate:
    """Сравнить один кандидат-продукт с набором требований из ТЗ."""
    base_specs: dict[str, Any] = product.get("base_specs") or {}

    cand = MatchCandidate(
        product_id=str(product.get("id", "")),
        brand=product.get("brand", ""),
        model=product.get("model", ""),
        category=product.get("category", ""),
    )

    for ts in tender_specs:
        req = parse_value(ts.value_raw, hint_unit=ts.unit or "")
        catalog_key = find_catalog_key(ts.name)
        sm = SpecMatch(
            tender_spec_name=ts.name,
            catalog_spec_key=catalog_key,
            requirement=req,
            required=ts.required,
        )

        if catalog_key is None:
            sm.status = "unmapped"
            sm.reason = f"no mapping for tender-spec {ts.name!r}"
            cand.unmapped_count += 1
        elif req.op == "raw":
            sm.status = "low_confidence"
            sm.reason = f"cannot parse requirement {ts.value_raw!r}"
        elif catalog_key not in base_specs:
            sm.status = "missing_in_catalog"
            sm.reason = f"catalog has no {catalog_key!r}"
            cand.missing_count += 1
        else:
            sm.catalog_value = base_specs[catalog_key]
            ok, why = satisfies(req, sm.catalog_value)
            sm.passes = ok
            sm.reason = why
            sm.status = "pass" if ok else "fail"
            if ok:
                cand.matched_count += 1
            else:
                cand.failed_count += 1

        cand.spec_matches.append(sm)

    # === Score ===
    total = len(tender_specs)
    if total == 0:
        cand.score = 0.0
        cand.reasoning = "no specs to match"
        return cand

    score = 100.0
    # Штраф за fail
    for sm in cand.spec_matches:
        if sm.status == "fail":
            score -= 20.0 if sm.required else 10.0
        elif sm.status == "missing_in_catalog":
            score -= 5.0
        elif sm.status == "unmapped":
            score -= 3.0
        elif sm.status == "low_confidence":
            score -= 2.0
    cand.score = max(0.0, score)

    # Compose human reasoning
    summary_parts = []
    if cand.matched_count:
        summary_parts.append(f"совпало {cand.matched_count}")
    if cand.failed_count:
        critical_fails = sum(1 for sm in cand.spec_matches if sm.status == "fail" and sm.required)
        if critical_fails:
            summary_parts.append(f"критических несоответствий: {critical_fails}")
        else:
            summary_parts.append(f"несоответствий: {cand.failed_count}")
    if cand.missing_count:
        summary_parts.append(f"нет данных в каталоге: {cand.missing_count}")
    cand.reasoning = "; ".join(summary_parts) if summary_parts else "no matches at all"

    return cand


def match_tender_to_catalog(
    extracted_specs: list[ExtractedSpec],
    candidate_products: list[dict[str, Any]],
    *,
    top_n: int = 5,
) -> list[MatchCandidate]:
    """Запустить матчинг всех specs vs всех кандидатов; вернуть top_n по score.

    :param extracted_specs: список характеристик из ТЗ (из ExtractionResult.specs)
    :param candidate_products: список продуктов из каталога — уже отфильтрованных
            извне по ОКПД2 / category / brand. Здесь не делается дополнительной выборки —
            это работа caller'а (он знает БД).
    :param top_n: вернуть лучшие N кандидатов
    """
    results = [match_one_candidate(p, extracted_specs) for p in candidate_products]
    results.sort(key=lambda c: c.score, reverse=True)
    return results[:top_n]
