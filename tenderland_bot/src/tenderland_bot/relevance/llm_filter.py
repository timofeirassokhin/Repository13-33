"""Tier-2 LLM-фильтр для классификации тендеров по метаданным.

Без скачивания файлов — только то, что вернул Tenderland Export.
Использует Claude Haiku 4.5 через прямой Anthropic SDK с prompt caching:
  - system-prompt (~5K токенов с tier2_instructions.md) кешируется
  - per-tender user-prompt маленький (~200 токенов)
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Iterable

import anthropic

from .schema import Tier2Decision, ScoreBreakdown


# Стоимости Claude Haiku 4.5 за 1M токенов (на 2026-05)
# актуальная цена — https://docs.anthropic.com/en/docs/about-claude/pricing
COST_INPUT_PER_M = 1.0
COST_OUTPUT_PER_M = 5.0
COST_CACHE_WRITE_PER_M = 1.25
COST_CACHE_READ_PER_M = 0.10
DEFAULT_MODEL = "claude-haiku-4-5"


def _load_instructions() -> str:
    """Грузим tier2_instructions.md как system-prompt."""
    here = Path(__file__).resolve().parents[3]
    instr = here / "config" / "tier2_instructions.md"
    return instr.read_text(encoding="utf-8")


def _build_user_message(tender_meta: dict, topic: str) -> str:
    """Компактное описание одного тендера для LLM."""
    cust = tender_meta.get("customers") or []
    cust_short = ""
    cust_full = ""
    if cust:
        c0 = cust[0]
        cust_short = c0.get("lotCustomerShortName", "") or c0.get("customerShortName", "") or ""
        cust_full = c0.get("lotCustomerFullName", "") or c0.get("customerFullName", "") or ""
    cats = tender_meta.get("lotCategories") or []
    cat_str = "; ".join(str(c) for c in cats[:3])
    return (
        f"Тема автопоиска: {topic}\n"
        f"Название тендера: {tender_meta.get('name') or ''}\n"
        f"НМЦК: {tender_meta.get('beginPrice') or 0} ₽\n"
        f"Заказчик (краткое): {cust_short}\n"
        f"Заказчик (полное): {cust_full}\n"
        f"Регион: {tender_meta.get('region') or ''}\n"
        f"Тип закупки: {tender_meta.get('typeName') or ''}\n"
        f"Категории ОКПД2: {cat_str}\n"
        f"Дата окончания подачи: {tender_meta.get('endDate') or ''}\n"
        f"Файлов в архиве: {tender_meta.get('fileCount') or 'n/a'}\n"
        f"\nКлассифицируй этот тендер строго в JSON-формате из раздела 7 инструкций."
    )


def _extract_json(text: str) -> dict:
    """Из текста ответа LLM достать JSON-объект (даже если в code-блоке)."""
    text = text.strip()
    # snip из ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)
    # найти первую {...} группу
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no JSON in LLM response: {text[:200]!r}")
    # сбалансировать скобки
    depth = 0
    end = -1
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise ValueError(f"unbalanced JSON braces: {text[:200]!r}")
    return json.loads(text[start:end])


def _decision_from_response(
    raw: dict, tender_id: str, topic: str, usage: Any, model: str
) -> Tier2Decision:
    # bullet-proof: если LLM забыл какое-то поле — заполним дефолтами
    sb_raw = raw.get("score_breakdown") or {}
    sb = ScoreBreakdown(
        model_match=int(sb_raw.get("model_match", 0)),
        brand_match=int(sb_raw.get("brand_match", 0)),
        instrument_type=int(sb_raw.get("instrument_type", 0)),
        technique=int(sb_raw.get("technique", 0)),
        component=int(sb_raw.get("component", 0)),
        name_multiplier=int(sb_raw.get("name_multiplier", 1)),
        price_bonus=int(sb_raw.get("price_bonus", 0)),
        customer_bonus=int(sb_raw.get("customer_bonus", 0)),
    )
    in_t = getattr(usage, "input_tokens", 0) or 0
    out_t = getattr(usage, "output_tokens", 0) or 0
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost = (
        in_t * COST_INPUT_PER_M / 1_000_000
        + out_t * COST_OUTPUT_PER_M / 1_000_000
        + cache_create * COST_CACHE_WRITE_PER_M / 1_000_000
        + cache_read * COST_CACHE_READ_PER_M / 1_000_000
    )
    return Tier2Decision(
        tender_id=tender_id,
        topic=topic,
        relevance=raw.get("relevance", "review"),
        confidence=float(raw.get("confidence", 0.5)),
        score_breakdown=sb,
        matched_signals=list(raw.get("matched_signals") or []),
        customer_class=raw.get("customer_class", "unknown"),
        customer_type=raw.get("customer_type"),
        detected_class=raw.get("detected_class"),
        flags=list(raw.get("flags") or []),
        reasoning=raw.get("reasoning", ""),
        model=model,
        input_tokens=in_t + cache_create + cache_read,
        output_tokens=out_t,
        cost_usd=cost,
    )


def classify_tender(
    tender_meta: dict,
    topic: str,
    *,
    tender_id: str,
    client: anthropic.Anthropic | None = None,
    model: str = DEFAULT_MODEL,
    max_retries: int = 2,
) -> Tier2Decision:
    """Классифицировать один тендер. Использует prompt caching системного промпта."""
    if client is None:
        client = anthropic.Anthropic()
    system = _load_instructions()
    user_msg = _build_user_message(tender_meta, topic)

    for attempt in range(max_retries + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": system,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_msg}],
            )
            text = "".join(b.text for b in resp.content if hasattr(b, "text"))
            raw = _extract_json(text)
            return _decision_from_response(raw, tender_id, topic, resp.usage, model)
        except (json.JSONDecodeError, ValueError) as e:
            if attempt == max_retries:
                return Tier2Decision(
                    tender_id=tender_id,
                    topic=topic,
                    relevance="review",
                    confidence=0.5,
                    error=f"parse: {e}",
                    model=model,
                )
            time.sleep(0.5)
        except anthropic.APIError as e:
            if attempt == max_retries:
                return Tier2Decision(
                    tender_id=tender_id,
                    topic=topic,
                    relevance="review",
                    confidence=0.5,
                    error=f"api: {type(e).__name__}: {e}",
                    model=model,
                )
            time.sleep(1.0 * (attempt + 1))


def classify_batch(
    tasks: Iterable[tuple[str, str, dict]],
    *,
    model: str = DEFAULT_MODEL,
    progress_cb=None,
) -> list[Tier2Decision]:
    """Классифицировать пачку (tender_id, topic, meta).
    Последовательно, с prompt caching — system читается из кеша после первого вызова.
    """
    client = anthropic.Anthropic()
    out: list[Tier2Decision] = []
    tasks_list = list(tasks)
    for i, (tid, topic, meta) in enumerate(tasks_list, 1):
        d = classify_tender(meta, topic, tender_id=tid, client=client, model=model)
        out.append(d)
        if progress_cb:
            progress_cb(i, len(tasks_list), d)
    return out
