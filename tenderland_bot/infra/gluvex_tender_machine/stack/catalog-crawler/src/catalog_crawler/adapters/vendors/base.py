"""VendorAdapter — базовый класс для парсера одного производителя.

Контракт:
  • adapter знает URL'ы карточек товаров своего бренда (sitemap или индекс)
  • для каждой карточки: vendor_code, model, group, description_md / pdf_url
  • base class сохраняет PDF/MD в MinIO, INSERT/UPDATE в product, audit_event

Структура данных в БД (одинаковая для всех брендов):
  producer    = product.brand
  group       = product.subcategory  (линейка / категория с сайта производителя)
  product     = product.display_name + .model
  артикул     = product.vendor_code
  brochure    = product.datasheet_paths[]  (MinIO путь)
  description = MinIO .md файл если PDF нет
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urljoin, urlparse

import asyncpg
import httpx
from selectolax.parser import HTMLParser

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.fetcher import Fetcher
from catalog_crawler.core.storage import put_object
from catalog_crawler.settings import Settings


@dataclass
class VendorProductData:
    """Стандартизированные данные карточки товара от вендора."""
    vendor_code: str
    name: str
    model: str
    group: str | None = None              # линейка / категория с сайта
    description_md: str | None = None     # markdown с techinfo если PDF нет
    pdf_urls: list[str] = field(default_factory=list)
    image_urls: list[str] = field(default_factory=list)
    specs: dict[str, str] = field(default_factory=dict)
    source_url: str = ""
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class VendorAdapter(ABC):
    """Базовый класс per-brand crawler."""

    brand_name: str      # "Agilent Technologies"
    brand_slug: str      # "agilent" — для file paths
    base_url: str        # "https://www.agilent.com"
    domain_hint: str = "general_lab"   # product_domain_t default
    user_agent_override: str | None = None  # если бренду нужен специфический UA

    # rate limit per-vendor, sec между запросами; base 0.7s = ~1.5 RPS
    rate_limit_seconds: float = 0.7

    def __init__(self, settings: Settings):
        self.settings = settings
        self._tenant_id = "11111111-1111-1111-1111-111111111111"

    # ---------- abstract — каждый бренд реализует ----------
    @abstractmethod
    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        """Возвращает список URL карточек товаров для этого бренда."""
        ...

    @abstractmethod
    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        """Парсит одну страницу товара. None если страница не товар."""
        ...

    # ---------- общая логика ----------
    async def run(self, limit: int = 0, skip_existing_fresh_days: int = 30) -> dict[str, Any]:
        """Полный цикл: list_urls → parse_product → save.

        Args:
          limit: ограничить число товаров (0 = все).
          skip_existing_fresh_days: если товар обновлялся менее N дней назад — пропускаем.
        """
        print(f"==> {self.brand_name}: starting crawl")
        print(f"    base URL: {self.base_url}")
        print(f"    rate limit: {self.rate_limit_seconds}s/request")
        if self.user_agent_override:
            print(f"    UA override: {self.user_agent_override[:60]}...")

        async with Fetcher(user_agent=self.user_agent_override) as fetcher:
            # 1. список URL
            urls = await self.list_product_urls(fetcher, limit=limit)
            print(f"    product URLs: {len(urls)}")
            if limit and limit > 0:
                urls = urls[:limit]
                print(f"    limited to: {len(urls)}")

            # 2. fetch + parse + save
            stats = {
                "vendor": self.brand_name,
                "total": len(urls),
                "ok": 0,
                "errors": 0,
                "with_pdf": 0,
                "with_description_md": 0,
                "matched_existing": 0,
                "created_new": 0,
                "skipped_fresh": 0,
            }

            conn: asyncpg.Connection = await get_conn()
            try:
                for i, url in enumerate(urls, 1):
                    try:
                        # skip if recently updated
                        if skip_existing_fresh_days > 0:
                            existing = await conn.fetchrow("""
                                SELECT id, updated_at FROM product
                                WHERE brand = $1 AND source_urls @> ARRAY[$2]::text[]
                                AND updated_at > now() - ($3 || ' days')::interval
                                LIMIT 1
                            """, self.brand_name, url, str(skip_existing_fresh_days))
                            if existing:
                                stats["skipped_fresh"] += 1
                                continue

                        html = await fetcher.get(url)
                        data = await self.parse_product(url, html)
                        if data is None:
                            continue

                        # 3. сохраняем PDF и/или markdown в MinIO
                        minio_paths: list[str] = []
                        if data.pdf_urls:
                            for pdf_url in data.pdf_urls[:3]:  # max 3 PDF
                                try:
                                    saved = await self._download_and_save_pdf(
                                        fetcher, pdf_url, data.vendor_code
                                    )
                                    if saved:
                                        minio_paths.append(saved)
                                        stats["with_pdf"] += 1
                                except Exception as e:
                                    print(f"      pdf {pdf_url}: {e}")

                        if not minio_paths and data.description_md:
                            saved = self._save_markdown(data)
                            if saved:
                                minio_paths.append(saved)
                                stats["with_description_md"] += 1

                        # 4. upsert в product
                        was_new = await self._upsert_product(conn, data, url, minio_paths)
                        if was_new:
                            stats["created_new"] += 1
                        else:
                            stats["matched_existing"] += 1

                        stats["ok"] += 1
                        if i <= 5 or i % 50 == 0 or i == len(urls):
                            print(f"  [{i:>5}/{len(urls)}] {data.vendor_code:20s} {data.model[:50]}")

                    except Exception as e:
                        stats["errors"] += 1
                        print(f"  [{i:>5}] ERROR {url}: {e}")

            finally:
                await conn.close()

        await audit_event(
            action=f"vendor_crawl_complete:{self.brand_slug}",
            payload=stats,
        )

        # summary
        print(f"\n==> SUMMARY {self.brand_name}")
        for k, v in stats.items():
            print(f"    {k}: {v}")
        return stats

    # ---------- helpers (общие для всех брендов) ----------
    async def _download_and_save_pdf(
        self, fetcher: Fetcher, pdf_url: str, vendor_code: str
    ) -> str | None:
        """Скачивает PDF и кладёт в MinIO bucket product-brochures."""
        # отдельный httpx — PDF может быть бинарным
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
            await asyncio.sleep(self.rate_limit_seconds)
            r = await c.get(pdf_url, headers={"User-Agent": self.settings.user_agent})
            if r.status_code != 200:
                return None
            content_type = r.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not pdf_url.lower().endswith(".pdf"):
                return None
            content = r.content
            content_hash = hashlib.sha256(content).hexdigest()[:16]
            slug = re.sub(r"[^a-zA-Z0-9-]", "_", vendor_code)[:80] or "noname"
            key = f"{self.brand_slug}/{slug}_{content_hash}.pdf"
            location = put_object(
                self.settings.minio_brochures_bucket,
                key,
                content,
                content_type="application/pdf",
            )
            return location

    def _save_markdown(self, data: VendorProductData) -> str | None:
        """Когда PDF нет — сохраняем technical info из data.description_md в MinIO."""
        if not data.description_md:
            return None
        body = data.description_md.encode("utf-8")
        content_hash = hashlib.sha256(body).hexdigest()[:16]
        slug = re.sub(r"[^a-zA-Z0-9-]", "_", data.vendor_code)[:80] or "noname"
        key = f"{self.brand_slug}/{slug}_{content_hash}.md"
        return put_object(
            self.settings.minio_brochures_bucket,
            key,
            body,
            content_type="text/markdown; charset=utf-8",
        )

    async def _upsert_product(
        self,
        conn: asyncpg.Connection,
        data: VendorProductData,
        url: str,
        minio_paths: list[str],
    ) -> bool:
        """INSERT or UPDATE в product. Возвращает True если создан новый."""
        # category берём из подсказки или 'other' — adapter может переопределить логику
        category = self._guess_category(data)
        domain = self.domain_hint

        # пытаемся найти существующий product по brand+vendor_code (приоритет) или brand+model
        existing = None
        if data.vendor_code:
            existing = await conn.fetchrow("""
                SELECT id FROM product WHERE brand=$1 AND vendor_code=$2 LIMIT 1
            """, self.brand_name, data.vendor_code)
        if existing is None:
            existing = await conn.fetchrow("""
                SELECT id FROM product WHERE brand=$1 AND model=$2 LIMIT 1
            """, self.brand_name, data.model[:200])

        content_hash = hashlib.sha256(
            f"{data.vendor_code}|{data.model}|{data.description_md or ''}".encode("utf-8")
        ).digest()

        if existing:
            # UPDATE — дополняем данными от производителя
            # nullable-friendly: пустые строки превращаем в NULL для skip
            v_vendor = data.vendor_code if data.vendor_code else None
            v_name = data.name[:500] if data.name else None
            v_desc = (data.description_md or "")[:5000] if data.description_md else None
            v_group = (data.group or "")[:120] if data.group else None
            await conn.execute("""
                UPDATE product SET
                  vendor_code     = COALESCE($2, vendor_code),
                  display_name    = COALESCE($3, display_name),
                  description     = COALESCE($4, description),
                  subcategory     = COALESCE($5, subcategory),
                  base_specs      = COALESCE(base_specs, '{}'::jsonb) || $6::jsonb,
                  source_urls     = (
                    SELECT array_agg(DISTINCT u)
                    FROM unnest(coalesce(source_urls, ARRAY[]::text[]) || ARRAY[$7]::text[]) AS u
                  ),
                  datasheet_paths = (
                    SELECT array_agg(DISTINCT p)
                    FROM unnest(coalesce(datasheet_paths, ARRAY[]::text[]) || $8::text[]) AS p
                  ),
                  brochure_urls   = (
                    SELECT array_agg(DISTINCT u)
                    FROM unnest(coalesce(brochure_urls, ARRAY[]::text[]) || $9::text[]) AS u
                  ),
                  metadata        = coalesce(metadata, '{}'::jsonb) || $10::jsonb,
                  content_hash    = $11,
                  imported_at     = now(),
                  imported_from   = $12,
                  updated_at      = now()
                WHERE id = $1
            """,
                existing["id"],
                v_vendor, v_name, v_desc, v_group,
                json.dumps(data.specs),
                url,
                minio_paths,
                data.pdf_urls,
                json.dumps({
                    "vendor_images": data.image_urls,
                    "vendor_raw": data.raw_metadata,
                }),
                content_hash,
                self.brand_slug,
            )
            return False
        else:
            # INSERT
            await conn.execute("""
                INSERT INTO product (
                  tenant_id, brand, model, vendor_code, category, domain,
                  display_name, description, subcategory,
                  base_specs, source_urls, datasheet_paths, brochure_urls,
                  metadata, content_hash, imported_at, imported_from
                )
                VALUES ($1, $2, $3, $4, $5::product_category_t, $6::product_domain_t,
                        $7, $8, $9,
                        $10::jsonb, $11::text[], $12::text[], $13::text[],
                        $14::jsonb, $15, now(), $16)
                ON CONFLICT (tenant_id, brand, model) DO NOTHING
            """,
                self._tenant_id,
                self.brand_name,
                data.model[:200],
                data.vendor_code or None,
                category, domain,
                data.name[:500],
                (data.description_md or "")[:5000] if data.description_md else None,
                (data.group or "")[:120] or None,
                json.dumps(data.specs),
                [url],
                minio_paths,
                data.pdf_urls,
                json.dumps({
                    "vendor_images": data.image_urls,
                    "vendor_raw": data.raw_metadata,
                }),
                content_hash,
                self.brand_slug,
            )
            return True

    def _guess_category(self, data: VendorProductData) -> str:
        """Default — 'other'. Subclass может override."""
        return "other"
