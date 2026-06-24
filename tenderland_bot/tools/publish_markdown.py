"""Upload Markdown brochure files to MinIO and link to products.

Mirrors the structure of `datasheet_paths`:
  - Uploads each .md to product-brochures/<brand_slug>/markdown/<name>.md
  - For each product where datasheet_paths contains the corresponding PDF,
    appends the MD path to markdown_paths (new column).

Usage:
  python tools/publish_markdown.py \
      --brand Memmert --brand-slug memmert \
      --md-dir /md --pdf-dir /pdfs
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
from minio import Minio

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
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    md_dir = Path(args.md_dir)
    md_files = sorted(md_dir.glob("*.md"))
    log.info("Found %d MD files in %s", len(md_files), md_dir)

    minio = Minio(
        os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )
    if not minio.bucket_exists(BUCKET):
        minio.make_bucket(BUCKET)

    conn = await asyncpg.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ.get("PG_PORT", 5432)),
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"],
        database=os.environ["PG_DB"],
    )

    # markdown_paths column must already exist (run as postgres user):
    #   ALTER TABLE product ADD COLUMN IF NOT EXISTS markdown_paths TEXT[];

    stats = {"uploaded": 0, "products_updated": 0, "links": 0}

    for md in md_files:
        # PDF path is the same name with .pdf extension (or .pdf.pdf for the
        # one HPPeco file). Try both.
        pdf_stem = md.stem
        # Sanitize for MinIO (matches what map_brand_pdfs did)
        # Original PDF name might have non-ASCII / special chars: brace as-is from disk
        # Reconstruct: pdf_to_markdown applied re.sub(r'[^\w.\-]','_', stem)
        # So MD filename is the SANITIZED stem. The PDF in MinIO is uploaded with
        # the same sanitization. → so we can derive directly.
        pdf_safe_name = re.sub(r"[^\w.\-]", "_", pdf_stem) + ".pdf"

        md_minio_path = f"{args.brand_slug}/markdown/{md.name}"
        md_full = f"{BUCKET}/{md_minio_path}"

        # Possible PDF paths (with both stem.pdf and stem.pdf.pdf weirdness)
        # Original sanitization run on `pdf.name` (not stem), so we look for
        # patterns in datasheet_paths.
        if not args.dry_run:
            minio.fput_object(BUCKET, md_minio_path, str(md),
                              content_type="text/markdown; charset=utf-8")
        stats["uploaded"] += 1

        # Match products where any datasheet_paths entry has the SAME stem
        # (just .pdf instead of .md, ignoring path prefix differences)
        # The cleanest way: search for products where datasheet path basename
        # starts with the same prefix.
        # Use SUFFIX match on datasheet_paths.
        pdf_basename_pattern = f"%{re.escape(pdf_stem)}%.pdf%"

        rows = await conn.fetch(
            """
            SELECT id, datasheet_paths FROM product
            WHERE brand = $1
              AND EXISTS (
                  SELECT 1 FROM unnest(datasheet_paths) AS dp
                  WHERE dp LIKE $2
              )
            """,
            args.brand, pdf_basename_pattern,
        )
        if not rows:
            log.debug("  no product matches for %s", md.name)
            continue

        log.info("  %s → %d products", md.name, len(rows))

        for row in rows:
            if args.dry_run:
                continue
            await conn.execute(
                """
                UPDATE product
                SET markdown_paths = (
                    SELECT array_agg(DISTINCT x)
                    FROM unnest(COALESCE(markdown_paths, '{}') || $2::text[]) AS x
                ),
                    updated_at = now()
                WHERE id = $1
                """,
                row["id"], [md_full],
            )
            stats["links"] += 1
        stats["products_updated"] += len(rows)

    log.info("\n=== STATS ===")
    log.info("MDs uploaded:     %d", stats["uploaded"])
    log.info("Product↔MD links: %d", stats["links"])

    await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
