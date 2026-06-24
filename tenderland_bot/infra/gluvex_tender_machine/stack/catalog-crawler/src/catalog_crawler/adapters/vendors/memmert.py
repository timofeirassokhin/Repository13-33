"""Memmert official site adapter.

Сайт memmert.com — открытый, простой HTML, без anti-bot.
8 категорий под /en/products/<category>/ + подкатегории + страницы конкретных моделей.

URL pattern:
  /en/products/heating-drying-ovens/heating-oven/UN30/  — конкретная модель
  /en/products/incubators/co2-incubators/              — подкатегория со списком
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from selectolax.parser import HTMLParser

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.fetcher import Fetcher


class MemmertAdapter(VendorAdapter):
    brand_name = "Memmert"
    brand_slug = "memmert"
    base_url = "https://www.memmert.com"
    domain_hint = "general_lab"
    rate_limit_seconds = 0.7

    # 8 верхнеуровневых категорий
    TOP_CATEGORIES = [
        ("climate-chambers",         "climate_chamber",            "Climate chambers"),
        ("heating-drying-ovens",     "drying_oven",                "Heating & drying ovens"),
        ("incubators",               "incubator",                  "Incubators"),
        ("ult-freezers",             "climate_chamber",            "ULT freezers"),
        ("water-baths",              "drying_oven",                "Water baths"),
        ("medical-devices",          "incubator",                  "Medical devices"),
    ]
    # для CSV-маппинга: первый — slug URL, второй — наш product_category_t

    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        """Memmert structure (TYPO3):
          /en/products/<category>/              — листинг series (например /incubators/)
          /en/products/<category>/<series>      — страница серии (UN, ICO, UF...) — это наш product

        Конкретные модели (UN30/UN55/UN75/etc) представлены на странице series,
        отдельных URL для каждой модели нет (TYPO3 series view).
        Стратегия: 1 проход по category pages, забираем series-level URL.
        """
        all_urls: set[str] = set()

        for cat_slug, _, _ in self.TOP_CATEGORIES:
            cat_url = f"{self.base_url}/en/products/{cat_slug}/"
            try:
                html = await fetcher.get(cat_url)
            except Exception as e:
                print(f"  list: failed {cat_url}: {e}")
                continue

            tree = HTMLParser(html)
            for a in tree.css("a[href]"):
                href = a.attrs.get("href", "")
                if not href or href.startswith(("#", "javascript:", "mailto:")):
                    continue
                full = urljoin(cat_url, href)
                p = urlparse(full)
                if p.netloc and p.netloc != urlparse(self.base_url).netloc:
                    continue
                if "?" in full:
                    continue  # skip TYPO3 query-string URL-ы — там cHash, 404
                parts = [s for s in p.path.strip("/").split("/") if s]
                # series URL: /en/products/<category>/<series>  (ровно 4 сегмента: en, products, cat, series)
                if (
                    len(parts) == 4
                    and parts[0] == "en"
                    and parts[1] == "products"
                    and parts[2] == cat_slug
                ):
                    all_urls.add(full)

        urls = sorted(all_urls)
        print(f"  list: found {len(urls)} series URLs across {len(self.TOP_CATEGORIES)} categories")
        return urls

    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        tree = HTMLParser(html)

        # name — H1 или og:title
        h1 = tree.css_first("h1")
        og = tree.css_first("meta[property='og:title']")
        name = (h1.text(strip=True) if h1 else None) \
               or (og.attrs.get("content", "").strip() if og else None) \
               or "?"

        # series-name — последний сегмент URL ('co2-incubator-ico', 'universal-oven', ...)
        parts = [s for s in urlparse(url).path.strip("/").split("/") if s]
        series_slug = parts[-1] if parts else "unknown"
        # model = это серия (UN/UF/ICO/IPP/SF...) — берём из URL slug, нормализуем
        model = series_slug
        # group — категория верхнего уровня
        category_slug = parts[-2] if len(parts) >= 2 else None
        group = (category_slug or "").replace("-", " ").title()

        # vendor_code пустой на series-level (там много models внутри)
        # модели типа UN30/UN55 будут в product_configuration отдельной итерацией
        vendor_code = ""

        # Извлекаем все упоминания моделей со страницы (UN30, UF55plus, ICO50, etc)
        body_text = tree.css_first("body").text(separator=" ") if tree.css_first("body") else ""
        models_on_page = sorted(set(re.findall(r"\b[A-Z]{2,4}\d{2,4}[A-Za-z]*\b", body_text)))[:30]

        # description — meta description или первый <p>
        desc_meta = tree.css_first("meta[name='description']") or tree.css_first("meta[property='og:description']")
        description = (desc_meta.attrs.get("content", "").strip() if desc_meta else "") or ""

        # ищем technical data — обычно в <table>, <dl> или div с classом "tech-data"
        specs: dict[str, str] = {}
        for table in tree.css("table"):
            for tr in table.css("tr"):
                cells = tr.css("td, th")
                if len(cells) == 2:
                    k = cells[0].text(strip=True)
                    v = cells[1].text(strip=True)
                    if k and v and len(k) < 100 and len(v) < 300:
                        specs[k] = v

        # PDF datasheet links
        pdf_urls: list[str] = []
        for a in tree.css("a[href]"):
            href = a.attrs.get("href", "")
            full = urljoin(url, href)
            if full.lower().endswith(".pdf") or ".pdf?" in full.lower():
                # фильтруем — нас интересуют брошюры/datasheet'ы, не каталоги/cookies
                txt = a.text(strip=True).lower()
                if any(k in (full.lower() + txt) for k in ("datasheet", "data-sheet", "brochure", "specification", "spec_sheet", model.lower())):
                    pdf_urls.append(full)
                elif "downloads" in full.lower():
                    pdf_urls.append(full)
        pdf_urls = list(dict.fromkeys(pdf_urls))[:3]

        # изображения
        images: list[str] = []
        for img in tree.css("img"):
            src = img.attrs.get("src") or img.attrs.get("data-src", "")
            if src and not src.endswith(".svg"):
                full = urljoin(url, src)
                if "memmert" in full and any(kw in full for kw in ("product", "model", "media", "images")):
                    images.append(full)
        images = list(dict.fromkeys(images))[:5]

        # description_md — если PDF не нашли, сохраняем технические данные в markdown
        description_md = None
        if not pdf_urls or len(specs) >= 3:
            md_lines = [
                f"# {name}",
                f"",
                f"**Производитель:** {self.brand_name}",
                f"**Модель:** {model}",
                f"**Группа:** {group}",
                f"**Артикул:** {vendor_code}",
                f"**Источник:** {url}",
                "",
            ]
            if description:
                md_lines += [description, ""]
            if specs:
                md_lines += ["## Технические характеристики", ""]
                for k, v in specs.items():
                    md_lines.append(f"- **{k}:** {v}")
            description_md = "\n".join(md_lines)

        return VendorProductData(
            vendor_code=vendor_code,
            name=name[:500],
            model=model[:200],
            group=group[:120] if group else None,
            description_md=description_md,
            pdf_urls=pdf_urls,
            image_urls=images,
            specs=specs,
            source_url=url,
            raw_metadata={
                "category_slug": category_slug,
                "series_slug": series_slug,
                "models_on_page": models_on_page,
            },
        )

    def _guess_category(self, data: VendorProductData) -> str:
        # маппинг по верхнеуровневому slug
        cat = data.raw_metadata.get("category_slug", "")
        for slug, product_cat, _ in self.TOP_CATEGORIES:
            if cat == slug:
                return product_cat
        # fallback по тексту названия группы
        g = (data.group or "").lower()
        if "climate" in g or "freezer" in g or "humidity" in g:
            return "climate_chamber"
        if "incubator" in g or "co2" in g:
            return "incubator"
        if "oven" in g or "heating" in g or "drying" in g:
            return "drying_oven"
        if "bath" in g:
            return "drying_oven"
        return "other"
