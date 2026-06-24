"""Нормализация значений характеристик из ТЗ в structured form.

На входе — raw текст из ячейки КТРУ-таблицы или из параграфа ТЗ:
  "≥ 80", "≥ 5 и ≤ 60", "±0,4", "Наличие", "≤ 120 (предельно)",
  "от 30 до 300", "30…300", "Да", "Нет", "Не менее 50",
  "от температуры окружающей среды + 5 до 80"

На выходе — `NormalizedValue` со структурой:
  {
    "op": ">=" | "<=" | "==" | "between" | "range" | "tolerance" | "presence",
    "value": float|None,
    "min": float|None,
    "max": float|None,
    "tolerance": float|None,
    "presence": bool|None,
    "unit": str,                # извлечённая единица если есть
    "raw": str,                 # исходный текст
    "confidence": float         # 0..1
  }

Это primary input для `matcher.py` — он использует normalized values чтобы
сравнивать ТЗ-требование с product.base_specs / product_configuration.specs.

Парсер консервативный: если не уверен — confidence низкий + сохраняет raw.
LLM-fallback (Haiku) для неоднозначных случаев — отдельная функция.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# Символы операторов в кириллических и латинских тендерных текстах
OP_GTE = re.compile(r"\s*(?:≥|>=|не\s+менее|от\s|не\s+мен\.|минимум|не\s+ниже|больше\s+или\s+равно)\s*", re.IGNORECASE)
OP_LTE = re.compile(r"\s*(?:≤|<=|не\s+более|до\s|не\s+бол\.|максимум|не\s+выше|меньше\s+или\s+равно)\s*", re.IGNORECASE)
OP_GT  = re.compile(r"\s*(?:>|больше|свыше)\s*", re.IGNORECASE)
OP_LT  = re.compile(r"\s*(?:<|меньше)\s*", re.IGNORECASE)
OP_EQ  = re.compile(r"\s*(?:равно|равен)\s+", re.IGNORECASE)

TOLERANCE = re.compile(r"[±\+\-]\s*(\d+(?:[\.,]\d+)?)", re.IGNORECASE)

# Числа (могут содержать запятую как десятичный разделитель)
NUMBER = re.compile(r"-?\d+(?:[\.,]\d+)?")

# Диапазон через тире / "и" / "..." / "от ... до"
RANGE_OT_DO = re.compile(
    r"от\s+(-?\d+(?:[\.,]\d+)?)\s+до\s+(-?\d+(?:[\.,]\d+)?)",
    re.IGNORECASE,
)
RANGE_GTE_AND_LTE = re.compile(
    r"(?:≥|>=)\s*(-?\d+(?:[\.,]\d+)?)\s+(?:и|,)\s*(?:≤|<=)\s*(-?\d+(?:[\.,]\d+)?)",
    re.IGNORECASE,
)
RANGE_DASH = re.compile(
    r"(-?\d+(?:[\.,]\d+)?)\s*(?:[—–\-…]|до|to)\s*(-?\d+(?:[\.,]\d+)?)",
    re.IGNORECASE,
)

# "Наличие" / "Да" / "Нет" / "Отсутствие"
PRESENCE_YES = re.compile(r"^\s*(?:наличие|да|есть|присутствует|имеется|\+)\s*$", re.IGNORECASE)
PRESENCE_NO = re.compile(r"^\s*(?:отсутствие|нет|отсутствует|-|без)\s*$", re.IGNORECASE)

# Единицы измерения часто фигурируют в отдельной колонке КТРУ-таблицы,
# но иногда вписаны прямо в значение: "≥ 80 л", "≤ 0,4 °C".
UNIT_PATTERNS = [
    (re.compile(r"\b(?:л|литр|liter|L)\b", re.IGNORECASE), "L"),
    (re.compile(r"\b(?:мл|миллилитр|mL)\b", re.IGNORECASE), "mL"),
    (re.compile(r"\b(?:°[CC]|градус(?:а|ов)?\s+(?:Цельси|целс))\b", re.IGNORECASE), "°C"),
    (re.compile(r"\b(?:кг|kg|килограмм)\b", re.IGNORECASE), "kg"),
    (re.compile(r"\b(?:г|gr?am?|gr)\b", re.IGNORECASE), "g"),
    (re.compile(r"\b(?:мм|mm|миллиметр)\b", re.IGNORECASE), "mm"),
    (re.compile(r"\b(?:см|cm|сантиметр)\b", re.IGNORECASE), "cm"),
    (re.compile(r"\b(?:м|m|метр)\b", re.IGNORECASE), "m"),
    (re.compile(r"\b(?:Вт|W|ватт|watt)\b", re.IGNORECASE), "W"),
    (re.compile(r"\b(?:кВт|kW|киловатт)\b", re.IGNORECASE), "kW"),
    (re.compile(r"\b(?:В|V|вольт|volt)\b", re.IGNORECASE), "V"),
    (re.compile(r"\b(?:А|A|ампер|ampere)\b", re.IGNORECASE), "A"),
    (re.compile(r"\b(?:Гц|Hz|герц)\b", re.IGNORECASE), "Hz"),
    (re.compile(r"\b(?:%|процент)\b", re.IGNORECASE), "%"),
    (re.compile(r"\b(?:бар|bar)\b", re.IGNORECASE), "bar"),
    (re.compile(r"\b(?:атм|atm|atmosphere)\b", re.IGNORECASE), "atm"),
    (re.compile(r"\b(?:Па|Pa|паскаль)\b", re.IGNORECASE), "Pa"),
    (re.compile(r"\bмин(?:ут)?\b", re.IGNORECASE), "min"),
    (re.compile(r"\bч(?:ас(?:ов)?)?\b", re.IGNORECASE), "h"),
    (re.compile(r"\bштук[аи]?\b", re.IGNORECASE), "pcs"),
]


@dataclass
class NormalizedValue:
    """Результат парсинга одного значения характеристики."""

    op: str = ""                       # ">=" | "<=" | ">" | "<" | "==" | "range" | "tolerance" | "presence" | "raw"
    value: float | None = None         # для скаляра (op == "==", ">=", "<=", ">", "<")
    min: float | None = None           # для range — нижняя граница
    max: float | None = None           # для range — верхняя граница
    tolerance: float | None = None     # для "±0.4"
    presence: bool | None = None       # для "Наличие" / "Отсутствие"
    unit: str = ""                     # извлечённая единица или пусто
    raw: str = ""                      # исходный текст
    confidence: float = 1.0            # 0..1, как уверены в парсинге

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "value": self.value,
            "min": self.min,
            "max": self.max,
            "tolerance": self.tolerance,
            "presence": self.presence,
            "unit": self.unit,
            "raw": self.raw,
            "confidence": self.confidence,
        }


def _to_float(s: str) -> float | None:
    """Преобразовать строку с числом (с запятой или точкой) в float."""
    if not s:
        return None
    s = s.replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _extract_unit(text: str) -> str:
    """Найти единицу в тексте; возвращает первую найденную или пусто."""
    for pat, unit in UNIT_PATTERNS:
        if pat.search(text):
            return unit
    return ""


def parse_value(raw: str, hint_unit: str = "") -> NormalizedValue:
    """Главный entrypoint — парсинг одного значения характеристики.

    :param raw: текст из ячейки КТРУ-таблицы (например ``"≥ 80"``, ``"±0,4"``, ``"Наличие"``)
    :param hint_unit: единица из соседней колонки таблицы (если известна — будет проставлена)
    :return: ``NormalizedValue`` с одним заполненным `op`.
    """
    text = (raw or "").strip()
    result = NormalizedValue(raw=text, unit=hint_unit)

    if not text:
        result.op = "raw"
        result.confidence = 0.0
        return result

    # 1. presence — "Наличие" / "Да" / "Нет"
    if PRESENCE_YES.match(text):
        result.op = "presence"
        result.presence = True
        return result
    if PRESENCE_NO.match(text):
        result.op = "presence"
        result.presence = False
        return result

    # извлечём unit если ещё не задан hint
    if not result.unit:
        result.unit = _extract_unit(text)

    # 2. tolerance — "±0,4"
    m_tol = TOLERANCE.search(text)
    if m_tol and "±" in text:
        v = _to_float(m_tol.group(1))
        if v is not None:
            result.op = "tolerance"
            result.tolerance = v
            return result

    # 3. range — приоритет от более специфичных к общим
    m = RANGE_GTE_AND_LTE.search(text)
    if m:
        result.op = "range"
        result.min = _to_float(m.group(1))
        result.max = _to_float(m.group(2))
        return result

    m = RANGE_OT_DO.search(text)
    if m:
        result.op = "range"
        result.min = _to_float(m.group(1))
        result.max = _to_float(m.group(2))
        return result

    m = RANGE_DASH.search(text)
    # NB: dash-range спорнее (тире может быть знаком "минус"). Проверим что
    # обе границы положительные и текст не содержит явно одного числа.
    if m:
        a = _to_float(m.group(1))
        b = _to_float(m.group(2))
        if a is not None and b is not None and a < b and len(NUMBER.findall(text)) == 2:
            result.op = "range"
            result.min = a
            result.max = b
            result.confidence = 0.9  # ниже из-за неоднозначности dash
            return result

    # 4. ops: >= / <= / > / < / == / "не менее" / "не более"
    nums = NUMBER.findall(text)

    if OP_GTE.search(text) and nums:
        result.op = ">="
        result.value = _to_float(nums[0])
        return result
    if OP_LTE.search(text) and nums:
        result.op = "<="
        result.value = _to_float(nums[0])
        return result
    if OP_GT.search(text) and nums:
        result.op = ">"
        result.value = _to_float(nums[0])
        return result
    if OP_LT.search(text) and nums:
        result.op = "<"
        result.value = _to_float(nums[0])
        return result

    # 5. чистое число без оператора — exact
    if len(nums) == 1:
        result.op = "=="
        result.value = _to_float(nums[0])
        return result

    # 6. fallback — raw
    result.op = "raw"
    result.confidence = 0.3
    return result


# ============================================================================
# Сравнение нормализованного требования из ТЗ с реальным значением каталога
# ============================================================================

def satisfies(requirement: NormalizedValue, catalog_value: Any) -> tuple[bool, str]:
    """Проверить — удовлетворяет ли `catalog_value` требованию `requirement`.

    :param requirement: NormalizedValue из ТЗ ("≥ 80 л")
    :param catalog_value: значение из product.base_specs (может быть int/float/dict/str)
    :return: (passes: bool, reason: str)
    """
    if requirement.op == "raw":
        return (False, "requirement is raw text, cannot compare")

    if requirement.op == "presence":
        # Каталог имеет такую фичу? Truthy/falsy.
        has = bool(catalog_value)
        if requirement.presence is True:
            return (has, f"need presence; catalog has={has}")
        if requirement.presence is False:
            return (not has, f"need absence; catalog has={has}")

    # Для скалярных операторов нужно числовое catalog_value
    cv = _to_float_any(catalog_value)
    if cv is None:
        return (False, f"catalog value {catalog_value!r} is not numeric")

    if requirement.op == ">=":
        return (cv >= requirement.value, f"{cv} >= {requirement.value}")
    if requirement.op == "<=":
        return (cv <= requirement.value, f"{cv} <= {requirement.value}")
    if requirement.op == ">":
        return (cv > requirement.value, f"{cv} > {requirement.value}")
    if requirement.op == "<":
        return (cv < requirement.value, f"{cv} < {requirement.value}")
    if requirement.op == "==":
        return (abs(cv - requirement.value) < 1e-9, f"{cv} == {requirement.value}")
    if requirement.op == "tolerance":
        # catalog должен быть АКЦЕНТ ≤ требуемого допуска (строже = лучше)
        return (cv <= requirement.tolerance, f"|catalog_tolerance|={cv} <= required_tol={requirement.tolerance}")
    if requirement.op == "range":
        # Здесь две интерпретации:
        #   1. (default) catalog должен ВКЛЮЧАТЬ всю требуемую область — catalog.min<=req.min, catalog.max>=req.max
        #   2. (point) catalog — точка, должна быть внутри [req.min, req.max]
        # При cv-как-точке — используем (2).
        return (requirement.min <= cv <= requirement.max,
                f"{requirement.min} <= {cv} <= {requirement.max}")

    return (False, f"unknown op: {requirement.op}")


def _to_float_any(v: Any) -> float | None:
    """Конвертировать что угодно (int/float/dict с 'value'/'min'+'max') в float."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        return _to_float(v)
    if isinstance(v, dict):
        if "value" in v:
            return _to_float_any(v["value"])
        if "min" in v and "max" in v:
            return (float(v["min"]) + float(v["max"])) / 2.0
    return None


# ============================================================================
# Smoke test
# ============================================================================

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    cases = [
        ("≥ 80", "L"),
        ("≥ 5 и ≤ 60", "°C"),
        ("±0,4", "°C"),
        ("Наличие", ""),
        ("Отсутствие", ""),
        ("≤ 120", "min"),
        ("≥ 500", "h"),
        ("от 30 до 300", "°C"),
        ("30…300", "°C"),
        ("Не менее 50", "L"),
        ("Не более 1.5", "kg"),
        ("220", "V"),
        ("2x150", ""),  # неоднозначный — должно стать raw
    ]
    for raw, hint in cases:
        nv = parse_value(raw, hint)
        print(f"  {raw!r:30}  →  {nv.to_dict()}")
