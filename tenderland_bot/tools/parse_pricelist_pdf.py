"""Generic pricelist PDF parser → JSON со списком артикулов.

Обрабатывает Illumina-style price lists (одна таблица на странице) где columns:
  Catalog # | Product Description | List Price (USD) | Customer Price (USD)

И **категорийные подзаголовки** — строки где Description пуст, но первая ячейка
содержит название группы ("AmpliSeq Lib Prep", "Bronze Service Contract", и т.д.).

Использование:
  python tools/parse_pricelist_pdf.py <path-to-pdf> [-o output.json]

Output: JSON-список словарей:
  {
    "catalog_number": "20019101",
    "description": "AmpliSeq™ Library PLUS (24 Reactions) for Illumina®",
    "category_section": "AmpliSeq Lib Prep",   # из подзаголовка
    "list_price_usd": 3257.0,
    "customer_price_usd": 2279.9,
    "is_quote_only": False,                     # True если "Request Quote"
    "page": 1,
  }

Бренд (Illumina) и imported_from задаются в importer-команде, не здесь.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# Catalog # — числовая (Illumina: 20019101, 20028446) или alphanumeric (могут быть варианты)
CATALOG_RE = re.compile(r"^\d{6,12}$|^[A-Z]{1,4}-?\d{4,12}[A-Z0-9-]*$", re.IGNORECASE)

PRICE_RE = re.compile(r"^[\d,]+\.\d{2}$")
QUOTE_RE = re.compile(r"^request\s*quote$", re.IGNORECASE)


@dataclass
class PriceItem:
    catalog_number: str
    description: str
    category_section: str = ""
    list_price_usd: float | None = None
    customer_price_usd: float | None = None
    is_quote_only: bool = False
    page: int = 0


def _parse_price(text: str) -> float | None:
    if not text:
        return None
    t = text.strip()
    if PRICE_RE.match(t):
        return float(t.replace(",", ""))
    return None


def _normalize_text(text: str) -> str:
    """Свести многострочный текст в одну строку, очистить."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def parse_pricelist(pdf_path: Path) -> list[PriceItem]:
    """Прогон по всем страницам PDF — извлечение PriceItem."""
    try:
        import pdfplumber
    except ImportError as exc:
        print(f"ERROR: pdfplumber required: pip install pdfplumber", file=sys.stderr)
        raise

    items: list[PriceItem] = []
    current_section = ""

    with pdfplumber.open(str(pdf_path)) as pdf:
        for page_idx, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for tbl in tables:
                # Первая строка — обычно header (Catalog # / Product Description / ...)
                # Skip rows where все cells пусты.
                for row in tbl:
                    if not row or all(not (c or "").strip() for c in row):
                        continue
                    # Normalize cells
                    cells = [_normalize_text(c or "") for c in row]
                    # Skip header rows
                    if cells[0].lower() in ("catalog #", "catalog#", "catalog number"):
                        continue
                    if len(cells) < 2:
                        continue

                    cat_raw = cells[0]
                    desc = cells[1] if len(cells) > 1 else ""
                    p1 = cells[2] if len(cells) > 2 else ""
                    p2 = cells[3] if len(cells) > 3 else ""

                    # Category section row — first cell non-empty, остальные пустые
                    if cat_raw and not desc and not p1 and not p2:
                        # Может быть category header или продолжение текста
                        # Эвристика: длина 3-60, не похоже на catalog number
                        if 3 <= len(cat_raw) <= 80 and not CATALOG_RE.match(cat_raw):
                            current_section = cat_raw
                            continue

                    # Catalog number row
                    if CATALOG_RE.match(cat_raw):
                        # Стандартные case'ы price'а: "3,257.00" / "Request Quote" / ""
                        list_price = _parse_price(p1)
                        cust_price = _parse_price(p2)
                        is_quote = QUOTE_RE.match(p1) is not None
                        item = PriceItem(
                            catalog_number=cat_raw,
                            description=desc,
                            category_section=current_section,
                            list_price_usd=list_price,
                            customer_price_usd=cust_price,
                            is_quote_only=is_quote,
                            page=page_idx,
                        )
                        items.append(item)

    return items


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="parse_pricelist_pdf")
    parser.add_argument("pdf_path", help="Path to pricelist PDF")
    parser.add_argument("-o", "--output", help="Output JSON path (default: <pdf>.json)")
    parser.add_argument("--brand", default="Illumina",
                        help="Brand to assign (default: Illumina)")
    args = parser.parse_args(argv)

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"ERROR: file not found: {pdf_path}", file=sys.stderr)
        return 1

    print(f"Parsing {pdf_path.name}...")
    items = parse_pricelist(pdf_path)
    print(f"  found {len(items)} catalog items")

    # Statistics
    from collections import Counter
    sections = Counter(it.category_section for it in items)
    print(f"  categories ({len(sections)}):")
    for sec, cnt in sections.most_common(20):
        print(f"    {cnt:>5}  {sec[:60]}")

    has_list_price = sum(1 for it in items if it.list_price_usd)
    has_cust_price = sum(1 for it in items if it.customer_price_usd)
    is_quote = sum(1 for it in items if it.is_quote_only)
    print(f"\n  with list_price:  {has_list_price}")
    print(f"  with cust_price:  {has_cust_price}")
    print(f"  request quote:    {is_quote}")

    output = Path(args.output) if args.output else pdf_path.with_suffix(".json")
    data = {
        "source_pdf": str(pdf_path),
        "brand": args.brand,
        "items_count": len(items),
        "items": [asdict(it) for it in items],
    }
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved → {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
