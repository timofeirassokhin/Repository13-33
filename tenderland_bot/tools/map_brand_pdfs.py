"""Generic brand-PDF mapper.

Takes a folder of PDFs + brand + family_patterns JSON file (or inline),
uploads PDFs to MinIO, then maps to product SKUs via family-regex ILIKE.

Usage (CAMAG example):
  python tools/map_brand_pdfs.py \
      --brand CAMAG --brand-slug camag --pdf-dir /pdfs \
      --families '{"HPTLC PRO":"\\bHPTLC[ -]?PRO\\b","Linomat":"\\bLinomat\\b",...}'

Or inline mode auto-detects family from filename (smart slug).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

import asyncpg
from minio import Minio

log = logging.getLogger(__name__)

BUCKET = "product-brochures"


def family_from_filename(path: Path) -> list[str]:
    """Heuristic: extract model/family tokens from filename."""
    name = path.stem
    # Remove common prefixes/suffixes
    name = re.sub(r"^(CAM|CAMAG|Brochure|Flyer|LQ|PB)[_®]?[-_]", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[®©™]", "", name)
    name = re.sub(r"_(20\d{2}|EN|web|v\d+|A4|Broschure|Brochure)([_-]|$)", "_", name, flags=re.IGNORECASE)
    name = re.sub(r"[_-]+", " ", name).strip()
    # Take first meaningful tokens
    return [name[:50]]


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--brand-slug", required=True)
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--families", default="",
                    help='JSON string {"family_token": "regex_pattern"}')
    ap.add_argument("--families-file", default="",
                    help='JSON file with family→regex mapping')
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # Load family patterns. Each entry may be:
    #   "Family": "regex"                  — same regex for filename + product DB search
    #   "Family": {"pdf": "...", "product": "..."}  — separate regexes
    # The product regex is converted to PostgreSQL ~* (case-insensitive POSIX).
    family_pdf_patterns: dict[str, re.Pattern[str]] = {}
    family_product_regexes: dict[str, str] = {}

    def _load(cfg: dict):
        for tok, val in cfg.items():
            if isinstance(val, dict):
                pdf_pat = val.get("pdf") or val.get("filename") or tok
                prod_pat = val.get("product") or val.get("description") or pdf_pat
            else:
                pdf_pat = val
                prod_pat = val
            family_pdf_patterns[tok] = re.compile(pdf_pat, re.IGNORECASE)
            family_product_regexes[tok] = prod_pat

    if args.families_file:
        _load(json.loads(Path(args.families_file).read_text(encoding="utf-8")))
    if args.families:
        _load(json.loads(args.families))

    pdf_dir = Path(args.pdf_dir)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    log.info("Found %d PDFs in %s", len(pdfs), pdf_dir)

    # MinIO + DB
    import os
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

    stats = {"uploaded": 0, "no_family": 0,
             "links": 0, "products_updated": set()}

    for pdf in pdfs:
        title = pdf.stem
        # Determine families
        if family_pdf_patterns:
            matched = [tok for tok, pat in family_pdf_patterns.items()
                       if pat.search(title)]
        else:
            matched = family_from_filename(pdf)

        # Sanitize filename for MinIO (drop unicode special chars)
        safe_name = re.sub(r"[^\w.\-]", "_", pdf.name)
        minio_path = f"{args.brand_slug}/{safe_name}"
        full_path = f"{BUCKET}/{minio_path}"

        if not args.dry_run:
            minio.fput_object(BUCKET, minio_path, str(pdf),
                              content_type="application/pdf")
        stats["uploaded"] += 1

        if not matched:
            stats["no_family"] += 1
            log.warning("  %s → no family match", pdf.name)
            continue

        log.info("  %s → families=%s", pdf.name, matched)

        for family in matched:
            # Use product regex (POSIX ~*) instead of literal ILIKE
            prod_regex = family_product_regexes.get(family, family)
            rows = await conn.fetch(
                """
                SELECT id FROM product
                WHERE brand = $1
                  AND (description ~* $2 OR model ~* $2 OR display_name ~* $2)
                """,
                args.brand, prod_regex,
            )
            if not rows:
                log.info("    family=%r → 0 SKUs matched", family)
                continue
            log.info("    family=%r → %d SKUs", family, len(rows))

            for row in rows:
                if args.dry_run:
                    continue
                await conn.execute(
                    """
                    UPDATE product
                    SET datasheet_paths = (
                        SELECT array_agg(DISTINCT x)
                        FROM unnest(COALESCE(datasheet_paths, '{}') || $2::text[]) AS x
                    ),
                        updated_at = now()
                    WHERE id = $1
                    """,
                    row["id"], [full_path],
                )
                stats["links"] += 1
                stats["products_updated"].add(str(row["id"]))

    log.info("\n=== STATS ===")
    log.info("PDFs uploaded:        %d", stats["uploaded"])
    log.info("PDFs without family:  %d", stats["no_family"])
    log.info("SKU↔PDF links:        %d", stats["links"])
    log.info("Unique products:      %d", len(stats["products_updated"]))

    await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
