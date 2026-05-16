"""Custom parser for TopAir combined CSV (multi-sheet matrix).

TopAir prices пришли в "combined" CSV с колонкой Sheet [0] и продуктами по
размерам. Структура нестандартна — описание не в отдельной колонке, а в
названии секции (тип товара).

Колонки:
  [0] Sheet (Fume Hood / Ductless / Biosafety / Cleanbench / ...)
  [1] Part code (FH-090, FH-090-PP, BS-1500, и т.д.)
  [2] Size cm
  [3] Size inches
  [4] List price USD
  [5-7] Tier prices
  [11] Цена Продажи usd

Strategy: каждая строка с part code = отдельный продукт.
description = "{Sheet category} {Part Code}  (size {cm} cm / {in} inch)"
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


PART_CODE_RE = re.compile(r"^[A-Z]{2,4}-?\d{2,4}([-A-Z0-9]+)?$")


def parse_topair(csv_path: Path) -> list[dict]:
    with open(csv_path, encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    items: list[dict] = []
    # CSV structure:
    #   [0]=sheet, [1]='', [2]=part_code/section_title, [3]=size_cm, [4]=size_in,
    #   [5]=list_price, [6..9]=tier prices, [10]=Цена Продажи usd
    # Sub-section description (e.g. "Metal Fume Hood with Base Cabinet") is
    # in col [2] of preceding rows where size cols are empty.
    current_subsection = ""
    for i, r in enumerate(rows[1:], start=2):
        if len(r) < 5:
            continue
        sheet = r[0].strip()
        col2 = r[2].strip() if len(r) > 2 else ""
        if sheet == "General Terms" or not col2:
            continue

        # Capture sub-section description: col2 is text and sizes empty
        if not PART_CODE_RE.match(col2):
            # If looks like a description (long text), keep it as current subsection
            if len(col2) > 20:
                current_subsection = col2
            continue

        part = col2
        size_cm = r[3].strip() if len(r) > 3 else ""
        size_in = r[4].strip() if len(r) > 4 else ""
        try:
            list_price = float(r[5]) if len(r) > 5 and r[5].strip() else None
        except ValueError:
            list_price = None
        # Цена Продажи usd at col 10
        sale_price = None
        if len(r) > 10 and r[10] and r[10].strip():
            try:
                sale_price = float(r[10])
            except ValueError:
                pass

        # description
        size_str = ""
        if size_cm:
            size_str = f" ({size_cm} cm"
            if size_in:
                size_str += f" / {size_in} in"
            size_str += ")"
        sub = f" — {current_subsection.strip()}" if current_subsection else ""
        desc = f"TopAir {sheet} {part}{sub}{size_str}".strip()

        items.append({
            "catalog_number": part,
            "description": desc,
            "description_ru": "",
            "category_section": sheet,
            "brand": "TopAir Systems",
            "currency": "USD",
            "price_purchase": list_price,
            "price_sale": sale_price,
            "vat": "",
            "unit": "Штука",
            "manufacturer_country": "Israel",
            "distributor": "Glüvex",
            "supplier_inn": "",
            "ru_number": "",
            "is_quote_only": False,
            "page": i,
        })

    # Dedup by catalog_number
    seen = set()
    dedup = []
    for it in items:
        if it["catalog_number"] in seen:
            continue
        seen.add(it["catalog_number"])
        dedup.append(it)
    return dedup


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()

    items = parse_topair(Path(args.csv_path))
    from collections import Counter
    sheets = Counter(it["category_section"] for it in items)
    print(f"Total items: {len(items)}")
    print(f"Sheets ({len(sheets)}):")
    for s, c in sheets.most_common():
        print(f"  {c:>5}  {s}")
    has_sale = sum(1 for it in items if it["price_sale"])
    has_list = sum(1 for it in items if it["price_purchase"])
    print(f"With list price: {has_list}, with sale price: {has_sale}")

    out = {
        "source_xlsx": str(args.csv_path),
        "brand": "TopAir Systems",
        "items_count": len(items),
        "items": items,
    }
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
