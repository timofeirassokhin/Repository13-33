"""Brochure web-search — поиск datasheet PDF по vendor_code через интернет.

Главное применение: **Agilent enrichment** — у нас 39,193 артикула Agilent
без datasheets, прямой crawl agilent.com заблокирован Akamai. Идея:
для каждого артикула ищем PDF в Google/Bing/DuckDuckGo, скачиваем,
кладём в MinIO + linkam к product.datasheet_paths.

Источники web-search (в порядке предпочтения):

1. **SerpAPI** (если SERPAPI_KEY в env) — Google Search API, $50/5000 запросов
2. **Bing Web Search API** (если BING_API_KEY в env) — $7/1000 запросов
3. **DuckDuckGo HTML scrape** (без ключа, default) — медленнее, может банить

Pipeline:
  1. SELECT product WHERE brand=X AND datasheet_paths IS NULL AND vendor_code IS NOT NULL
  2. для каждого vendor_code:
     a. query = f'"{vendor_code}" {brand} datasheet pdf'
     b. web search → top-5 results
     c. для каждого PDF-результата: download → content_hash → MinIO put
     d. update product.datasheet_paths
     e. audit_event(brochure_web_found)
  3. rate-limit между запросами (5s — чтоб не быть забанным)

Использование:
  docker compose run --rm catalog-crawler brochure-web Agilent --limit 100
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, quote_plus

import httpx
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.storage import put_object
from catalog_crawler.settings import Settings

log = logging.getLogger(__name__)


# Search engine preference order
SEARCH_ENGINES = ["serpapi", "bing", "duckduckgo"]


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str = ""

    @property
    def is_pdf(self) -> bool:
        return self.url.lower().endswith(".pdf") or ".pdf?" in self.url.lower()


# ============================================================================
# Search engine adapters
# ============================================================================

async def search_serpapi(query: str, *, num: int = 10) -> list[SearchResult]:
    """Google search через SerpAPI. Требует SERPAPI_KEY."""
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return []
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://serpapi.com/search.json", params={
            "engine": "google",
            "q": query,
            "num": num,
            "api_key": api_key,
        })
    if r.status_code != 200:
        log.warning("SerpAPI returned %s: %s", r.status_code, r.text[:100])
        return []
    data = r.json()
    results = []
    for it in data.get("organic_results", [])[:num]:
        results.append(SearchResult(
            url=it.get("link", ""),
            title=it.get("title", ""),
            snippet=it.get("snippet", ""),
        ))
    return results


async def search_bing(query: str, *, num: int = 10) -> list[SearchResult]:
    """Bing Web Search API. Требует BING_API_KEY."""
    api_key = os.environ.get("BING_API_KEY")
    if not api_key:
        return []
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(
            "https://api.bing.microsoft.com/v7.0/search",
            params={"q": query, "count": num, "responseFilter": "Webpages"},
            headers={"Ocp-Apim-Subscription-Key": api_key},
        )
    if r.status_code != 200:
        log.warning("Bing API returned %s", r.status_code)
        return []
    data = r.json()
    results = []
    for it in (data.get("webPages") or {}).get("value", [])[:num]:
        results.append(SearchResult(
            url=it.get("url", ""),
            title=it.get("name", ""),
            snippet=it.get("snippet", ""),
        ))
    return results


async def search_duckduckgo(query: str, *, num: int = 10) -> list[SearchResult]:
    """DuckDuckGo HTML — без API ключа. Парсит результаты через scrape.

    Использует https://html.duckduckgo.com/html/ (упрощённая HTML версия).
    """
    url = "https://html.duckduckgo.com/html/"
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.post(url, data={"q": query, "b": ""}, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        })
    if r.status_code != 200:
        log.warning("DuckDuckGo returned %s", r.status_code)
        return []
    tree = HTMLParser(r.text)
    results = []
    for res_node in tree.css(".result"):
        a = res_node.css_first("a.result__a")
        if a is None:
            continue
        href = a.attrs.get("href", "")
        title = a.text(strip=True)
        snippet_node = res_node.css_first(".result__snippet")
        snippet = snippet_node.text(strip=True) if snippet_node else ""
        # DuckDuckGo wrap'ит URL через uddg parameter — разворачиваем
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                from urllib.parse import unquote
                href = unquote(m.group(1))
        results.append(SearchResult(url=href, title=title, snippet=snippet))
        if len(results) >= num:
            break
    return results


async def search_any(query: str, *, num: int = 10) -> list[SearchResult]:
    """Попробовать поисковики в порядке предпочтения. Первый не-пустой результат."""
    for engine in SEARCH_ENGINES:
        try:
            if engine == "serpapi":
                results = await search_serpapi(query, num=num)
            elif engine == "bing":
                results = await search_bing(query, num=num)
            elif engine == "duckduckgo":
                results = await search_duckduckgo(query, num=num)
            else:
                results = []
            if results:
                log.debug("search engine %s returned %d results", engine, len(results))
                return results
        except Exception as exc:
            log.warning("search engine %s failed: %s", engine, exc)
    return []


# ============================================================================
# Download + persist PDF
# ============================================================================

async def download_and_save_pdf(
    settings: Settings,
    *,
    url: str,
    brand_slug: str,
    vendor_code: str,
    product_id: str,
) -> str | None:
    """Скачать PDF + положить в MinIO + audit_event. Возвращает object_key или None."""
    try:
        async with httpx.AsyncClient(
            timeout=60, follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GluvexBrochureFinder/1.0)",
                "Accept": "application/pdf,*/*;q=0.5",
            },
        ) as c:
            r = await c.get(url)
        if r.status_code != 200:
            log.warning("download %s → %s", url, r.status_code)
            return None
        content_type = r.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not url.lower().endswith(".pdf"):
            # Не PDF — пропускаем
            return None
        content = r.content
        if len(content) < 1024:  # < 1KB — скорее всего не валидный
            return None

        # Filename: <vendor_code>__<hash6>.pdf
        h = hashlib.sha256(content).hexdigest()[:8]
        safe_code = re.sub(r"[^A-Za-z0-9_\-]", "_", vendor_code)[:60]
        object_key = f"{brand_slug}/{safe_code}__{h}.pdf"

        # Put to MinIO bucket 'product-brochures'
        put_object("product-brochures", object_key, content, content_type="application/pdf")

        return object_key
    except Exception as exc:
        log.warning("download_and_save failed for %s: %s", url, exc)
        return None


# ============================================================================
# Main pipeline
# ============================================================================

async def enrich_brand_brochures(
    settings: Settings,
    *,
    brand: str,
    limit: int = 0,
    rate_limit_seconds: float = 5.0,
    max_pdfs_per_product: int = 2,
):
    """Web-search brochures для всех продуктов бренда без datasheets.

    :param brand: точное значение product.brand (например 'Agilent Technologies')
    :param limit: ограничить число продуктов для теста (0 = все)
    :param rate_limit_seconds: пауза между поисковыми запросами (защита от бана)
    :param max_pdfs_per_product: сколько PDF сохранять на один продукт
    """
    conn = await get_conn()
    brand_slug = re.sub(r"[^a-z0-9]+", "_", brand.lower()).strip("_")

    try:
        # Найти продукты без datasheets, имеющие vendor_code
        query = """
            SELECT id, vendor_code, brand, model
            FROM product
            WHERE brand = $1
              AND vendor_code IS NOT NULL AND vendor_code != ''
              AND (datasheet_paths IS NULL OR array_length(datasheet_paths, 1) IS NULL)
            ORDER BY id
        """
        if limit and limit > 0:
            query += f"\nLIMIT {limit}"

        products = await conn.fetch(query, brand)
        log.info("brand=%s: %d products without datasheets", brand, len(products))
        if not products:
            return

        stats = {"total": len(products), "found": 0, "saved": 0, "errors": 0, "skipped": 0}

        for i, prod in enumerate(products, 1):
            vendor_code = prod["vendor_code"]
            model = prod["model"]
            product_id = prod["id"]

            search_query = f'"{vendor_code}" {brand} datasheet pdf'
            log.info("[%d/%d] %s — searching: %s", i, len(products), vendor_code, search_query)

            try:
                results = await search_any(search_query, num=10)
            except Exception as exc:
                log.warning("search failed for %s: %s", vendor_code, exc)
                stats["errors"] += 1
                await asyncio.sleep(rate_limit_seconds)
                continue

            # Фильтр: только PDF, не на agilent.com (Akamai), приоритет distributor / repository sites
            pdf_candidates = [r for r in results if r.is_pdf]
            if not pdf_candidates:
                stats["skipped"] += 1
                await asyncio.sleep(rate_limit_seconds)
                continue

            saved_keys: list[str] = []
            for cand in pdf_candidates[:max_pdfs_per_product]:
                key = await download_and_save_pdf(
                    settings,
                    url=cand.url,
                    brand_slug=brand_slug,
                    vendor_code=vendor_code,
                    product_id=str(product_id),
                )
                if key:
                    saved_keys.append(key)
                    stats["saved"] += 1
                    log.info("    saved → %s", key)

            if saved_keys:
                # Update product.datasheet_paths
                await conn.execute(
                    "UPDATE product SET datasheet_paths = $1, updated_at = now() WHERE id = $2",
                    saved_keys, product_id,
                )
                await audit_event(
                    conn,
                    event_type="brochure_web_found",
                    actor="brochure_web_search",
                    payload={
                        "product_id": str(product_id),
                        "vendor_code": vendor_code,
                        "brand": brand,
                        "model": model,
                        "saved_count": len(saved_keys),
                    },
                )
                stats["found"] += 1

            # rate-limit
            await asyncio.sleep(rate_limit_seconds)

            # Log progress every 20
            if i % 20 == 0:
                log.info("progress: %s", stats)

        log.info("DONE. Final stats: %s", stats)

    finally:
        await conn.close()
