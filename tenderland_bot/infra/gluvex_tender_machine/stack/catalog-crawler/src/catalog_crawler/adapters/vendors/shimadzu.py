"""Shimadzu adapter — JSON-driven, bypasses HTML scraping.

Shimadzu (shimadzu.com/an/) is a Vue.js SPA fed by JSON APIs. The whole product
catalog (~631 products) is exposed as a single JSON file, and per-product PDFs
are listed in a second JSON per product_id. We do NOT scrape HTML — we hit
JSON endpoints directly.

Endpoints (verified open through curl + IPRoyal residential):
  - /an/json/product_page/product_page_list.json
      → master catalog list[{category_id, nid, products: [...]}],
        each product has: product_id, name, sub_name, description, link_url,
        product_category[], represent_category_id, image_path, short_name,
        discontinued, release_date, tabs.{overview, downloads, spec, ...}
  - /an/json/advanced_product_search/merged_download_list/<product_id>.json
      → tree with PDF entries: {file_type: "PDF", url: "/an/.../file.pdf", region: [...]}
  - /an/json/product_category/product_category_list.json
      → top-level 19 categories (LC, LC-MS, GC, GC-MS, AA, ICP, UV-Vis, FTIR, etc.)

PDFs live at /an/sites/shimadzu.com.an/files/pim/pim_document_file/brochures/<dir>/<name>.pdf.

Categorization:
  represent_category_id (often a sub-category) → walk to top-level via
  product_category[] list, then map top-level ID → product_category_t.
  Fallback: URL keyword match + category-name fuzzy match.
"""
from __future__ import annotations

import asyncio
import json as json_lib
from typing import Any
from urllib.parse import urljoin, urlparse

import asyncpg
import httpx

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.fetcher import Fetcher


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36"
)


class ShimadzuAdapter(VendorAdapter):
    brand_name = "Shimadzu"
    brand_slug = "shimadzu"
    base_url = "https://www.shimadzu.com"
    domain_hint = "analytical"
    rate_limit_seconds = 0.5
    user_agent_override = BROWSER_UA

    PAGES_JSON_URL = "https://www.shimadzu.com/an/json/product_page/product_page_list.json"
    DOWNLOADS_JSON_TPL = (
        "https://www.shimadzu.com/an/json/advanced_product_search"
        "/merged_download_list/{pid}.json"
    )

    # Top-level Shimadzu category_id → product_category_t (verified IDs from product_category_list.json)
    TOP_CATEGORY_MAP: dict[int, str] = {
        339: "hplc_system",          # Liquid Chromatography
        345: "mass_spectrometer",    # Liquid Chromatograph-Mass Spectrometry
        353: "gc_system",            # Gas Chromatography
        359: "mass_spectrometer",    # Gas Chromatograph-Mass Spectrometry
        366: "consumable",           # Columns, Reagents and Consumables
        369: "software",             # Software & Informatics
        521: "mass_spectrometer",    # MALDI-Based Instruments and Solutions
        372: "uv_vis_spectrometer",  # Molecular Spectroscopy (UV-Vis / FTIR / Raman / NIR)
        385: "icp_ms",               # Elemental Analysis (AA / ICP-OES / ICP-MS / XRF)
        400: "other",                # Life Science Lab Instruments
        408: "other",                # Material Testing
        416: "other",                # Non-Destructive Testing (NDT)
        508: "other",                # Total Organic Carbon Analysis
        422: "other",                # Continuous Monitoring Analysis
        427: "other",                # Surface Analysis
        432: "other",                # Thermal Analysis
        434: "other",                # Particle Size Analysis
        439: "balance",              # Balances
        624: "accessory",            # Automated Sample Preparation System
    }

    # URL-path keyword overrides — applied to link_url path (lower-case).
    # Sorted longest-first at match time. More-specific keys beat less-specific.
    URL_CATEGORY_MAP: dict[str, str] = {
        # liquid chromatography drill-down
        "hplc-consumables": "consumable",
        "shim-pack": "hplc_column",
        "uhplc-column": "hplc_column",
        "hplc-column": "hplc_column",
        "lc-consumables": "consumable",
        "lc-column": "hplc_column",
        # liquid-chromatography hub URL slug (was missing — Nexera-e/MSS/Co-Sense fell in 'other')
        "liquid-chromatography": "hplc_system",
        "hplc-system": "hplc_system",
        "nexera": "hplc_system",        # все Nexera-X3, Nexera-Lite, Nexera MX, Mikros — HPLC
        "uhplc": "hplc_system",
        "hplc": "hplc_system",
        # gas chromatography drill-down
        "gas-chromatography": "gc_system",
        "gc-system": "gc_system",
        "gc-column": "gc_column",
        "gc-consumables": "consumable",
        # mass spec
        "triple-quadrupole": "mass_spectrometer",
        "single-quadrupole": "mass_spectrometer",
        "tof-ms": "mass_spectrometer",
        "qtof": "mass_spectrometer",
        "lc-ms": "mass_spectrometer",
        "gc-ms": "mass_spectrometer",
        "lcms": "mass_spectrometer",
        "gcms": "mass_spectrometer",
        "maldi": "mass_spectrometer",
        # spectroscopy
        "ftir-microscope": "ftir_spectrometer",
        "ftir": "ftir_spectrometer",
        "raman": "uv_vis_spectrometer",  # no raman enum; closest analytical match
        "uv-vis-nir": "uv_vis_spectrometer",
        "uv-vis": "uv_vis_spectrometer",
        "spectrophotometer": "uv_vis_spectrometer",
        # elemental
        "atomic-absorption": "aas_system",
        "aas-system": "aas_system",
        "icp-oes": "icp_oes",
        "icp-ms": "icp_ms",
        "edx-fs": "icp_ms",         # ED-XRF; closest analytical bucket
        "wavelength-dispersive-x-ray-fluorescence": "icp_ms",
        "optical-emission-spectroscopy": "icp_oes",
        # accessories / consumables explicit
        "vials": "vial",
        "syringe-filter": "syringe_filter",
        "autosampler": "hplc_autosampler",
        # balances
        "analytical-balances": "balance",
        "electronic-balances": "balance",
        "moisture-analyzer": "balance",
        # software always last
        "software": "software",
    }

    def __init__(self, settings):
        super().__init__(settings)
        # Populated by list_product_urls() so parse_product() can read by URL
        self._url_to_product: dict[str, dict[str, Any]] = {}

    # ---------- list_product_urls ----------
    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        print(f"  Fetching master JSON: {self.PAGES_JSON_URL}")
        text = await fetcher.get(self.PAGES_JSON_URL)
        data = json_lib.loads(text)

        total = sum(len(e.get("products", [])) for e in data)
        urls: list[str] = []
        seen: set[str] = set()
        skipped_no_url = 0
        skipped_discontinued = 0
        for entry in data:
            for p in entry.get("products", []):
                if p.get("discontinued"):
                    skipped_discontinued += 1
                    continue
                link_url = p.get("link_url") or p.get("alias")
                if not link_url:
                    skipped_no_url += 1
                    continue
                full = urljoin(self.base_url, link_url)
                if full in seen:
                    continue
                seen.add(full)
                self._url_to_product[full] = p
                urls.append(full)

        print(
            f"  Master JSON: {total} entries → kept {len(urls)} "
            f"(skipped {skipped_discontinued} discontinued, {skipped_no_url} no-url)"
        )
        return urls

    # ---------- parse_product ----------
    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        """Builds VendorProductData from cached master JSON entry + downloads JSON.

        `html` argument is ignored — Shimadzu HTML is a Vue.js SPA shell with no
        useful product data.
        """
        p = self._url_to_product.get(url)
        if not p:
            return None
        name = (p.get("name") or "").strip()
        if not name:
            return None

        sub_name = (p.get("sub_name") or "").strip()
        description_text = (p.get("description") or "").strip() or sub_name
        product_id = p.get("product_id")
        short_name = (p.get("short_name") or "").strip()

        # Model extraction:
        #  - prefer short_name if available and reasonable
        #  - else last meaningful path segment (e.g., .../hplc-system/mss/index.html → "mss")
        #  - else first 80 chars of name
        path = urlparse(url).path
        parts = [s for s in path.strip("/").split("/") if s and s != "index.html"]
        slug = parts[-1] if parts else ""
        if short_name and len(short_name) <= 60:
            model = short_name
        elif slug:
            # CAP uppercase short slugs ("mss" → "MSS"), keep dashed multi-token as-is
            model = slug.upper() if (len(slug) <= 8 and "-" not in slug) else slug
        else:
            model = name[:80]

        # Categories
        cats = p.get("product_category") or []
        cat_names = [c.get("name", "") for c in cats if c.get("name")]
        group = cat_names[0] if cat_names else None

        # Fetch downloads JSON → PDFs
        pdf_urls: list[str] = []
        if product_id:
            try:
                pdf_urls = await self._fetch_pdf_urls(product_id)
            except Exception as e:
                print(f"    [pid={product_id}] downloads JSON fail: {e}")

        # Image (one only — front-of-card thumbnail)
        images: list[str] = []
        if p.get("image_path"):
            images.append(urljoin(self.base_url, p["image_path"]))

        # Markdown summary — always saved (Shimadzu description is rich, HTML page is SPA shell)
        md_lines = [
            f"# {name}",
            "",
            f"**Производитель:** Shimadzu",
            f"**Модель:** {model}",
        ]
        if sub_name and sub_name != name:
            md_lines.append(f"**Подзаголовок:** {sub_name}")
        if group:
            md_lines.append(f"**Категория:** {group}")
        if product_id:
            md_lines.append(f"**Shimadzu Product ID:** {product_id}")
        md_lines.append(f"**Источник:** {url}")
        md_lines.append("")
        if cat_names and len(cat_names) > 1:
            md_lines.append(f"**Все категории:** {' / '.join(cat_names)}")
            md_lines.append("")
        if description_text:
            md_lines += [description_text, ""]
        description_md = "\n".join(md_lines)

        return VendorProductData(
            vendor_code=str(product_id) if product_id else model[:50],
            name=name[:500],
            model=model[:200],
            group=group[:120] if group else None,
            description_md=description_md,
            pdf_urls=pdf_urls,
            image_urls=images,
            specs={},
            source_url=url,
            raw_metadata={
                "product_id": product_id,
                "represent_category_id": p.get("represent_category_id"),
                "categories": cat_names,
                "release_date": p.get("release_date"),
                "short_name": short_name,
                "url_slug": slug,
            },
        )

    # ---------- helpers ----------
    async def _fetch_pdf_urls(self, product_id: int) -> list[str]:
        """Fetches Shimadzu's per-product downloads JSON and walks it for PDF entries."""
        url = self.DOWNLOADS_JSON_TPL.format(pid=product_id)
        await asyncio.sleep(self.rate_limit_seconds)
        async with httpx.AsyncClient(
            timeout=60,
            follow_redirects=True,
            proxy=self.proxy_url,
            headers={"User-Agent": self.user_agent_override or BROWSER_UA},
        ) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return []
            try:
                data = r.json()
            except Exception:
                return []
        return self._walk_pdfs(data)[:5]  # cap per product

    def _walk_pdfs(self, obj: Any) -> list[str]:
        """Recursively collects {file_type: PDF, url: ...} entries from downloads JSON."""
        urls: list[str] = []
        seen: set[str] = set()

        def visit(o: Any) -> None:
            if isinstance(o, dict):
                if o.get("file_type") == "PDF" and o.get("url"):
                    full = urljoin(self.base_url, o["url"])
                    if full not in seen and full.lower().endswith(".pdf"):
                        seen.add(full)
                        urls.append(full)
                for v in o.values():
                    visit(v)
            elif isinstance(o, list):
                for x in o:
                    visit(x)

        visit(obj)
        return urls

    def _guess_category(self, data: VendorProductData) -> str:
        """Category resolution: TOP_CATEGORY_MAP via product_category[] ancestor,
        then URL keyword, then category-name fuzzy. Default 'other'."""
        # 1. Walk through product_category[] ids; first one matching TOP_CATEGORY_MAP wins.
        #    represent_category_id may be a sub-cat — need raw ids list, not available
        #    on data; but data.raw_metadata has 'represent_category_id' AND we can match
        #    by category NAME against TOP_CATEGORY_MAP through their canonical names.
        rep_cid = data.raw_metadata.get("represent_category_id")
        if isinstance(rep_cid, int) and rep_cid in self.TOP_CATEGORY_MAP:
            return self.TOP_CATEGORY_MAP[rep_cid]

        # 2. URL keyword (sorted by length desc — most specific first)
        url_lower = data.source_url.lower()
        for kw in sorted(self.URL_CATEGORY_MAP.keys(), key=lambda s: -len(s)):
            if kw in url_lower:
                return self.URL_CATEGORY_MAP[kw]

        # 3. Category-name fuzzy fallback
        for cname in data.raw_metadata.get("categories", []):
            cl = cname.lower()
            if "liquid chromato" in cl or "hplc" in cl or "uplc" in cl:
                return "hplc_system"
            if "gas chromato" in cl:
                return "gc_system"
            if "mass spec" in cl or "maldi" in cl:
                return "mass_spectrometer"
            if "ftir" in cl or "infrared" in cl:
                return "ftir_spectrometer"
            if "uv-vis" in cl or "molecular spectro" in cl:
                return "uv_vis_spectrometer"
            if "icp" in cl:
                return "icp_ms"
            if "atomic absorption" in cl or "aas" in cl:
                return "aas_system"
            if "balance" in cl:
                return "balance"

        return "other"
