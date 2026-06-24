# -*- coding: utf-8 -*-
"""Probe-скрипт: пройти по диапазону autosearch id через GetAutosearch и собрать
инвентарь, не упираясь в HTTP 500 GetAutosearchList.

Запускается из tenderland_bot/ (нужен .env с TL_API_KEY).

Usage:
    PYTHONPATH=src python scripts/probe_autosearch_range.py 373300 373430

Output:
    _api_check/by_id/<id>.json        — параметры каждого живого автопоиска
    _api_check/inventory_<DDMMYY>.json — машинная сводка
    _api_check/inventory_<DDMMYY>.txt  — человекочитаемая сводка
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

from tenderland_bot.api_client import TenderlandAPIError, TenderlandClient
from tenderland_bot.config import load_settings
from tenderland_bot.md_parser import parse_keywords_dir


def filter_shape(params: dict) -> dict:
    """Свести параметры в компактный вид для сравнения с темами."""
    out = {
        "filter_kind": None,        # "name+files" | "name_only" | "files_only" | "keywords_136" | "contract_*" | "other"
        "include_len": 0,
        "exclude_len": 0,
        "include_head": "",
        "status_value": None,
        "status_value_type": None,  # "int" | "str" | None
        "interval": params.get("interval"),
        "has_status_filter": False,
        "fields_count": len(params.get("fields") or []),
    }
    and_groups = (params.get("filters") or {}).get("and") or []
    text_filters: list[dict] = []
    for g in and_groups:
        if "or" in g:
            for sub in g["or"]:
                if sub.get("type") == "text":
                    text_filters.append(sub)
        elif g.get("type") == "text":
            text_filters.append(g)
        if g.get("name") == "tender_status":
            out["has_status_filter"] = True
            v = g.get("value")
            out["status_value"] = v
            out["status_value_type"] = "int" if isinstance(v, int) else (
                "str" if isinstance(v, str) else type(v).__name__)
    # filter_kind по полям
    names = sorted({tf.get("name") for tf in text_filters if tf.get("name")})
    if names == ["tender_files", "tender_name"]:
        out["filter_kind"] = "name+files"
    elif names == ["tender_name"]:
        out["filter_kind"] = "name_only"
    elif names == ["tender_files"]:
        out["filter_kind"] = "files_only"
    elif "tender_keywords_include" in names or any("keywords" in n for n in names):
        out["filter_kind"] = "keywords_136"
    elif any(n.startswith("contract_") for n in names):
        out["filter_kind"] = "contract_*"
    elif names:
        out["filter_kind"] = "+".join(names)
    # длина и сниппет — берём первое поле где есть include
    for tf in text_filters:
        inc = tf.get("include") or ""
        exc = tf.get("exclude") or ""
        if inc:
            out["include_len"] = len(inc)
            out["exclude_len"] = len(exc)
            out["include_head"] = inc[:80]
            break
    return out


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    start_id = int(sys.argv[1])
    end_id = int(sys.argv[2])

    # Каталог тем (для сопоставления по длине)
    config_dir = Path(__file__).resolve().parents[1] / "config"
    topics = parse_keywords_dir(config_dir)
    topics_by_inc_len = {}
    for name, t in topics.items():
        topics_by_inc_len.setdefault(len(t.include_text), []).append(name)

    settings = load_settings()
    out_root = Path(__file__).resolve().parents[1] / "_api_check"
    by_id = out_root / "by_id"
    by_id.mkdir(parents=True, exist_ok=True)

    inventory = []
    n_ok = 0
    n_404 = 0
    n_err = 0
    started = time.time()

    print(f"Probe range {start_id}..{end_id} ({end_id - start_id + 1} ids)...")
    with TenderlandClient(api_key=settings.api_key, base_url=settings.base_url,
                          timeout=settings.http_timeout) as client:
        for asid in range(start_id, end_id + 1):
            try:
                data = client.get_autosearch(asid)
            except TenderlandAPIError as e:
                if e.http_status in (400, 404):
                    n_404 += 1
                    continue
                n_err += 1
                print(f"  {asid}: ERROR {e.code} {e.description!r}")
                continue
            except Exception as e:
                n_err += 1
                print(f"  {asid}: EXCEPTION {type(e).__name__}: {e}")
                continue
            n_ok += 1
            (by_id / f"{asid}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            shape = filter_shape(data)
            shape["id"] = asid
            # сопоставление по длине INCLUDE
            matched = topics_by_inc_len.get(shape["include_len"], [])
            shape["likely_topic"] = matched[0] if len(matched) == 1 else (
                "|".join(matched) if matched else None)
            inventory.append(shape)
            print(f"  {asid}: kind={shape['filter_kind']:<14} inc={shape['include_len']:>5}ch "
                  f"exc={shape['exclude_len']:>5}ch status={shape['status_value_type']} "
                  f"interval={shape['interval']} topic={shape['likely_topic']}")
            time.sleep(0.1)  # лёгкая задержка между запросами

    elapsed = time.time() - started
    print(f"\nDone in {elapsed:.1f}s. live={n_ok} 404={n_404} errors={n_err}")

    # Сводка
    stamp = date.today().strftime("%d%m%y")
    json_out = out_root / f"inventory_{stamp}.json"
    txt_out = out_root / f"inventory_{stamp}.txt"
    json_out.write_text(json.dumps(inventory, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    # Текстовая сводка с группировкой
    lines = [
        f"Probe range {start_id}..{end_id}",
        f"Live autosearches: {n_ok}    404/missing: {n_404}    errors: {n_err}",
        "",
        f"{'id':>7}  {'kind':<14}  {'inc':>6}  {'exc':>6}  {'status':>6}  {'interval':<10}  topic",
        "-" * 100,
    ]
    for it in inventory:
        lines.append(
            f"{it['id']:>7}  {str(it['filter_kind']):<14}  {it['include_len']:>6}  "
            f"{it['exclude_len']:>6}  {str(it['status_value_type']):>6}  "
            f"{str(it['interval']):<10}  {it['likely_topic'] or ''}"
        )
    # сводка по filter_kind
    from collections import Counter
    kinds = Counter(it["filter_kind"] for it in inventory)
    status_types = Counter(it["status_value_type"] for it in inventory)
    lines += ["", "By filter_kind:"]
    for k, v in kinds.most_common():
        lines.append(f"  {k}: {v}")
    lines += ["", "By tender_status value type:"]
    for k, v in status_types.most_common():
        lines.append(f"  {k}: {v}")
    txt_out.write_text("\n".join(lines), encoding="utf-8")

    print(f"\nSaved:\n  {json_out}\n  {txt_out}")


if __name__ == "__main__":
    main()
