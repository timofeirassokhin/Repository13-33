"""Brochure web-search — расширенный поиск технических документов по vendor_code и model.

Цель: для каждого артикула в БД найти PDF datasheets / application notes / brochures
через интернет-поиск.

Стратегия (multi-query) — для каждого продукта:
  1. "<vendor_code>" <brand> datasheet pdf          # точный артикул
  2. "<vendor_code>" <brand> application note pdf
  3. "<vendor_code>" <brand> brochure pdf
  4. <brand> <model> datasheet pdf                  # по названию модели
  5. <brand> <model> application note pdf
  6. site:<vendor_site> <vendor_code>               # ограничение на оф. сайт
  7. site:support.<vendor> <vendor_code>            # support-сайт

Каждый PDF классифицируется по типу (datasheet / app_note / brochure / spec_sheet /
technical_note / manual / other) по эвристике из URL + title.

В MinIO сохраняется как:
  product-brochures/<brand_slug>/<vendor_code>__<doc_type>__<hash6>.pdf

В product.datasheet_paths добавляется object_key.
В audit_events пишется поиск-event со списком queries и find/save статистикой.

Поисковые движки (auto-fallback):
  1. SerpAPI (SERPAPI_KEY env, $50/5K)
  2. Bing API (BING_API_KEY env, $7/1K)
  3. DuckDuckGo HTML scrape (no key, медленно)

Сейчас этот модуль — **главная модель** для сбора брошюр. Pattern переиспользуем
для Agilent, MGI, AmoyDx и других — конфиг site_filters + vendor_site_overrides.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, unquote

import httpx
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.storage import put_object
from catalog_crawler.settings import Settings

log = logging.getLogger(__name__)


# Order matters — каждый query пробует engines sequentially.
# DuckDuckGo возвращает HTTP 202 (rate-limit) на серверный IP — пропускаем default.
# Bing HTML работает без API и хорошо терпит серверные IP — основной free engine.
# google_playwright требует PROXY_URL — только когда set.
# Включить DDG: SEARCH_ENGINES_INCLUDE_DDG=1 env (для регионов где DDG не banned).
SEARCH_ENGINES = ["serpapi", "bing", "bing_html", "google_playwright"]
if os.environ.get("SEARCH_ENGINES_INCLUDE_DDG", "").lower() in ("1", "true", "yes"):
    SEARCH_ENGINES.append("duckduckgo")


@dataclass
class SearchResult:
    url: str
    title: str = ""
    snippet: str = ""

    @property
    def is_pdf(self) -> bool:
        u = self.url.lower()
        return u.endswith(".pdf") or ".pdf?" in u or "/pdf/" in u


# ============================================================================
# Per-vendor configuration (site filters + naming)
# ============================================================================

@dataclass
class VendorSearchConfig:
    """Параметры поиска для конкретного бренда."""

    brand: str                              # точное значение product.brand
    brand_slug: str                         # для MinIO путей
    # Оф. сайт(ы) бренда для site:-фильтров. Первый — главный.
    vendor_sites: list[str] = field(default_factory=list)
    # Сайты дистрибьюторов / репозиториев (расширяют покрытие)
    distributor_sites: list[str] = field(default_factory=list)
    # Имя бренда для query (часто отличается от product.brand —
    # например в БД "Salus / Биофьюжн" а для поиска "Salus")
    search_brand_names: list[str] = field(default_factory=list)


VENDOR_CONFIGS: dict[str, VendorSearchConfig] = {
    "Illumina": VendorSearchConfig(
        brand="Illumina",
        brand_slug="illumina",
        vendor_sites=["illumina.com", "support.illumina.com"],
        distributor_sites=["scientigen.com", "thermofisher.com"],
        search_brand_names=["Illumina"],
    ),
    "Agilent Technologies": VendorSearchConfig(
        brand="Agilent Technologies",
        brand_slug="agilent",
        vendor_sites=["agilent.com"],
        distributor_sites=["lacopa.group", "millab.ru", "imc-systems.ru"],
        search_brand_names=["Agilent", "Agilent Technologies"],
    ),
    "MGI Tech": VendorSearchConfig(
        brand="MGI Tech",
        brand_slug="mgi_tech",
        vendor_sites=["mgi-tech.com", "global-mgitech.com"],
        distributor_sites=["shop.helicon.ru"],
        search_brand_names=["MGI", "MGI Tech", "BGI", "DNBSEQ"],
    ),
    "AmoyDx": VendorSearchConfig(
        brand="AmoyDx",
        brand_slug="amoydx",
        vendor_sites=["amoydiagnostics.com"],
        distributor_sites=[],
        search_brand_names=["AmoyDx", "Amoy Diagnostics"],
    ),
    "Pillar Biosciences": VendorSearchConfig(
        brand="Pillar Biosciences",
        brand_slug="pillar",
        vendor_sites=["pillar-biosciences.com"],
        distributor_sites=[],
        search_brand_names=["Pillar Biosciences", "Pillar Bio"],
    ),
    "Burning Rock": VendorSearchConfig(
        brand="Burning Rock",
        brand_slug="burning_rock",
        vendor_sites=["brbiotech.com"],
        distributor_sites=[],
        search_brand_names=["Burning Rock", "Burning Rock Dx"],
    ),
    "Genemind": VendorSearchConfig(
        brand="Genemind",
        brand_slug="genemind",
        vendor_sites=["genemind.com", "en.genemind.com"],
        distributor_sites=["sesana.ru"],
        search_brand_names=["Genemind", "GeneMind"],
    ),
    "Сесана": VendorSearchConfig(
        brand="Сесана",
        brand_slug="sesana",
        vendor_sites=["sesana.ru"],
        distributor_sites=[],
        search_brand_names=["Геноскан", "Сесана", "Sesana"],
    ),
}


def get_vendor_config(brand: str) -> VendorSearchConfig:
    """Returns config for known brand, or sensible defaults for unknown."""
    if brand in VENDOR_CONFIGS:
        return VENDOR_CONFIGS[brand]
    # default config
    slug = re.sub(r"[^a-z0-9]+", "_", brand.lower()).strip("_")
    return VendorSearchConfig(
        brand=brand,
        brand_slug=slug,
        vendor_sites=[],
        distributor_sites=[],
        search_brand_names=[brand],
    )


# ============================================================================
# Query generation
# ============================================================================

@dataclass
class Query:
    text: str
    doc_type_hint: str = "datasheet"     # default
    site_filter: str = ""                 # если query содержит site:X


def build_queries(
    vendor_code: str,
    model: str,
    vendor_cfg: VendorSearchConfig,
    include_distributors: bool = True,
) -> list[Query]:
    """Generate multi-query strategy для одного продукта."""
    queries: list[Query] = []
    # Очищаем model от vendor_code suffix `[20019101]` (мы его добавили в imports)
    clean_model = re.sub(r"\s*\[\w+\]\s*$", "", model or "").strip()
    primary_name = vendor_cfg.search_brand_names[0] if vendor_cfg.search_brand_names else vendor_cfg.brand

    # 1-3: по точному артикулу + тип документа
    for doc_keyword, dt in [
        ("datasheet", "datasheet"),
        ("application note", "application_note"),
        ("brochure", "brochure"),
    ]:
        queries.append(Query(
            text=f'"{vendor_code}" {primary_name} {doc_keyword} filetype:pdf',
            doc_type_hint=dt,
        ))

    # 4-5: по названию модели
    if clean_model and len(clean_model) > 3 and clean_model.upper() not in ("FRU", "SPARE", "USED", "REFURB"):
        for doc_keyword, dt in [
            ("datasheet", "datasheet"),
            ("application note", "application_note"),
        ]:
            queries.append(Query(
                text=f'{primary_name} "{clean_model}" {doc_keyword} filetype:pdf',
                doc_type_hint=dt,
            ))

    # 6-7: site-filter на оф. сайты бренда
    for site in vendor_cfg.vendor_sites[:2]:
        queries.append(Query(
            text=f'site:{site} {vendor_code}',
            doc_type_hint="datasheet",
            site_filter=site,
        ))

    # 8-9: дистрибьюторы (опционально)
    if include_distributors:
        for site in vendor_cfg.distributor_sites[:1]:
            queries.append(Query(
                text=f'site:{site} {vendor_code} {primary_name}',
                doc_type_hint="datasheet",
                site_filter=site,
            ))

    return queries


# ============================================================================
# Document type inference из URL/title
# ============================================================================

DOC_TYPE_KEYWORDS: dict[str, list[str]] = {
    "datasheet": ["datasheet", "data-sheet", "data_sheet", "spec-sheet", "spec_sheet", "specification"],
    "application_note": ["application-note", "application_note", "applicationnote", "app-note", "app_note", "appnote", "applications"],
    "brochure": ["brochure", "product-brochure", "company-brochure", "overview", "product-guide"],
    "technical_note": ["technical-note", "technical_note", "tech-note", "tech_note", "white-paper", "whitepaper"],
    "manual": ["manual", "user-guide", "user_guide", "instructions", "handbook"],
    "compliance": ["msds", "sds", "safety-data", "certificate-of-analysis", "coa", "ce-mark", "iso"],
}


def infer_doc_type(url: str, title: str, query_hint: str) -> str:
    """Угадать тип документа из URL/title. Fallback на query hint."""
    text = f"{url} {title}".lower()
    for dt, keywords in DOC_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return dt
    return query_hint or "datasheet"


# ============================================================================
# Search engine adapters (DuckDuckGo / Bing / SerpAPI)
# ============================================================================

async def search_serpapi(query: str, *, num: int = 10) -> list[SearchResult]:
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        return []
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get("https://serpapi.com/search.json", params={
            "engine": "google", "q": query, "num": num, "api_key": api_key,
        })
    if r.status_code != 200:
        log.warning("SerpAPI [%s]: %s", r.status_code, r.text[:80])
        return []
    data = r.json()
    return [
        SearchResult(url=it.get("link",""), title=it.get("title",""), snippet=it.get("snippet",""))
        for it in (data.get("organic_results") or [])[:num]
    ]


async def search_bing(query: str, *, num: int = 10) -> list[SearchResult]:
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
        return []
    data = r.json()
    return [
        SearchResult(url=it.get("url",""), title=it.get("name",""), snippet=it.get("snippet",""))
        for it in (data.get("webPages") or {}).get("value", [])[:num]
    ]


async def search_duckduckgo(query: str, *, num: int = 10) -> list[SearchResult]:
    """DuckDuckGo HTML scrape — без API ключа.

    NB: DDG активно банит серверные IP. Если 403 — переключаемся на bing_html.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query, "b": ""},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36",
                "Accept": "text/html",
            },
        )
    if r.status_code != 200:
        return []
    tree = HTMLParser(r.text)
    results = []
    for res in tree.css(".result"):
        a = res.css_first("a.result__a")
        if a is None:
            continue
        href = a.attrs.get("href", "")
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                href = unquote(m.group(1))
        snippet_node = res.css_first(".result__snippet")
        results.append(SearchResult(
            url=href, title=a.text(strip=True),
            snippet=snippet_node.text(strip=True) if snippet_node else "",
        ))
        if len(results) >= num:
            break
    return results


async def search_bing_html(query: str, *, num: int = 10) -> list[SearchResult]:
    """Bing HTML scrape — без API ключа.

    Bing намного terpимее серверных IP чем DuckDuckGo. Хороший first-choice
    free engine. Парсит результаты из `<li class="b_algo">` блоков.
    """
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(
            "https://www.bing.com/search",
            params={"q": query, "count": num, "form": "QBLH"},
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/130.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
    if r.status_code != 200:
        log.warning("Bing HTML returned %s", r.status_code)
        return []
    tree = HTMLParser(r.text)
    results: list[SearchResult] = []
    # Bing organic results: <li class="b_algo">
    for node in tree.css("li.b_algo"):
        # title link
        h2_a = node.css_first("h2 a")
        if h2_a is None:
            continue
        href = h2_a.attrs.get("href", "")
        title = h2_a.text(strip=True)
        # snippet — <div class="b_caption"><p>
        snippet_node = node.css_first(".b_caption p")
        results.append(SearchResult(
            url=href, title=title,
            snippet=snippet_node.text(strip=True) if snippet_node else "",
        ))
        if len(results) >= num:
            break
    return results


async def search_google_playwright(query: str, *, num: int = 10) -> list[SearchResult]:
    """Google search через PlaywrightFetcher + IPRoyal residential proxy.

    Использует наш существующий headless Chromium со stealth. proxy подмешивает
    residential IP — выглядит как обычный browser у обычного юзера.
    Требует PROXY_URL env.
    """
    if not os.environ.get("PROXY_URL"):
        return []
    try:
        from catalog_crawler.core.playwright_fetcher import PlaywrightFetcher
    except ImportError:
        return []

    url = f"https://www.google.com/search?q={httpx.QueryParams({'q': query})['q']}&num={num}"
    try:
        async with PlaywrightFetcher(
            rate_limit_seconds=1.0,
            block_assets=True,
            wait_until="domcontentloaded",
        ) as f:
            html = await f.get(url)
    except Exception as exc:
        log.warning("Google playwright failed: %s", exc)
        return []

    tree = HTMLParser(html)
    results: list[SearchResult] = []
    # Google organic results: <div class="yuRUbf"> contains <a href> with title h3
    # CSS structure changes; try multiple selectors.
    for node in tree.css("div.yuRUbf a, div.tF2Cxc a, div.g a"):
        href = node.attrs.get("href", "")
        if not href or not href.startswith("http"):
            continue
        # Skip Google's own URLs (calculator, etc.)
        if "google.com" in href.lower():
            continue
        h3 = node.css_first("h3")
        title = h3.text(strip=True) if h3 else node.text(strip=True)[:120]
        if not title or len(title) < 5:
            continue
        results.append(SearchResult(url=href, title=title))
        if len(results) >= num:
            break
    return results


async def search_any(query: str, *, num: int = 10) -> tuple[list[SearchResult], str]:
    """Возвращает (results, engine_used). Auto-fallback по списку SEARCH_ENGINES.

    Порядок: serpapi → bing(api) → bing_html → google_playwright → duckduckgo.
    Серверные IP banятся DuckDuckGo, поэтому он fallback-of-last-resort.
    """
    for engine in SEARCH_ENGINES:
        try:
            if engine == "serpapi":
                r = await search_serpapi(query, num=num)
            elif engine == "bing":
                r = await search_bing(query, num=num)
            elif engine == "bing_html":
                r = await search_bing_html(query, num=num)
            elif engine == "google_playwright":
                r = await search_google_playwright(query, num=num)
            elif engine == "duckduckgo":
                r = await search_duckduckgo(query, num=num)
            else:
                r = []
            if r:
                log.debug("engine=%s returned %d", engine, len(r))
                return r, engine
        except Exception as exc:
            log.warning("search %s failed: %s", engine, exc)
    return [], "none"


# ============================================================================
# PDF download + persist
# ============================================================================

async def download_and_save_pdf(
    *,
    url: str,
    brand_slug: str,
    vendor_code: str,
    doc_type: str = "datasheet",
) -> tuple[str | None, int]:
    """Download → MinIO. Returns (object_key, size_bytes) or (None, 0) on error."""
    try:
        async with httpx.AsyncClient(
            timeout=90, follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; GluvexBrochureSearch/1.1)",
                "Accept": "application/pdf,*/*;q=0.5",
            },
        ) as c:
            r = await c.get(url)
        if r.status_code != 200:
            return None, 0
        ct = r.headers.get("content-type", "").lower()
        content = r.content
        # Real PDF check — magic bytes %PDF
        if not (content.startswith(b"%PDF") or "pdf" in ct):
            return None, 0
        if len(content) < 2048:   # < 2KB — скорее всего error page
            return None, 0

        h = hashlib.sha256(content).hexdigest()[:8]
        safe_code = re.sub(r"[^A-Za-z0-9_\-]", "_", vendor_code)[:60]
        safe_dt = re.sub(r"[^a-z_]", "", doc_type) or "doc"
        object_key = f"{brand_slug}/{safe_code}__{safe_dt}__{h}.pdf"
        put_object("product-brochures", object_key, content, content_type="application/pdf")
        return object_key, len(content)
    except Exception as exc:
        log.debug("download %s failed: %s", url, exc)
        return None, 0


# ============================================================================
# Main pipeline
# ============================================================================

async def enrich_brand_brochures(
    settings: Settings,
    *,
    brand: str,
    limit: int = 0,
    rate_limit_seconds: float = 3.0,
    max_pdfs_per_product: int = 5,
    category_filter: str | None = None,
    only_no_datasheet: bool = True,
):
    """Многократный поиск брошюр для всех продуктов бренда через интернет.

    :param brand: точное значение product.brand
    :param limit: 0 = все
    :param rate_limit_seconds: пауза между search-запросами (защита от banов)
    :param max_pdfs_per_product: сколько PDF максимум сохранять на 1 артикул
    :param category_filter: например 'sequencer_platform' — только приборы
    :param only_no_datasheet: True = только продукты без datasheet'ов
    """
    vendor_cfg = get_vendor_config(brand)
    conn = await get_conn()

    try:
        sql = """
            SELECT id, vendor_code, brand, model, category, display_name
            FROM product
            WHERE brand = $1 AND vendor_code IS NOT NULL AND vendor_code != ''
        """
        args: list[Any] = [brand]
        if only_no_datasheet:
            sql += "\nAND (datasheet_paths IS NULL OR array_length(datasheet_paths, 1) IS NULL)"
        if category_filter:
            sql += f"\nAND category = $2::product_category_t"
            args.append(category_filter)
        sql += "\nORDER BY id"
        if limit and limit > 0:
            sql += f"\nLIMIT {limit}"

        products = await conn.fetch(sql, *args)
        log.info(
            "brand=%s category=%s: %d products to enrich",
            brand, category_filter or "ALL", len(products),
        )
        if not products:
            return

        global_stats = {
            "total_products": len(products),
            "with_finds": 0,
            "pdfs_saved": 0,
            "queries_total": 0,
            "errors": 0,
        }

        for i, prod in enumerate(products, 1):
            product_id = prod["id"]
            vendor_code = prod["vendor_code"]
            model = prod["model"] or ""

            log.info("[%d/%d] %s | %s | %s",
                     i, len(products), vendor_code, prod["category"], model[:60])

            queries = build_queries(vendor_code, model, vendor_cfg)
            global_stats["queries_total"] += len(queries)

            # Track unique PDF URLs seen (deduplicate cross-query)
            seen_urls: set[str] = set()
            saved_keys: list[str] = []
            saved_metadata: list[dict] = []

            for q in queries:
                if len(saved_keys) >= max_pdfs_per_product:
                    break
                try:
                    results, engine = await search_any(q.text, num=10)
                except Exception as exc:
                    log.warning("    search '%s' failed: %s", q.text[:60], exc)
                    global_stats["errors"] += 1
                    await asyncio.sleep(rate_limit_seconds)
                    continue

                # Filter PDF candidates
                pdf_candidates = [r for r in results if r.is_pdf]
                log.debug("    Q='%s' (%s) → %d results, %d PDFs",
                          q.text[:60], engine, len(results), len(pdf_candidates))

                for r in pdf_candidates:
                    if r.url in seen_urls:
                        continue
                    seen_urls.add(r.url)
                    if len(saved_keys) >= max_pdfs_per_product:
                        break
                    doc_type = infer_doc_type(r.url, r.title, q.doc_type_hint)
                    obj_key, size = await download_and_save_pdf(
                        url=r.url,
                        brand_slug=vendor_cfg.brand_slug,
                        vendor_code=vendor_code,
                        doc_type=doc_type,
                    )
                    if obj_key:
                        saved_keys.append(obj_key)
                        saved_metadata.append({
                            "object_key": obj_key,
                            "source_url": r.url,
                            "title": r.title[:200],
                            "doc_type": doc_type,
                            "size_bytes": size,
                            "from_query": q.text[:120],
                            "search_engine": engine,
                        })
                        log.info("    + saved %-18s %s", doc_type, obj_key)
                # rate-limit между поисками
                await asyncio.sleep(rate_limit_seconds)

            if saved_keys:
                # Update product
                await conn.execute(
                    "UPDATE product SET datasheet_paths = $1, updated_at = now() WHERE id = $2",
                    saved_keys, product_id,
                )
                # Audit event
                global_stats["with_finds"] += 1
                global_stats["pdfs_saved"] += len(saved_keys)
            await conn.close() if False else None  # type-hint, leave open

            if i % 10 == 0:
                log.info("=== progress %d/%d: %s", i, len(products), global_stats)

        # Final audit
        log.info("DONE %s: %s", brand, global_stats)

    finally:
        await conn.close()

    # Audit after conn closed
    try:
        await audit_event(
            action="brochure_web_search_completed",
            actor_type="catalog_crawler",
            actor_id="brochure_web_search",
            payload={
                "brand": brand,
                "category_filter": category_filter,
                "stats": global_stats,
            },
        )
    except Exception as exc:
        log.warning("audit_event failed: %s", exc)
