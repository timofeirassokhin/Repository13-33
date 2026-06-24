"""GluvexLab adapter — парсит sitemap.xml + manufacturer/category страницы.

Phase 1 (это): структура каталога — бренды, категории, статистика sitemap-ов.
Phase 2: детальные карточки товаров → product таблица.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from lxml import etree
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event
from catalog_crawler.core.fetcher import Fetcher
from catalog_crawler.core.storage import put_object
from catalog_crawler.settings import Settings


SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class GluvexLabAdapter:
    """Crawler for gluvexlab.com."""

    BASE_URL = "https://gluvexlab.com"
    SITEMAP_INDEX = f"{BASE_URL}/sitemap.xml"

    def __init__(self, settings: Settings):
        self.settings = settings

    # ------------------------------------------------------------------
    # Phase 1 — структура каталога
    # ------------------------------------------------------------------
    async def crawl_structure(
        self,
        upload_to_minio: bool = True,
        local_path: str | None = None,
    ) -> dict[str, Any]:
        """Парсит sitemap → собирает бренды/категории/статистику."""
        print(f"==> crawl_structure: fetching {self.SITEMAP_INDEX}")
        async with Fetcher() as f:
            # 1. sitemap-index
            index_xml = await f.get(self.SITEMAP_INDEX)
            sitemaps = _parse_sitemap_index(index_xml)
            print(f"    sitemaps in index: {len(sitemaps)}")
            for sm in sitemaps[:5]:
                print(f"      {sm['loc']} (modified {sm['lastmod']})")
            if len(sitemaps) > 5:
                print(f"      ... + {len(sitemaps)-5} more")

            # 2. manufacturers sitemap
            mfr_sm = _find_sitemap(sitemaps, "manufacturers")
            manufacturers: list[dict[str, str]] = []
            if mfr_sm:
                print(f"\n==> parsing manufacturers sitemap: {mfr_sm}")
                mfr_xml = await f.get(mfr_sm)
                mfr_urls = _parse_url_sitemap(mfr_xml)
                print(f"    manufacturer URLs: {len(mfr_urls)}")
                for u in mfr_urls:
                    slug = _slug_from_url(u["loc"], prefix="/brands/")
                    manufacturers.append({
                        "slug": slug,
                        "url": u["loc"],
                        "lastmod": u.get("lastmod", ""),
                    })

            # 3. categories sitemap
            cat_sm = _find_sitemap(sitemaps, "catalog_rubrics")
            categories: list[dict[str, str]] = []
            if cat_sm:
                print(f"\n==> parsing categories sitemap: {cat_sm}")
                cat_xml = await f.get(cat_sm)
                cat_urls = _parse_url_sitemap(cat_xml)
                print(f"    category URLs: {len(cat_urls)}")
                for u in cat_urls:
                    slug = _slug_from_url(u["loc"], prefix="/catalog/")
                    categories.append({
                        "slug": slug,
                        "url": u["loc"],
                        "lastmod": u.get("lastmod", ""),
                    })

            # 4. product sitemaps — счётчик ссылок без скачивания самих
            product_sitemaps = [s for s in sitemaps if "catalog_products" in s["loc"] and "_" in s["loc"].rsplit("/", 1)[-1]]
            print(f"\n==> product sitemaps (sharded): {len(product_sitemaps)}")
            for ps in product_sitemaps[:3]:
                print(f"      {ps['loc']}")
            if len(product_sitemaps) > 3:
                print(f"      ... + {len(product_sitemaps)-3} more")

        # 5. enrich manufacturer pages — получим количество товаров
        # (это дополнительная информация, по одной странице на бренд)
        print(f"\n==> enriching {len(manufacturers)} manufacturer pages for product counts")
        async with Fetcher() as f:
            for m in manufacturers:
                try:
                    html = await f.get(m["url"])
                    count = _extract_product_count(html)
                    m["product_count"] = count
                    print(f"    {m['slug']:50s}  {count} items")
                except Exception as e:
                    m["product_count"] = None
                    m["fetch_error"] = str(e)[:200]
                    print(f"    {m['slug']:50s}  ERROR: {e}")

        # 6. build dump
        dump = {
            "source": "gluvexlab.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "sitemap_index": self.SITEMAP_INDEX,
            "sitemaps_total": len(sitemaps),
            "manufacturers": manufacturers,
            "manufacturers_count": len(manufacturers),
            "categories": categories,
            "categories_count": len(categories),
            "product_sitemaps_count": len(product_sitemaps),
            "product_sitemap_urls": [s["loc"] for s in product_sitemaps],
        }

        # 7. save / upload
        body = json.dumps(dump, indent=2, ensure_ascii=False).encode("utf-8")

        if local_path:
            with open(local_path, "wb") as fp:
                fp.write(body)
            print(f"\n==> local dump: {local_path}")

        if upload_to_minio:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            key = f"gluvexlab/structure/{ts}.json"
            location = put_object(
                self.settings.minio_raw_bucket,
                key,
                body,
                content_type="application/json; charset=utf-8",
            )
            print(f"\n==> uploaded to MinIO: {location}")

            await audit_event(
                action="crawl_structure_complete",
                payload={
                    "source": "gluvexlab",
                    "manufacturers": len(manufacturers),
                    "categories": len(categories),
                    "product_sitemaps": len(product_sitemaps),
                    "minio_object": location,
                },
            )

        # 8. summary
        print("\n==> SUMMARY")
        print(f"    manufacturers: {len(manufacturers)}")
        print(f"    categories:    {len(categories)}")
        print(f"    sharded sitemaps with products: {len(product_sitemaps)}")
        total_items = sum(m.get("product_count") or 0 for m in manufacturers)
        print(f"    total items (sum by brands): {total_items}")

        return dump


# ============================================================
# helpers
# ============================================================
def _parse_sitemap_index(xml_text: str) -> list[dict[str, str]]:
    root = etree.fromstring(xml_text.encode("utf-8"))
    out = []
    for sm in root.findall("sm:sitemap", SITEMAP_NS):
        loc = sm.findtext("sm:loc", "", SITEMAP_NS)
        lastmod = sm.findtext("sm:lastmod", "", SITEMAP_NS)
        out.append({"loc": loc, "lastmod": lastmod})
    return out


def _parse_url_sitemap(xml_text: str) -> list[dict[str, str]]:
    root = etree.fromstring(xml_text.encode("utf-8"))
    out = []
    for u in root.findall("sm:url", SITEMAP_NS):
        loc = u.findtext("sm:loc", "", SITEMAP_NS)
        lastmod = u.findtext("sm:lastmod", "", SITEMAP_NS)
        out.append({"loc": loc, "lastmod": lastmod})
    return out


def _find_sitemap(sitemaps: list[dict[str, str]], substring: str) -> str | None:
    for sm in sitemaps:
        if substring in sm["loc"]:
            return sm["loc"]
    return None


def _slug_from_url(url: str, prefix: str = "") -> str:
    path = urlparse(url).path
    if prefix and path.startswith(prefix):
        path = path[len(prefix):]
    return path.strip("/")


# регулярка для подхвата числа товаров на странице бренда — попробуем несколько вариантов
_COUNT_PATTERNS = [
    re.compile(r"Найдено:?\s*<[^>]+>(\d+)<"),
    re.compile(r"товаров[^0-9]{0,10}(\d{1,6})"),
    re.compile(r'data-total[^=]*=\s*["\'](\d+)["\']'),
    re.compile(r"(\d{1,6})\s*товаров"),
]


def _extract_product_count(html: str) -> int | None:
    """Пытается найти счётчик товаров на странице бренда."""
    # selectolax — быстрый, но регулярки часто проще для счётчиков
    for pat in _COUNT_PATTERNS:
        m = pat.search(html)
        if m:
            return int(m.group(1))

    # альтернатива: считаем карточки товаров на первой странице (не точно, но даёт нижнюю оценку)
    tree = HTMLParser(html)
    for selector in (".card.product", ".product-card", ".item.product", "[data-product-id]"):
        cards = tree.css(selector)
        if cards:
            return len(cards)
    return None
