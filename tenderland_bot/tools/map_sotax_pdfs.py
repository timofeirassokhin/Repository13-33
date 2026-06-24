"""Upload SOTAX PDFs to MinIO and map to product SKUs by model family.

Strategy:
  1. Загружаем все 89 PDF в MinIO bucket `product-brochures` под путь
     `sotax/<file_id>__<slug>.pdf`
  2. Для каждой брошюры извлекаем `family` из title (AT50, Xtend, JetX, TPW...)
  3. UPDATE product SET datasheet_paths = array_append(...)
     WHERE brand='SOTAX' AND (description ILIKE %family% OR model ILIKE %family%)

Запуск (внутри docker compose run --rm catalog-crawler):
  python tools/map_sotax_pdfs.py --pdf-dir /pdfs --manifest /pdfs/manifest.json
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
BRAND_SLUG = "sotax"

# Family extraction patterns. Order matters — more specific first.
# Maps regex → canonical family token for SQL match.
FAMILY_PATTERNS = [
    (re.compile(r"\bATF Xtend\b", re.IGNORECASE), "ATF Xtend"),
    (re.compile(r"\bATS Xtend\b", re.IGNORECASE), "ATS Xtend"),
    (re.compile(r"\bMP Xtend\b", re.IGNORECASE), "MP Xtend"),
    (re.compile(r"\bXtend\b", re.IGNORECASE), "Xtend"),
    (re.compile(r"\bAT[-_ ]?MD\b", re.IGNORECASE), "AT-MD"),
    (re.compile(r"\bAT[-_ ]?50\b", re.IGNORECASE), "AT50"),
    (re.compile(r"\bJetX\b", re.IGNORECASE), "JetX"),
    (re.compile(r"\bDT[-_ ]?50\b", re.IGNORECASE), "DT50"),
    (re.compile(r"\bDT[-_ ]?2\b", re.IGNORECASE), "DT2"),
    (re.compile(r"\bFT[-_ ]?2\b", re.IGNORECASE), "FT2"),
    (re.compile(r"\bMT[-_ ]?50\b", re.IGNORECASE), "MT50"),
    (re.compile(r"\bST[-_ ]?50\b", re.IGNORECASE), "ST50"),
    (re.compile(r"\bWT[-_ ]?50\b", re.IGNORECASE), "WT50"),
    (re.compile(r"\bPF[-_ ]?1\b", re.IGNORECASE), "PF1"),
    (re.compile(r"\bTD[-_ ]?1\b", re.IGNORECASE), "TD1"),
    (re.compile(r"\bTM[-_ ]?200\b", re.IGNORECASE), "TM200"),
    (re.compile(r"\bTPW\b", re.IGNORECASE), "TPW"),
    (re.compile(r"\bAPW\b", re.IGNORECASE), "APW"),
    (re.compile(r"\bASP\s*C\b", re.IGNORECASE), "ASP C"),
    (re.compile(r"\bq[-_ ]?doc\b", re.IGNORECASE), "q-doc"),
    (re.compile(r"\bSDT[-_ ]?L\b", re.IGNORECASE), "SDT-L"),
    (re.compile(r"\bWinSOTAX\b", re.IGNORECASE), "WinSOTAX"),
    (re.compile(r"\bSOTAX MD\b", re.IGNORECASE), "SOTAX MD"),
    (re.compile(r"\bMDsoft\b", re.IGNORECASE), "MDsoft"),
    (re.compile(r"\bTPWsoft\b", re.IGNORECASE), "TPWsoft"),
    (re.compile(r"\bAPWsoft\b", re.IGNORECASE), "APWsoft"),
    (re.compile(r"\bBioJect\b", re.IGNORECASE), "BioJect"),
    (re.compile(r"\bPhysical Testing\b", re.IGNORECASE), "Physical Testing"),
]


def extract_families(title: str) -> list[str]:
    """Returns all family tokens found in the title (deduped)."""
    found: list[str] = []
    for pat, token in FAMILY_PATTERNS:
        if pat.search(title) and token not in found:
            found.append(token)
    return found


async def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pdf_dir = Path(args.pdf_dir)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    items = manifest["items"]

    # MinIO client (env vars from catalog-crawler container)
    import os
    minio = Minio(
        os.environ["MINIO_ENDPOINT"],
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=os.environ.get("MINIO_SECURE", "false").lower() == "true",
    )
    if not minio.bucket_exists(BUCKET):
        minio.make_bucket(BUCKET)
        log.info("created bucket %s", BUCKET)

    # DB connection
    pg_host = os.environ["PG_HOST"]
    pg_port = int(os.environ.get("PG_PORT", 5432))
    pg_user = os.environ["PG_USER"]
    pg_pass = os.environ["PG_PASSWORD"]
    pg_db = os.environ["PG_DB"]
    conn = await asyncpg.connect(
        host=pg_host, port=pg_port, user=pg_user,
        password=pg_pass, database=pg_db,
    )

    stats = {"uploaded": 0, "skipped_no_pdf": 0,
             "mapped_total": 0, "products_updated": set()}
    pdf_to_path: dict[str, str] = {}

    # Step 1: upload all PDFs to MinIO
    log.info("=== Step 1: upload PDFs to MinIO ===")
    for it in items:
        fid = it["file_id"]
        title = it["title"]
        # Find local PDF
        matches = list(pdf_dir.glob(f"f{fid}__*.pdf"))
        if not matches:
            stats["skipped_no_pdf"] += 1
            log.warning("no local PDF for f%s | %s", fid, title)
            continue
        local = matches[0]
        minio_path = f"{BRAND_SLUG}/{local.name}"
        if args.dry_run:
            log.info("[dry] would upload %s → %s/%s", local.name, BUCKET, minio_path)
        else:
            minio.fput_object(BUCKET, minio_path, str(local),
                              content_type="application/pdf")
        full_path = f"{BUCKET}/{minio_path}"
        pdf_to_path[fid] = full_path
        stats["uploaded"] += 1

    log.info("uploaded %d PDFs to MinIO", stats["uploaded"])

    # Step 2: for each PDF extract family + UPDATE matching products
    log.info("=== Step 2: map PDFs to product SKUs by family ===")
    no_family: list[dict] = []
    for it in items:
        fid = it["file_id"]
        title = it["title"]
        if fid not in pdf_to_path:
            continue
        families = extract_families(title)
        if not families:
            no_family.append(it)
            continue

        pdf_path = pdf_to_path[fid]
        for family in families:
            # Match products by family token in description or model
            # Build LIKE pattern with case-insensitive
            pattern = f"%{family}%"
            rows = await conn.fetch(
                """
                SELECT id, vendor_code, description FROM product
                WHERE brand = 'SOTAX'
                  AND (description ILIKE $1 OR model ILIKE $1 OR display_name ILIKE $1)
                """,
                pattern,
            )
            if not rows:
                continue

            for row in rows:
                pid = row["id"]
                if args.dry_run:
                    continue
                # array_append, but avoid dupes — use array_distinct via subquery
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
                    pid,
                    [pdf_path],
                )
                stats["mapped_total"] += 1
                stats["products_updated"].add(str(pid))

            log.info("  f%s [%s] → family=%r matched %d SKUs",
                     fid, title[:50], family, len(rows))

    log.info("\n=== STATS ===")
    log.info("PDFs uploaded:     %d", stats["uploaded"])
    log.info("PDFs without family match: %d", len(no_family))
    for it in no_family:
        log.info("  no-family: f%s | %s", it["file_id"], it["title"])
    log.info("Total SKU↔PDF links: %d", stats["mapped_total"])
    log.info("Unique products updated: %d", len(stats["products_updated"]))

    await conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
