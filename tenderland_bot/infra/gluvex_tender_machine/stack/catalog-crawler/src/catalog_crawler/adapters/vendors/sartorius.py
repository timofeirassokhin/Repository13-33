"""Sartorius official site adapter.

sartorius.com — большая компания: lab equipment (балансы, пипетки),
bioprocess (биореакторы, cell culture), filtration, lab water, BLI (Octet),
diagnostics. Сайт открытый при User-Agent похожем на браузер (303-редирект иначе).

URL pattern:
  /en/products                              — root
  /en/products/<category>                   — категория (cell-culture-media, biolayer-interferometry)
  /en/products/<category>/<series-or-product>  — конкретный продукт ИЛИ подкатегория
  /en/products/<category>/<sub>/<model>     — иногда глубже

Стратегия: 2-step walk — root → list categories → list products в каждой.
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.fetcher import Fetcher


class SartoriusAdapter(VendorAdapter):
    brand_name = "Sartorius"
    brand_slug = "sartorius"
    base_url = "https://www.sartorius.com"
    domain_hint = "life_science_general"
    rate_limit_seconds = 0.7
    user_agent_override = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
    )

    # маппинг slug категории Sartorius → product_category_t
    CATEGORY_MAP: dict[str, str] = {
        "weighing": "balance",
        "laboratory-balances": "balance",
        "biolayer-interferometry": "other",  # Octet — нет аналога, держим в other
        "cell-culture-media": "consumable",
        "cell-culture-reagents-supplements": "consumable",
        "cell-analysis": "other",
        "lab-filtration-purification": "syringe_filter",
        "lab-water": "water_purifier",
        "pipetting": "consumable",
        "balances-moisture-analyzers": "balance",
        "filters": "syringe_filter",
        "single-use-bioreactors": "other",
        "bioreactors-fermentors": "other",
        "filtration-purification": "syringe_filter",
        "cell-line-development": "other",
        "diagnostics": "other",
    }
    DOMAIN_MAP: dict[str, str] = {
        "balance": "general_lab",
        "syringe_filter": "analytical",
        "water_purifier": "general_lab",
        "consumable": "life_science_general",
    }

    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        """Собираем все L4 product URL'ы со страницы /en/products.

        Если найдено мало — ходим в каждую L3 category и собираем там тоже.
        """
        all_urls: set[str] = set()

        # 1. сначала — главная /en/products
        root_url = f"{self.base_url}/en/products"
        try:
            html = await fetcher.get(root_url)
        except Exception as e:
            print(f"  list: root {root_url} fail: {e}")
            return []
        l3_categories: set[str] = set()
        for u in self._extract_internal_links(html, root_url):
            depth = self._url_depth(u)
            if depth == 3:
                l3_categories.add(u)
            elif depth >= 4:
                all_urls.add(u)

        print(f"  list: root → {len(l3_categories)} L3 categories, {len(all_urls)} direct L4+ products")

        # 2. ходим по L3 категориям, собираем оттуда продукты
        for i, cat_url in enumerate(sorted(l3_categories), 1):
            try:
                html = await fetcher.get(cat_url)
            except Exception as e:
                print(f"  list: cat fail {cat_url}: {e}")
                continue
            cat_products = 0
            for u in self._extract_internal_links(html, cat_url):
                if self._url_depth(u) >= 4 and u not in all_urls:
                    all_urls.add(u)
                    cat_products += 1
            if cat_products > 0 and i <= 30:
                print(f"  list: [{i}/{len(l3_categories)}] {urlparse(cat_url).path}: +{cat_products}")

            if limit and len(all_urls) >= limit * 2:
                break

        urls = sorted(all_urls)
        print(f"  list: TOTAL {len(urls)} product/subcategory URLs")
        return urls

    @staticmethod
    def _extract_internal_links(html: str, base_url: str) -> set[str]:
        tree = HTMLParser(html)
        out: set[str] = set()
        for a in tree.css("a[href]"):
            href = a.attrs.get("href", "")
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            full = urljoin(base_url, href)
            full = full.split("#")[0].split("?")[0]
            p = urlparse(full)
            if p.netloc != "www.sartorius.com":
                continue
            if "/en/products" not in p.path:
                continue
            # игнорируем resources / compendium / specials
            if any(x in p.path for x in (
                "/resources", "-resources", "/compendium", "/calculator",
                "/applications", "/services", "/contact",
            )):
                continue
            out.add(full)
        return out

    @staticmethod
    def _url_depth(url: str) -> int:
        return len([s for s in urlparse(url).path.strip("/").split("/") if s])

    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        tree = HTMLParser(html)

        # name
        h1 = tree.css_first("h1")
        og = tree.css_first("meta[property='og:title']")
        name = (h1.text(strip=True) if h1 else None) \
               or (og.attrs.get("content", "").strip() if og else None) \
               or "?"
        if not name or name == "?":
            return None

        # path parts
        parts = [s for s in urlparse(url).path.strip("/").split("/") if s]
        # /en/products/<category>/<...>
        category_slug = parts[2] if len(parts) >= 3 else ""
        product_slug = parts[-1]
        model = product_slug

        # group: красивое название категории
        group = category_slug.replace("-", " ").title() if category_slug else None

        # description
        desc_meta = tree.css_first("meta[name='description']") \
                     or tree.css_first("meta[property='og:description']")
        description = (desc_meta.attrs.get("content", "").strip() if desc_meta else "") or ""

        # vendor_code — Sartorius иногда показывает "Order Code" / "Product Code" / "Part Number"
        body_text = tree.css_first("body").text(separator=" ") if tree.css_first("body") else ""
        vendor_code = ""
        for pat in (
            r"Order\s*(?:Code|No\.?|Number)\s*:?\s*([A-Z0-9\-\._]{4,30})",
            r"Part\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9\-\._]{4,30})",
            r"Product\s*(?:Code|No\.?|Number)\s*:?\s*([A-Z0-9\-\._]{4,30})",
            r"Cat\.?\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9\-\._]{4,30})",
        ):
            m = re.search(pat, body_text)
            if m:
                vendor_code = m.group(1)
                break

        # specs — table-based
        specs: dict[str, str] = {}
        for table in tree.css("table"):
            for tr in table.css("tr"):
                cells = tr.css("td, th")
                if len(cells) == 2:
                    k = cells[0].text(strip=True)
                    v = cells[1].text(strip=True)
                    if k and v and len(k) < 100 and len(v) < 400:
                        specs[k] = v
        # dl-based
        for dl in tree.css("dl"):
            dts = dl.css("dt")
            dds = dl.css("dd")
            for dt, dd in zip(dts, dds):
                k = dt.text(strip=True)
                v = dd.text(strip=True)
                if k and v:
                    specs[k] = v

        # PDF links
        pdf_urls: list[str] = []
        for a in tree.css("a[href]"):
            href = a.attrs.get("href", "")
            full = urljoin(url, href).split("#")[0]
            low = full.lower()
            txt = a.text(strip=True).lower()
            if (".pdf" in low) and any(k in (low + " " + txt) for k in (
                "datasheet", "data-sheet", "brochure", "specification",
                "spec_sheet", "product-information", "fact-sheet",
                model.lower()
            )):
                pdf_urls.append(full)
        pdf_urls = list(dict.fromkeys(pdf_urls))[:3]

        # images
        images: list[str] = []
        for img in tree.css("img"):
            src = img.attrs.get("src") or img.attrs.get("data-src", "")
            if src and "sartorius" in src and not src.endswith(".svg"):
                full = urljoin(url, src)
                if any(kw in full for kw in ("product", "image", "media")):
                    images.append(full)
        images = list(dict.fromkeys(images))[:5]

        # markdown fallback
        description_md = None
        if not pdf_urls or len(specs) >= 3:
            md = [
                f"# {name}",
                "",
                f"**Производитель:** {self.brand_name}",
                f"**Модель:** {model}",
                f"**Группа:** {group or '?'}",
                f"**Артикул:** {vendor_code or '—'}",
                f"**Источник:** {url}",
                "",
            ]
            if description:
                md += [description, ""]
            if specs:
                md += ["## Технические характеристики", ""]
                for k, v in list(specs.items())[:40]:
                    md.append(f"- **{k}:** {v}")
            description_md = "\n".join(md)

        return VendorProductData(
            vendor_code=vendor_code,
            name=name[:500],
            model=model[:200],
            group=(group or "")[:120],
            description_md=description_md,
            pdf_urls=pdf_urls,
            image_urls=images,
            specs=specs,
            source_url=url,
            raw_metadata={
                "category_slug": category_slug,
                "url_depth": len(parts),
            },
        )

    def _guess_category(self, data: VendorProductData) -> str:
        cat = data.raw_metadata.get("category_slug", "")
        if cat in self.CATEGORY_MAP:
            return self.CATEGORY_MAP[cat]
        # heuristic
        g = (data.group or "").lower()
        if "balance" in g or "weighing" in g:
            return "balance"
        if "filter" in g or "filtration" in g:
            return "syringe_filter"
        if "water" in g and "purification" in g:
            return "water_purifier"
        if "pipett" in g:
            return "consumable"
        return "other"
