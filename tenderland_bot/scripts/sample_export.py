# -*- coding: utf-8 -*-
"""Sample N newest tenders from autosearches by id, bypassing list_autosearches()
(которая валит HTTP 500 из-за двух старых фантомов с int tender_status).

Usage:
    PYTHONPATH=src python scripts/sample_export.py 373343 MDX_01_Sequencers 20

    PYTHONPATH=src python scripts/sample_export.py 373343 373417 --limit 30

Args:
    id1 id2 ... — autosearch IDs
    --limit N (default 20)

Output:
    _api_check/sample_<id>.json   — сырой JSON всех полученных тендеров
    _api_check/sample_<id>.md     — компактная таблица для глаз
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from tenderland_bot.api_client import TenderlandClient
from tenderland_bot.config import load_settings
from tenderland_bot.models import TenderRow


def parse_args():
    args = sys.argv[1:]
    limit = 20
    ids = []
    name_hints: dict[int, str] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--limit", "-n"):
            limit = int(args[i + 1])
            i += 2
            continue
        # id или id=name
        if "=" in a:
            id_part, name_part = a.split("=", 1)
            asid = int(id_part)
            name_hints[asid] = name_part
            ids.append(asid)
        else:
            try:
                asid = int(a)
                ids.append(asid)
            except ValueError:
                # name hint without id is ignored
                pass
        i += 1
    return ids, name_hints, limit


def fmt_money(v) -> str:
    if v is None or v == "":
        return "—"
    try:
        n = float(v)
        return f"{n:>15,.0f} ₽".replace(",", " ")
    except Exception:
        return str(v)


def short(s, n=70):
    if not s:
        return ""
    s = str(s).replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def main():
    ids, name_hints, limit = parse_args()
    if not ids:
        print(__doc__)
        sys.exit(2)

    out_root = Path(__file__).resolve().parents[1] / "_api_check"
    out_root.mkdir(parents=True, exist_ok=True)

    s = load_settings()
    with TenderlandClient(api_key=s.api_key, base_url=s.base_url,
                          timeout=s.http_timeout) as c:
        for asid in ids:
            label = name_hints.get(asid, f"autosearch_{asid}")
            print(f"\n=== {label} (id {asid}) — limit {limit} ===")
            task = c.create_export(autosearch_id=asid, limit=limit, batch_size=min(limit, 100))
            print(f"  total_count={task.total_count} export_id={task.id}")

            items = []
            for it in c.iter_export(task.id, min(task.total_count, limit),
                                    batch_size=min(limit, 100)):
                items.append(it)
            print(f"  fetched={len(items)}")

            # сырой JSON
            (out_root / f"sample_{asid}.json").write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

            # md-таблица
            rows = [TenderRow.from_export_item(it) for it in items]
            md = [
                f"# Sample: {label} (id {asid}) — top {len(rows)} newest of {task.total_count}",
                "",
                "| # | regNumber | НМЦК | Заказчик | Регион | Тип | Подача до | Название |",
                "|---|---|---:|---|---|---|---|---|",
            ]
            for i, r in enumerate(rows, 1):
                md.append(
                    f"| {i} | {short(r.reg_number, 20)} | "
                    f"{fmt_money(getattr(r, 'begin_price', None))} | "
                    f"{short(getattr(r, 'customer_name', '') or getattr(r, 'customer_short_name', ''), 35)} | "
                    f"{short(getattr(r, 'region', ''), 20)} | "
                    f"{short(getattr(r, 'type_name', ''), 12)} | "
                    f"{short(str(getattr(r, 'end_date', '') or ''), 10)} | "
                    f"{short(getattr(r, 'name', ''), 80)} |"
                )
            (out_root / f"sample_{asid}.md").write_text("\n".join(md), encoding="utf-8")

        st = c.get_statistic()
        print(f"\nAPI quota: {st.get('dailyQueryCount')}/{st.get('dailyQueryLimit')} req, "
              f"{st.get('dailyDataTransferredCount')}/{st.get('dailyDataTransferredLimit')} units")


if __name__ == "__main__":
    main()
