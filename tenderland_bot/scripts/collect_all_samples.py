# -*- coding: utf-8 -*-
"""Сбор свежих выдач по всем 21 автопоиску для анализа шума.

Запуск:
    PYTHONPATH=src python scripts/collect_all_samples.py [--limit 30]

Выход:
    _api_check/all/<id>_<topic>.json     — сами тендеры (raw)
    _api_check/all/<id>_<topic>.txt      — компактная таблица для глаз (категории!)
    _api_check/all/_inventory.json       — мета по каждому автопоиску
                                            (total_count, кол-во полей в OR, есть ли date/НМЦК)
    _api_check/all/_inventory.txt        — табличка-сводка для пользователя
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

from tenderland_bot.api_client import TenderlandClient, TenderlandAPIError
from tenderland_bot.config import load_settings


# Маппинг id → topic (финальный после правок пользователя)
AUTOSEARCHES = [
    (373343, "01_LC_LCMS_GPC_Prep"),
    (373385, "02_GC_GCMS"),
    (373389, "03_ICP_OES"),
    (373392, "04_AAS"),
    (373396, "05_ICP_MS"),
    (373397, "06_IC"),
    (373398, "07_UV_Vis"),
    (373400, "08_FTIR"),
    (373401, "09_Service"),
    (373413, "10_Consumables"),
    (373417, "MDX_01_Sequencers"),
    (373430, "MDX_02_Reagents_Libraries"),
    (373451, "MDX_03_Oncology_Panels"),
    (373453, "MDX_04_NIPT_PGT_HLA"),
    (373454, "MDX_06_Sequencing_Services"),
    (373923, "LAB_01_Climate"),
    (373925, "LAB_02_Sterilization"),
    (373926, "LAB_03_Evaporation"),
    (373935, "LAB_04_Mixing_Homogenization"),
    (373954, "LAB_05_Reactors"),
    (373956, "CER_03_Liquid_Handling_Robotics"),
]


def parse_args():
    limit = 30
    for i, a in enumerate(sys.argv[1:]):
        if a == "--limit" and i + 1 < len(sys.argv[1:]):
            limit = int(sys.argv[2 + i])
    return limit


def filter_shape(params: dict) -> dict:
    """Какие поля в OR + есть ли date/НМЦК/категории фильтры."""
    out = {
        "or_fields": [],
        "has_publishdate": False,
        "publishdate_dynamic": None,
        "has_beginprice": False,
        "beginprice_from": None,
        "has_categories": False,
        "categories_filter": None,
        "has_ktru": False,
    }
    for grp in (params.get("filters") or {}).get("and") or []:
        if "or" in grp:
            for sub in grp["or"]:
                n = sub.get("name", "")
                if sub.get("type") == "text":
                    out["or_fields"].append(n)
        else:
            n = grp.get("name", "")
            if n == "tender_publishDate":
                out["has_publishdate"] = True
                dyn = {k: grp.get(k) for k in ("dynamicType", "dynamicValue", "dynamicPeriod") if k in grp}
                out["publishdate_dynamic"] = dyn or None
            elif n == "tender_beginPrice":
                out["has_beginprice"] = True
                out["beginprice_from"] = grp.get("from")
            elif n == "tender_lotCategories":
                out["has_categories"] = True
            elif n in ("tender_lotktru", "tender_lotktru2"):
                out["has_ktru"] = True
    return out


def fmt_money(v) -> str:
    if v is None or v == "":
        return ""
    try:
        n = float(v)
        return f"{n:,.0f}".replace(",", " ")
    except Exception:
        return str(v)


def short(s, n=70):
    if not s:
        return ""
    return str(s).replace("\n", " ").strip()[:n]


def main():
    limit = parse_args()
    out_root = Path(__file__).resolve().parents[1] / "_api_check" / "all"
    out_root.mkdir(parents=True, exist_ok=True)

    s = load_settings()
    inventory = []
    with TenderlandClient(api_key=s.api_key, base_url=s.base_url,
                          timeout=s.http_timeout) as c:
        for aid, topic in AUTOSEARCHES:
            try:
                params = c.get_autosearch(aid)
                shape = filter_shape(params)
                task = c.create_export(autosearch_id=aid, limit=limit, batch_size=min(limit, 100))
                total = task.total_count
                items = []
                if total > 0:
                    for it in c.iter_export(task.id, min(total, limit), batch_size=min(limit, 100)):
                        items.append(it)

                # raw JSON
                (out_root / f"{aid}_{topic}.json").write_text(
                    json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

                # компактный txt с категориями
                lines = [
                    f"# {topic} (id {aid})",
                    f"# total_count={total}, fetched={len(items)}, limit={limit}",
                    f"# shape: OR={shape['or_fields']}, date_dyn={shape['publishdate_dynamic']}, "
                    f"begin>={shape['beginprice_from']}, has_categories={shape['has_categories']}, has_ktru={shape['has_ktru']}",
                    "",
                    f"{'№':>3} | {'НМЦК':>14} | {'категории':<50} | название",
                    "-" * 130,
                ]
                for i, it in enumerate(items, 1):
                    t = it.get("tender", {})
                    nm = short(t.get("name", "") or "", 60)
                    bp = fmt_money(t.get("beginPrice"))
                    cats = t.get("lotCategories") or []
                    cat_str = "; ".join(short(c, 25) for c in cats[:2])
                    lines.append(f"{i:>3} | {bp:>14} | {cat_str:<50} | {nm}")
                (out_root / f"{aid}_{topic}.txt").write_text("\n".join(lines), encoding="utf-8")

                inventory.append({
                    "id": aid,
                    "topic": topic,
                    "total_count": total,
                    "sample_size": len(items),
                    "shape": shape,
                })
                print(f"  {aid} {topic:<35} total={total:>4} sampled={len(items)} "
                      f"OR={shape['or_fields']} dyn={shape['publishdate_dynamic']}")
            except TenderlandAPIError as e:
                print(f"  {aid} {topic} ERR {e.code}: {e.description}")
                inventory.append({"id": aid, "topic": topic, "error": f"{e.code}: {e.description}"})
            time.sleep(0.2)

        st = c.get_statistic()

    # _inventory.json + _inventory.txt
    (out_root / "_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"Inventory of {len(inventory)} autosearches",
        f"Quota after collection: {st.get('dailyQueryCount')}/{st.get('dailyQueryLimit')} req, "
        f"{st.get('dailyDataTransferredCount')}/{st.get('dailyDataTransferredLimit')} units",
        "",
        f"{'id':>7} | {'topic':<35} | {'total':>5} | {'OR fields':<45} | {'date_dyn':<22} | begin>= | cats | ktru",
        "-" * 160,
    ]
    for inv in inventory:
        if "error" in inv:
            lines.append(f"{inv['id']:>7} | {inv['topic']:<35} | ERROR: {inv['error']}")
            continue
        sh = inv["shape"]
        or_s = ",".join(f.replace("tender_", "") for f in sh["or_fields"])[:43]
        dyn = sh["publishdate_dynamic"] or "—"
        dyn_s = (f"d={dyn.get('dynamicValue')}/{dyn.get('dynamicPeriod')}"
                 if isinstance(dyn, dict) else str(dyn))[:20]
        bp = str(sh["beginprice_from"] or "—")[:8]
        cats = "+" if sh["has_categories"] else "—"
        ktru = "+" if sh["has_ktru"] else "—"
        lines.append(
            f"{inv['id']:>7} | {inv['topic']:<35} | {inv['total_count']:>5} | "
            f"{or_s:<45} | {dyn_s:<22} | {bp:>7} | {cats:^4} | {ktru:^4}"
        )
    (out_root / "_inventory.txt").write_text("\n".join(lines), encoding="utf-8")
    print()
    print("\n".join(lines[:4]))
    print(f"\nSaved → {out_root}")


if __name__ == "__main__":
    main()
