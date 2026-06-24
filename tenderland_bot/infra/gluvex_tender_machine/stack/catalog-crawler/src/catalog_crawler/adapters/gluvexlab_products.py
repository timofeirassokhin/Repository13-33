"""GluvexLab product-page extractor (Phase 2).

Парсит детальные карточки товаров → INSERT в gluvex_documents.product

Best-effort селекторы — на разных типах товаров вёрстка может отличаться, мы
извлекаем что есть, остальное оставляем в metadata.raw_html_snippet для последующей
доработки.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

import asyncpg
from lxml import etree
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.fetcher import Fetcher
from catalog_crawler.settings import Settings


SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ============================================================
# Маппинг slug категории gluvexlab → product_category_t ENUM
# ============================================================
# Из 542 категорий покрываем топовые ~30-40, остальные → 'other' + subcategory=<slug>.
# Расширяется при анализе результатов первого прогона.
GLUVEX_CATEGORY_MAP: dict[str, str] = {
    # хроматография — системы
    "zhidkostnye_khromatografy": "hplc_system",
    "gazovye_khromatografy": "gc_system",
    "gazovye-mass-spektrometry": "mass_spectrometer",
    "gidkostnye-mass-spektrometry": "mass_spectrometer",
    "khromatomass-spektrometry": "mass_spectrometer",
    "mass-spektrometry": "mass_spectrometer",
    # колонки
    "kolonki_dlya_khromatografii": "hplc_column",
    "kolonki-dlya-gkh": "gc_column",        # фикс опечатки
    "kolonki-dlya-vezhkh": "hplc_column",   # фикс опечатки
    "kolonki-dlya-gh": "gc_column",          # alt slug (на случай)
    "kolonki-dlya-vegkh": "hplc_column",    # alt slug
    "khromatograficheskie_kolonki": "hplc_column",
    # HPLC модули — для slot-based config
    "moduli-avtosamplerov-dlya-vegch": "hplc_autosampler",
    "avtosamplery": "hplc_autosampler",
    "moduli-detektorov-dlya-vegch": "hplc_detector",
    # спектроскопия
    "atomno_absorbtsionnye_spektrofotometry": "aas_system",
    "ik-fure-spektrometry": "ftir_spectrometer",
    "uf_spektrofotometry": "uv_vis_spectrometer",
    "uf-vidimye-spektrofotometry": "uv_vis_spectrometer",
    "raman_spektrometers": "raman_spectrometer",
    "icp-oes": "icp_oes",
    "icp_oes": "icp_oes",
    "icp-ms": "icp_ms",
    "icp_ms": "icp_ms",
    # секвенирование
    "sekvenatory": "sequencer_platform",
    "reagenty-dlya-sekvenirovaniya": "sequencer_reagent_kit",
    "nabory-dlya-podgotovki-bibliotek-ngs": "ngs_library_prep_kit",
    "naborysekvenirovanie-ngs": "ngs_target_capture_panel",
    # PCR
    "ampligenetics": "realtime_pcr",
    "realtime-pcr": "realtime_pcr",
    "ampligenetics-vremyaprolomu": "realtime_pcr",
    "amplifiers": "pcr_thermal_cycler",
    "real-time-pcr-system": "realtime_pcr",
    "nabory-dlya-pcr": "pcr_kit",
    "nabory-dlya-vydelenija-dnk": "dna_extraction_kit",
    "nabory-dlya-vydelenija-rnk": "rna_extraction_kit",
    # общая лаборатория
    "tsentrifugi": "centrifuge",
    "centrifugi": "centrifuge",
    "shejkery-i-vortexes": "shaker_vortex",
    "vortexes": "shaker_vortex",
    "inkubatory": "incubator",
    "sushilnye-shkafy": "drying_oven",
    "termostaty": "drying_oven",
    "klimaticheskie-kamery": "climate_chamber",
    "boksy-biologicheskoy-bezopasnosti": "biological_safety_cabinet",
    "laminarnye-shkafy": "laminar_hood",
    "vesy-laboratornye": "balance",
    "titratory": "titrator",
    "sistemy-vodopodgotovki": "water_purifier",
    "gel-elektroforez": "electrophoresis",
    # расходники
    "vialy-dlya-khromatografii": "vial",
    "vialy": "vial",
    "filtry-membrannye": "syringe_filter",
    "shpritsevye-filtry": "syringe_filter",
    "kartridzhi-spe": "spe_cartridge",
    "septas": "septa",
    "butylki-laboratornye": "consumable",
    "kolby-laboratornye": "consumable",
    "stakany_laboratornye": "consumable",
    "tsilindry": "consumable",
    "pipetki": "consumable",
    "nakonechniki": "consumable",
    "probirki": "consumable",
}

# domain по category
CATEGORY_TO_DOMAIN: dict[str, str] = {
    "hplc_system": "analytical", "gc_system": "analytical", "mass_spectrometer": "analytical",
    "aas_system": "analytical", "icp_oes": "analytical", "icp_ms": "analytical",
    "uv_vis_spectrometer": "analytical", "ftir_spectrometer": "analytical",
    "nir_spectrometer": "analytical", "raman_spectrometer": "analytical",
    "hplc_column": "analytical", "gc_column": "analytical",
    "sequencer_platform": "genetics_ngs", "sequencer_flowcell": "genetics_ngs",
    "sequencer_reagent_kit": "genetics_ngs",
    "ngs_library_prep_kit": "genetics_ngs", "ngs_target_capture_panel": "genetics_ngs",
    "ngs_amplicon_panel": "genetics_ngs",
    "pcr_kit": "molecular_diagnostics", "realtime_pcr_kit": "molecular_diagnostics",
    "dna_extraction_kit": "molecular_diagnostics", "rna_extraction_kit": "molecular_diagnostics",
    "pcr_thermal_cycler": "molecular_diagnostics", "realtime_pcr": "molecular_diagnostics",
}


def map_category(slug: str) -> tuple[str, str, str]:
    """slug → (product_category_t, product_domain_t, subcategory_raw)"""
    cat = GLUVEX_CATEGORY_MAP.get(slug, "other")
    domain = CATEGORY_TO_DOMAIN.get(cat, "general_lab")
    return cat, domain, slug


# ============================================================
# Extractor — из HTML страницы → dict
# ============================================================
def extract_product(url: str, html: str) -> dict[str, Any]:
    """Best-effort извлечение полей со страницы товара."""
    tree = HTMLParser(html)

    # name — приоритет: h1 > og:title > <title>
    h1 = tree.css_first("h1")
    og_title = tree.css_first("meta[property='og:title']")
    title_tag = tree.css_first("title")
    name = (h1.text(strip=True) if h1 else None) \
           or (og_title.attrs.get("content", "").strip() if og_title else None) \
           or (title_tag.text(strip=True) if title_tag else None) \
           or "?"

    # description — meta[name=description] / og:description
    desc_meta = tree.css_first("meta[name='description']") \
                 or tree.css_first("meta[property='og:description']")
    description = desc_meta.attrs.get("content", "").strip() if desc_meta else None

    # breadcrumbs — пытаемся вытащить
    breadcrumbs: list[str] = []
    for selector in ("nav.breadcrumb a", ".breadcrumb a", "[itemtype*='BreadcrumbList'] a"):
        nodes = tree.css(selector)
        if nodes:
            breadcrumbs = [n.text(strip=True) for n in nodes if n.text(strip=True)]
            break

    # category из URL — /catalog/<category>/<slug>
    parts = urlparse(url).path.strip("/").split("/")
    category_slug = parts[1] if len(parts) >= 3 and parts[0] == "catalog" else ""
    product_slug = parts[-1] if len(parts) >= 3 else ""

    category, domain, subcategory = map_category(category_slug)

    # бренд — пытаемся из meta или breadcrumb (но обычно бренд указан на странице явно)
    brand_meta = tree.css_first("meta[itemprop='brand']") \
                  or tree.css_first("meta[property='product:brand']")
    brand = brand_meta.attrs.get("content", "").strip() if brand_meta else None

    # ищем "Производитель: X" в тексте — частый pattern на ru-сайтах
    if not brand:
        body_text = tree.css_first("body").text(separator=" ", strip=True) if tree.css_first("body") else ""
        m = re.search(r"Производитель:?\s*([A-Za-zА-Яа-я0-9\-\.\s]{2,40})", body_text)
        if m:
            brand = m.group(1).strip().split("  ")[0].strip()

    # vendor_code (артикул) — pattern "Артикул:" или "SKU:" или "Код:"
    vendor_code = None
    body_text = tree.css_first("body").text(separator=" ", strip=True) if tree.css_first("body") else ""
    for pat in (r"Артикул:?\s*([A-Z0-9\-\._/]+)", r"SKU:?\s*([A-Z0-9\-\._/]+)", r"Код:?\s*([A-Z0-9\-\._/]+)"):
        m = re.search(pat, body_text)
        if m:
            vendor_code = m.group(1).strip()
            break

    # PDF брошюры — все <a href*='.pdf'>
    pdf_urls = []
    for a in tree.css("a[href$='.pdf'], a[href*='.pdf?']"):
        href = a.attrs.get("href", "")
        if href:
            pdf_urls.append(urljoin(url, href))
    pdf_urls = list(dict.fromkeys(pdf_urls))  # dedup сохраняя порядок

    # изображения товара — основное
    images = []
    for img in tree.css("img"):
        src = img.attrs.get("src") or img.attrs.get("data-src", "")
        if src and any(kw in src.lower() for kw in ("catalog", "product", "tovar", "static")):
            full = urljoin(url, src)
            if not full.endswith((".svg", ".gif")):
                images.append(full)
    images = list(dict.fromkeys(images))[:5]

    # таблица характеристик — частый pattern <table> или dl/dt/dd
    specs: dict[str, str] = {}
    for table in tree.css("table"):
        for tr in table.css("tr"):
            cells = tr.css("td, th")
            if len(cells) == 2:
                key = cells[0].text(strip=True)
                val = cells[1].text(strip=True)
                if key and val and len(key) < 60 and len(val) < 200:
                    specs[key] = val
    for dl in tree.css("dl"):
        dts = dl.css("dt")
        dds = dl.css("dd")
        for dt, dd in zip(dts, dds):
            k = dt.text(strip=True)
            v = dd.text(strip=True)
            if k and v and len(k) < 60 and len(v) < 200:
                specs[k] = v

    # display_name = name; model — пытаемся извлечь после "Производитель: X" или из name
    model = name
    if brand and name.lower().startswith(brand.lower()):
        model = name[len(brand):].strip(" -—,:")

    return {
        "url": url,
        "name": name,
        "display_name": name,
        "description": description,
        "brand": brand,
        "model": model,
        "vendor_code": vendor_code,
        "category_slug": category_slug,
        "category": category,
        "subcategory": subcategory,
        "domain": domain,
        "product_slug": product_slug,
        "breadcrumbs": breadcrumbs,
        "brochure_urls": pdf_urls,
        "images": images,
        "base_specs": specs,
        "needs_brochure_lookup": len(pdf_urls) == 0,
    }


# ============================================================
# Crawler — fetch all product URLs from sitemaps + extract
# ============================================================
async def crawl_products(
    settings: Settings,
    limit: int = 0,
    sitemap_shards: Optional[list[int]] = None,
    tenant_id: str = "11111111-1111-1111-1111-111111111111",
) -> dict[str, Any]:
    """
    Args:
      limit: ограничить число товаров (0 = все)
      sitemap_shards: список индексов sitemap_<N> (например [0, 1]).
                      None = все шарды (полный crawl, ~57k товаров).
    """
    print(f"==> crawl_products: limit={limit}, shards={sitemap_shards or 'all'}")
    base = "https://gluvexlab.com"

    async with Fetcher() as f:
        # 1. список всех URL из выбранных шардов
        if sitemap_shards is None:
            # парсим sitemap-index чтобы найти все sharded product sitemaps
            xml = await f.get(f"{base}/sitemap.xml")
            root = etree.fromstring(xml.encode())
            shard_urls = []
            for sm in root.findall("sm:sitemap", SITEMAP_NS):
                loc = sm.findtext("sm:loc", "", SITEMAP_NS)
                if "catalog_products_" in loc:
                    shard_urls.append(loc)
        else:
            shard_urls = [f"{base}/sitemap.catalog_products_{i}.xml" for i in sitemap_shards]

        print(f"    shard sitemaps: {len(shard_urls)}")
        all_urls: list[str] = []
        for sm_url in shard_urls:
            xml = await f.get(sm_url)
            root = etree.fromstring(xml.encode())
            for u in root.findall("sm:url", SITEMAP_NS):
                all_urls.append(u.findtext("sm:loc", "", SITEMAP_NS))

        print(f"    total product URLs: {len(all_urls)}")
        if limit:
            all_urls = all_urls[:limit]
            print(f"    limited to: {len(all_urls)}")

        # 2. fetch + extract + DB write
        stats = {
            "total": len(all_urls), "ok": 0, "errors": 0,
            "by_category": {}, "by_brand": {}, "with_brochure": 0, "without_brochure": 0,
        }

        conn: asyncpg.Connection = await get_conn()
        try:
            for i, url in enumerate(all_urls, 1):
                try:
                    html = await f.get(url)
                    p = extract_product(url, html)
                    content_hash = hashlib.sha256(html.encode("utf-8")).digest()

                    # INSERT в product (ON CONFLICT updates)
                    await conn.execute("""
                        INSERT INTO product
                          (tenant_id, brand, model, category, domain, display_name, description,
                           subcategory, vendor_code, base_specs, source_urls, brochure_urls,
                           metadata, content_hash, imported_at, imported_from)
                        VALUES ($1, $2, $3, $4::product_category_t, $5::product_domain_t,
                                $6, $7, $8, $9, $10::jsonb, $11::text[], $12::text[],
                                $13::jsonb, $14, now(), 'gluvexlab')
                        ON CONFLICT (tenant_id, brand, model) DO UPDATE SET
                          display_name = EXCLUDED.display_name,
                          description = EXCLUDED.description,
                          category = EXCLUDED.category,
                          subcategory = EXCLUDED.subcategory,
                          vendor_code = EXCLUDED.vendor_code,
                          base_specs = EXCLUDED.base_specs,
                          source_urls = EXCLUDED.source_urls,
                          brochure_urls = EXCLUDED.brochure_urls,
                          metadata = EXCLUDED.metadata,
                          content_hash = EXCLUDED.content_hash,
                          imported_at = EXCLUDED.imported_at,
                          updated_at = now()
                    """,
                        tenant_id,
                        p["brand"] or "_unknown",
                        p["model"][:200],  # max 200 chars
                        p["category"],
                        p["domain"],
                        p["display_name"][:500],
                        p["description"],
                        p["subcategory"][:120] if p["subcategory"] else None,
                        p["vendor_code"],
                        json.dumps(p["base_specs"]),
                        [url],
                        p["brochure_urls"],
                        json.dumps({
                            "category_slug": p["category_slug"],
                            "product_slug": p["product_slug"],
                            "breadcrumbs": p["breadcrumbs"],
                            "images": p["images"],
                            "needs_brochure_lookup": p["needs_brochure_lookup"],
                        }),
                        content_hash,
                    )

                    stats["ok"] += 1
                    stats["by_category"][p["category"]] = stats["by_category"].get(p["category"], 0) + 1
                    if p["brand"]:
                        stats["by_brand"][p["brand"]] = stats["by_brand"].get(p["brand"], 0) + 1
                    if p["brochure_urls"]:
                        stats["with_brochure"] += 1
                    else:
                        stats["without_brochure"] += 1

                    if i <= 5 or i % 50 == 0 or i == len(all_urls):
                        print(f"  [{i:>5}/{len(all_urls)}] {p['category']:30s} {p['brand'] or '?':20s} {p['model'][:60]}")
                except Exception as e:
                    stats["errors"] += 1
                    print(f"  [{i:>5}] ERROR: {url} → {e}")
        finally:
            await conn.close()

    # 3. audit + summary
    await audit_event(
        action="crawl_products_complete",
        payload={
            "source": "gluvexlab",
            "total": stats["total"],
            "ok": stats["ok"],
            "errors": stats["errors"],
            "with_brochure": stats["with_brochure"],
            "without_brochure": stats["without_brochure"],
            "top_categories": dict(sorted(stats["by_category"].items(), key=lambda x: -x[1])[:10]),
            "top_brands": dict(sorted(stats["by_brand"].items(), key=lambda x: -x[1])[:10]),
        },
    )

    print(f"\n==> SUMMARY")
    print(f"    OK: {stats['ok']}, errors: {stats['errors']}")
    print(f"    with brochure: {stats['with_brochure']}, without: {stats['without_brochure']}")
    print(f"    by category (top 10):")
    for cat, n in sorted(stats["by_category"].items(), key=lambda x: -x[1])[:10]:
        print(f"      {cat:30s} {n}")
    print(f"    by brand (top 10):")
    for brand, n in sorted(stats["by_brand"].items(), key=lambda x: -x[1])[:10]:
        print(f"      {brand:30s} {n}")

    return stats
