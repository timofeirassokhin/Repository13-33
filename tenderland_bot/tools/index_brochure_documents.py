"""Index Markdown brochures into `brochure_documents` table for FTS.

Reads MD files from a local dir + a brand-slug, upserts each into
brochure_documents with auto-generated tsvector (fts column).

After running for all brands, query examples:

  -- Find docs containing tender requirement keywords
  SELECT title, ts_rank(fts, q) AS rank
  FROM brochure_documents, websearch_to_tsquery('english', 'peltier incubator humidity') q
  WHERE fts @@ q
  ORDER BY rank DESC LIMIT 10;

  -- Find PRODUCTS where brochure mentions specific spec
  SELECT p.vendor_code, p.display_name, bd.title, ts_rank(bd.fts, q) AS r
  FROM product p
  JOIN brochure_documents bd ON bd.minio_path = ANY(p.markdown_paths),
       websearch_to_tsquery('english', 'vacuum oven 200°C') q
  WHERE bd.fts @@ q ORDER BY r DESC LIMIT 10;
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from pathlib import Path

import asyncpg

log = logging.getLogger(__name__)

BUCKET = "product-brochures"


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--brand-slug", required=True)
    ap.add_argument("--md-dir", required=True)
    args = ap.parse_args()

    md_dir = Path(args.md_dir)
    md_files = sorted(md_dir.glob("*.md"))
    log.info("Found %d MD files for brand=%s", len(md_files), args.brand)

    conn = await asyncpg.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ.get("PG_PORT", 5432)),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        database=os.environ["PG_DB"],
    )

    stats = {"inserted": 0, "updated": 0, "errors": 0}

    for md in md_files:
        content = md.read_text(encoding="utf-8")
        size = len(content.encode("utf-8"))

        # Extract title and page count from header (set by pdf_to_markdown.py)
        title = md.stem
        title_m = re.search(r"^# (.+)$", content, re.MULTILINE)
        if title_m:
            title = title_m.group(1).strip()
        page_count = 0
        pg_m = re.search(r"_Pages: (\d+)_", content)
        if pg_m:
            page_count = int(pg_m.group(1))

        minio_path = f"{BUCKET}/{args.brand_slug}/markdown/{md.name}"
        # PDF path stem (sanitize same way as map_brand_pdfs.py for matching)
        pdf_name = md.stem + ".pdf"
        pdf_path = f"{BUCKET}/{args.brand_slug}/{pdf_name}"

        try:
            res = await conn.execute(
                """
                INSERT INTO brochure_documents
                    (brand, minio_path, pdf_path, title, content, size_bytes, page_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (minio_path) DO UPDATE
                SET title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    size_bytes = EXCLUDED.size_bytes,
                    page_count = EXCLUDED.page_count,
                    updated_at = now()
                """,
                args.brand, minio_path, pdf_path, title, content, size, page_count,
            )
            if "INSERT 0 1" in res:
                stats["inserted"] += 1
            else:
                stats["updated"] += 1
        except Exception as e:
            log.warning("FAIL %s: %s", md.name, e)
            stats["errors"] += 1

    log.info("DONE: inserted=%d updated=%d errors=%d",
             stats["inserted"], stats["updated"], stats["errors"])
    await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
