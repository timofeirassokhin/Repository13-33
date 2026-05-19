"""PDF → Markdown converter for product brochures.

Uses pdfplumber to extract:
  - Page-by-page text (preserving order)
  - Tables (specifications, spec tables)
  - Approximate heading detection (font-size based)

Strategy for RAG:
  - Output is split into per-page sections so chunking is straightforward
  - Tables serialized as Markdown pipe tables (easy to LLM-read)
  - Filename prefix stays so we can map MD ↔ PDF ↔ product

Usage (inside catalog-crawler container):
  python tools/pdf_to_markdown.py --pdf-dir /pdfs --out-dir /md
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def _table_to_markdown(rows: list[list[str | None]]) -> str:
    """Format a 2D list as a Markdown pipe table."""
    if not rows:
        return ""
    # Normalize cells
    norm = []
    width = max(len(r) for r in rows)
    for r in rows:
        cells = [(c or "").strip().replace("\n", " ").replace("|", "\\|") for c in r]
        cells += [""] * (width - len(cells))
        norm.append(cells)

    # Use first row as header
    header = norm[0]
    sep = ["---"] * len(header)
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for r in norm[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def pdf_to_markdown(pdf_path: Path) -> str:
    import pdfplumber
    parts: list[str] = []
    parts.append(f"# {pdf_path.stem}\n")
    parts.append(f"_Source: {pdf_path.name}_\n")

    with pdfplumber.open(str(pdf_path)) as pdf:
        n_pages = len(pdf.pages)
        parts.append(f"_Pages: {n_pages}_\n")

        for page_idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            tables = page.extract_tables() or []

            parts.append(f"\n## Page {page_idx}\n")
            if text:
                # Keep text as-is in code block? No — keep readable
                # Collapse single linebreaks within paragraphs (rough heuristic)
                parts.append(text)
                parts.append("")
            for t_idx, tbl in enumerate(tables, start=1):
                if not tbl or all(not any(c for c in row) for row in tbl):
                    continue
                parts.append(f"\n### Table {page_idx}.{t_idx}\n")
                parts.append(_table_to_markdown(tbl))
                parts.append("")

    return "\n".join(parts)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if args.limit:
        pdfs = pdfs[:args.limit]
    log.info("Converting %d PDFs to Markdown", len(pdfs))

    done, failed = 0, 0
    for pdf in pdfs:
        # Sanitize filename for MD
        safe = re.sub(r"[^\w.\-]", "_", pdf.stem)
        md_path = out_dir / f"{safe}.md"
        try:
            md = pdf_to_markdown(pdf)
            md_path.write_text(md, encoding="utf-8")
            log.info("  %s → %s (%d chars)", pdf.name, md_path.name, len(md))
            done += 1
        except Exception as e:
            log.warning("  FAILED %s: %s", pdf.name, e)
            failed += 1

    log.info("DONE: %d converted, %d failed", done, failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
