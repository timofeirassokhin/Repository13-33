"""Brochure-finder — отдельный pipeline для скачивания PDF datasheet'ов.

Работает по схеме:
  1. Адаптер знает download-center URL вендора (/service/downloads/, /library/, etc.)
  2. Парсит страницу → собирает все PDF links
  3. Скачивает каждый PDF
  4. Кладёт в MinIO product-brochures/<brand_slug>/
  5. Пытается матчить к существующим product записям через
     model name / vendor_code / keyword extraction из filename

Запуск: docker compose run --rm catalog-crawler brochures memmert
"""
from __future__ import annotations

import asyncio
import hashlib
import re
from urllib.parse import urljoin, urlparse

import asyncpg
import httpx
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.fetcher import Fetcher
from catalog_crawler.core.storage import put_object
from catalog_crawler.settings import Settings


# brand_slug → (downloads_url, brand_name, model_regex_for_match)
DOWNLOAD_CENTERS: dict[str, dict] = {
    "memmert": {
        "url": "https://www.memmert.com/en/downloads/",
        "brand_name": "Memmert",
        # модели Memmert: UN30, UF55plus, ICO150, ICOmed, ICP260, HCP260, HPP110, SF55plus, SFP800, SR1000, TTC100 ...
        "model_pattern": r"\b([A-Z]{2,5}\d{2,4}[a-zA-Z]*)\b",
    },
}


async def run_brochures(settings: Settings, brand_slug: str, limit: int = 0):
    if brand_slug not in DOWNLOAD_CENTERS:
        print(f"unknown brand: {brand_slug}, available: {list(DOWNLOAD_CENTERS.keys())}")
        return

    cfg = DOWNLOAD_CENTERS[brand_slug]
    print(f"==> brochure_finder: {cfg['brand_name']} ({brand_slug})")
    print(f"    downloads URL: {cfg['url']}")

    async with Fetcher(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
    ) as fetcher:
        html = await fetcher.get(cfg["url"])
        tree = HTMLParser(html)

        # все <a href> с .pdf
        pdf_links: list[dict] = []
        for a in tree.css("a[href]"):
            href = a.attrs.get("href", "")
            if not href:
                continue
            full = urljoin(cfg["url"], href).split("#")[0]
            low = full.lower()
            if ".pdf" not in low:
                continue
            link_text = a.text(strip=True) or ""
            pdf_links.append({
                "url": full,
                "link_text": link_text,
            })

        # дедуп по URL
        seen = set()
        uniq = []
        for p in pdf_links:
            if p["url"] not in seen:
                seen.add(p["url"])
                uniq.append(p)
        pdf_links = uniq

        print(f"    PDF links found: {len(pdf_links)}")
        if limit and limit > 0:
            pdf_links = pdf_links[:limit]
            print(f"    limited to: {len(pdf_links)}")

        # скачиваем + матчим
        model_re = re.compile(cfg["model_pattern"])
        conn: asyncpg.Connection = await get_conn()
        stats = {"total": len(pdf_links), "saved": 0, "matched": 0, "errors": 0, "skipped_dup": 0}

        try:
            for i, item in enumerate(pdf_links, 1):
                url = item["url"]
                link_text = item["link_text"]
                try:
                    async with httpx.AsyncClient(timeout=60, follow_redirects=True,
                                                  headers={"User-Agent": "Mozilla/5.0"}) as c:
                        r = await c.get(url)
                        if r.status_code != 200:
                            stats["errors"] += 1
                            continue
                        content = r.content
                        # верификация что это PDF
                        if not content[:4].startswith(b"%PDF"):
                            stats["errors"] += 1
                            continue

                    content_hash = hashlib.sha256(content).hexdigest()[:16]
                    # filename из URL
                    filename = url.rsplit("/", 1)[-1].split("?")[0]
                    safe = re.sub(r"[^a-zA-Z0-9._\-]", "_", filename)[:120]
                    key = f"{brand_slug}/{content_hash}_{safe}"
                    location = put_object(
                        settings.minio_brochures_bucket,
                        key, content,
                        content_type="application/pdf",
                    )
                    stats["saved"] += 1

                    # пытаемся матчить к моделям в БД по URL + link_text
                    haystack = f"{url} {link_text}"
                    models_in_text = model_re.findall(haystack)
                    matched_ids = []
                    for model_code in models_in_text[:5]:
                        # ищем продукт в БД у которого model или vendor_code содержит этот код
                        rows = await conn.fetch("""
                            SELECT id, model FROM product
                            WHERE brand = $1
                              AND (model ILIKE '%' || $2 || '%'
                                   OR vendor_code = $2
                                   OR $2 = ANY(synonyms))
                            LIMIT 5
                        """, cfg["brand_name"], model_code)
                        for r2 in rows:
                            matched_ids.append(r2["id"])

                    # обогащаем матченные продукты: добавляем PDF в datasheet_paths
                    matched_ids = list(set(matched_ids))
                    if matched_ids:
                        stats["matched"] += 1
                        await conn.execute("""
                            UPDATE product SET
                              datasheet_paths = (
                                SELECT array_agg(DISTINCT p)
                                FROM unnest(coalesce(datasheet_paths, ARRAY[]::text[]) || ARRAY[$1]::text[]) AS p
                              ),
                              updated_at = now()
                            WHERE id = ANY($2::uuid[])
                        """, location, matched_ids)

                    if i <= 5 or i % 50 == 0 or i == len(pdf_links):
                        print(f"  [{i:>4}/{len(pdf_links)}] saved {location} (matched {len(matched_ids)} products)")

                except Exception as e:
                    stats["errors"] += 1
                    print(f"  [{i:>4}] ERROR {url}: {e}")

        finally:
            await conn.close()

        await audit_event(
            action=f"brochure_finder_complete:{brand_slug}",
            payload=stats,
        )
        print(f"\n==> SUMMARY {brand_slug}")
        for k, v in stats.items():
            print(f"    {k}: {v}")
