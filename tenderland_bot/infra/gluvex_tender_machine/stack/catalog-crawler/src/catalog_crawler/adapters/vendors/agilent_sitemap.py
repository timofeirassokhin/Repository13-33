"""Agilent sitemap-only adapter.

Agilent защищён Akamai — HTML-pages не парсятся даже через residential proxy.
НО sitemap.xml пускает всех (нужен для SEO).

Стратегия: парсим sitemap → создаём stub-product записи (brand+url+slug) → описания
и specs приходят позже через distributor adapters (Lacopa/Millab/Element-msc).
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urlparse

from lxml import etree

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.fetcher import Fetcher


SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


class AgilentSitemapAdapter(VendorAdapter):
    """Парсит sitemap Agilent → создаёт stub-product entries."""

    brand_name = "Agilent Technologies"
    brand_slug = "agilent"
    base_url = "https://www.agilent.com"
    domain_hint = "analytical"
    rate_limit_seconds = 0.5

    SITEMAP_INDEX = "https://www.agilent.com/sitemap.xml"
    PRODUCT_SITEMAPS = [
        "https://www.agilent.com/products0.xml",
        "https://www.agilent.com/pim_commerce01.xml",
        "https://www.agilent.com/pim_commerce1.xml",
    ]

    # маппинг category→product_category_t
    CATEGORY_MAP: dict[str, str] = {
        "liquid-chromatography": "hplc_system",
        "gas-chromatography": "gc_system",
        "mass-spectrometry": "mass_spectrometer",
        "atomic-spectroscopy": "aas_system",
        "icp-ms": "icp_ms",
        "icp-oes": "icp_oes",
        "uv-vis": "uv_vis_spectrometer",
        "molecular-spectroscopy": "ftir_spectrometer",
        "hplc-systems": "hplc_system",
        "hplc-columns": "hplc_column",
        "gc-systems": "gc_system",
        "gc-columns": "gc_column",
        "sample-vials": "vial",
        "mass-spec-systems": "mass_spectrometer",
        "polymerase-chain-reaction-(pcr)": "pcr_kit",
        "ngs": "ngs_library_prep_kit",
        "sureselect": "ngs_target_capture_panel",
        "vacuum-technologies": "accessory",
    }

    def __init__(self, settings):
        super().__init__(settings)
        self.user_agent_override = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )
        import os
        self.proxy_url = os.environ.get("PROXY_URL") or None

    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        """Тянем все URL из 3 product sitemap'ов Agilent (фильтруя /en/ только)."""
        all_urls: set[str] = set()
        for sm_url in self.PRODUCT_SITEMAPS:
            try:
                xml = await fetcher.get(sm_url)
            except Exception as e:
                print(f"  sitemap fail {sm_url}: {e}")
                continue
            try:
                root = etree.fromstring(xml.encode("utf-8"))
            except Exception as e:
                print(f"  sitemap parse fail {sm_url}: {e}")
                continue

            for u in root.findall("sm:url", SITEMAP_NS):
                loc = u.findtext("sm:loc", "", SITEMAP_NS)
                # только /en/product/... (английский)
                if "/en/product" not in loc:
                    continue
                # отфильтровать non-en локали
                if any(x in loc for x in ("/zh-cn/", "/ja-jp/", "/ko-kr/", "/de-de/", "/fr-fr/", "/it-it/")):
                    continue
                all_urls.add(loc)

            print(f"  sitemap {sm_url}: total in DB = {len(all_urls)}")
            if limit and len(all_urls) >= limit:
                break

        urls = sorted(all_urls)
        print(f"  ИТОГО: {len(urls)} EN-product URL из Agilent sitemap")
        return urls

    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        """Sitemap-only mode: html не fetch'ится для Agilent (403 Akamai).
        Вместо этого формируем VendorProductData из URL-структуры.

        НО! base.run() уже сделал fetch и передал html сюда. Если html — Access Denied,
        мы всё равно создаём stub-запись по URL pattern.
        """
        # URL pattern: https://www.agilent.com/en/product/<category>/<sub>/<sub>/<model-slug>
        path = urlparse(url).path.strip("/").split("/")
        # path: ['en', 'product', 'category', 'sub1', 'sub2', 'model-slug']
        if len(path) < 4:
            return None

        category_top = path[2] if len(path) >= 3 else ""
        product_slug = path[-1]
        intermediate = path[3:-1] if len(path) > 4 else []
        group = " / ".join(s.replace("-", " ").title() for s in [category_top] + intermediate)

        # name = красивая форма последнего сегмента
        name = product_slug.replace("-", " ").replace("_", " ").title()
        # некоторые slug заканчиваются на 6-цифр номер: split it
        m = re.match(r"^(.+?)-(\d{4,8})$", product_slug)
        vendor_code = ""
        if m:
            name = m.group(1).replace("-", " ").title()
            vendor_code = m.group(2)

        # пытаемся достать что-то из html если он был получен (но обычно 403 = маленький HTML)
        # base.run() передаёт html как есть; если 403, у нас Access Denied страница ~400 байт
        description_md = self._build_markdown_stub(name, vendor_code, group, url)

        return VendorProductData(
            vendor_code=vendor_code,
            name=name[:500],
            model=product_slug[:200],
            group=group[:120],
            description_md=description_md,
            pdf_urls=[],
            image_urls=[],
            specs={},
            source_url=url,
            raw_metadata={
                "stub_from_sitemap": True,
                "category_top": category_top,
                "intermediate": intermediate,
                "needs_enrichment": True,
            },
        )

    def _build_markdown_stub(self, name: str, vendor_code: str, group: str, url: str) -> str:
        return (
            f"# {name}\n"
            f"\n"
            f"**Производитель:** {self.brand_name}\n"
            f"**Группа:** {group}\n"
            f"**Артикул (slug):** {vendor_code or '—'}\n"
            f"**Источник:** {url}\n"
            f"\n"
            f"> Это **stub-запись** из Agilent sitemap.\n"
            f"> Описания и характеристики будут добавлены позже через дистрибьюторов\n"
            f"> (Lacopa, Millab, Element-msc) которые импортируют Agilent в Россию.\n"
        )

    def _guess_category(self, data: VendorProductData) -> str:
        cat = data.raw_metadata.get("category_top", "")
        if cat in self.CATEGORY_MAP:
            return self.CATEGORY_MAP[cat]
        for slug, c in self.CATEGORY_MAP.items():
            if slug in cat or slug in (data.raw_metadata.get("intermediate") or []):
                return c
        return "other"
