"""GenericVendorAdapter — универсальный для брендов с простой структурой.

Подходит для большинства небольших вендоров общелабораторного оборудования:
  - вход через 1-2 точки (главный каталог)
  - product pages имеют <h1> с названием
  - PDF datasheets через <a href*='.pdf'>
  - specs в <table> или <dl>

Использование:
    adapter = GenericVendorAdapter(
        settings,
        brand_name="SOTAX",
        brand_slug="sotax",
        base_url="https://www.sotax.com",
        entry_urls=["https://www.sotax.com/products/"],
        category_keyword_map={"dissolution": "accessory", "tablet": "accessory"},
        domain_hint="pharmaceutical",
        max_depth=4,
    )
    await adapter.run()
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.fetcher import Fetcher
from catalog_crawler.settings import Settings


class GenericVendorAdapter(VendorAdapter):
    """Универсальный adapter для брендов с открытой простой структурой."""

    def __init__(
        self,
        settings: Settings,
        *,
        brand_name: str,
        brand_slug: str,
        base_url: str,
        entry_urls: list[str],
        category_keyword_map: dict[str, str] | None = None,
        domain_hint: str = "general_lab",
        default_category: str = "other",
        max_depth: int = 4,
        max_urls: int = 500,
        url_must_contain: list[str] | None = None,
        url_must_not_contain: list[str] | None = None,
        user_agent_override: str | None = None,
        rate_limit_seconds: float = 0.7,
    ):
        super().__init__(settings)
        # инстанс-переменные override class-attributes
        self.brand_name = brand_name
        self.brand_slug = brand_slug
        self.base_url = base_url
        self.entry_urls = entry_urls
        self.category_keyword_map = category_keyword_map or {}
        self.domain_hint = domain_hint
        self.default_category = default_category
        self.max_depth = max_depth
        self.max_urls = max_urls
        # фильтры на URL пути: must_contain — минимум одно из, must_not_contain — ни одно
        self.url_must_contain = url_must_contain or ["/product"]
        self.url_must_not_contain = url_must_not_contain or [
            "/news", "/career", "/contact", "/about", "/legal",
            "/imprint", "/privacy", "/login", "/cart", "/checkout",
            "/blog", "/event", "/service/contact", "/resources/library",
            "/applications", "/calculator", "/whitepaper", "/webinar",
            # multilingual locale paths — пропускаем всё кроме явно разрешённого entry
            "/es/", "/fr/", "/de/", "/it/", "/jp/", "/zh/", "/ru/",
            "/cn/", "/kr/", "/br/", "/pl/",
            "/america/", "/dach/", "/asia/", "/india/",
            "/productos/", "/produits/", "/prodotti/", "/produkte/",
        ]
        self.user_agent_override = user_agent_override
        self.rate_limit_seconds = rate_limit_seconds

    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        """BFS по сайту от entry_urls, ограниченный max_depth/max_urls."""
        found: set[str] = set()
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(u, 0) for u in self.entry_urls]
        host = urlparse(self.base_url).netloc

        while queue and len(found) < self.max_urls:
            url, depth = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if depth > self.max_depth:
                continue

            try:
                html = await fetcher.get(url)
            except Exception as e:
                print(f"  list[d{depth}] FAIL {url}: {e}")
                continue

            tree = HTMLParser(html)
            for a in tree.css("a[href]"):
                href = a.attrs.get("href", "")
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                full = urljoin(url, href).split("#")[0]
                p = urlparse(full)
                # remove query string for dedup (некоторые TYPO3 / WP добавляют tracking)
                full_no_q = f"{p.scheme}://{p.netloc}{p.path}"
                if p.netloc and p.netloc != host:
                    continue
                path_lower = p.path.lower()
                if any(s in path_lower for s in self.url_must_not_contain):
                    continue
                if self.url_must_contain and not any(s in path_lower for s in self.url_must_contain):
                    continue
                if full_no_q in found or full_no_q in visited:
                    continue

                # depth подсчёт
                parts = [s for s in p.path.strip("/").split("/") if s]
                # эвристика — страница "продукта" обычно на depth 3+
                if len(parts) >= 3:
                    found.add(full_no_q)
                else:
                    queue.append((full_no_q, depth + 1))

                if limit and len(found) >= limit * 2:
                    break

        urls = sorted(found)
        print(f"  list: found {len(urls)} product URLs (visited {len(visited)} pages, max_depth {self.max_depth})")
        return urls

    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        tree = HTMLParser(html)

        # name
        h1 = tree.css_first("h1")
        og = tree.css_first("meta[property='og:title']")
        name = ""
        if h1 and h1.text(strip=True):
            name = h1.text(strip=True)
        elif og and og.attrs.get("content"):
            name = og.attrs["content"].strip()
        if not name or len(name) < 3:
            return None

        # model
        parts = [s for s in urlparse(url).path.strip("/").split("/") if s]
        product_slug = parts[-1] if parts else "unknown"
        category_slug = parts[-2] if len(parts) >= 2 else ""
        group = category_slug.replace("-", " ").replace("_", " ").title() if category_slug else None
        model = product_slug

        # description
        desc_meta = tree.css_first("meta[name='description']") \
                     or tree.css_first("meta[property='og:description']")
        description = ""
        if desc_meta:
            content = desc_meta.attrs.get("content", "")
            if content:
                description = content.strip()

        # vendor_code (best-effort)
        body_text = ""
        body = tree.css_first("body")
        if body:
            body_text = body.text(separator=" ")[:8000]  # limit для performance
        vendor_code = ""
        for pat in (
            r"(?:Order\s*(?:Code|No\.?|Number)|Part\s*No\.?|Cat\.?\s*No\.?|Article\s*No\.?|SKU|Product\s*Code)\s*:?\s*([A-Z0-9][A-Z0-9\-\._/]{2,29})",
        ):
            m = re.search(pat, body_text)
            if m:
                vendor_code = m.group(1)
                break

        # specs (table + dl)
        specs: dict[str, str] = {}
        for table in tree.css("table"):
            for tr in table.css("tr"):
                cells = tr.css("td, th")
                if len(cells) == 2:
                    k = cells[0].text(strip=True)
                    v = cells[1].text(strip=True)
                    if k and v and len(k) < 100 and len(v) < 400:
                        specs[k] = v
        for dl in tree.css("dl"):
            for dt, dd in zip(dl.css("dt"), dl.css("dd")):
                k = (dt.text(strip=True) or "")
                v = (dd.text(strip=True) or "")
                if k and v:
                    specs[k] = v
        if len(specs) > 50:
            specs = dict(list(specs.items())[:50])

        # PDF
        pdf_urls: list[str] = []
        for a in tree.css("a[href]"):
            href = a.attrs.get("href", "")
            if not href:
                continue
            full = urljoin(url, href).split("#")[0]
            low = full.lower()
            txt = (a.text(strip=True) or "").lower()
            if ".pdf" in low:
                if any(k in (low + " " + txt) for k in (
                    "datasheet", "data-sheet", "brochure", "manual",
                    "specification", "spec_sheet", "product-info", "fact-sheet",
                    model.lower()[:20],
                )):
                    pdf_urls.append(full)
        pdf_urls = list(dict.fromkeys(pdf_urls))[:3]

        # images
        images: list[str] = []
        host = urlparse(self.base_url).netloc
        for img in tree.css("img"):
            src = img.attrs.get("src") or img.attrs.get("data-src") or ""
            if not src:
                continue
            full = urljoin(url, src)
            if not full.lower().endswith((".svg", ".gif", ".ico")) and host in full:
                images.append(full)
        images = list(dict.fromkeys(images))[:5]

        # markdown
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
                "product_slug": product_slug,
            },
        )

    def _guess_category(self, data: VendorProductData) -> str:
        text = " ".join([
            (data.group or "").lower(),
            data.raw_metadata.get("category_slug", "").lower(),
            data.raw_metadata.get("product_slug", "").lower(),
            data.model.lower(),
        ])
        # keyword-based mapping (приоритет — длинные ключи)
        for kw, cat in sorted(self.category_keyword_map.items(), key=lambda x: -len(x[0])):
            if kw.lower() in text:
                return cat
        return self.default_category
