"""Postgres-слой бота (asyncpg). Read-only access к таблице product."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import asyncpg

from .settings import Settings


# ---------- модели ----------
@dataclass
class Product:
    id: UUID
    brand: str
    model: str
    vendor_code: str | None
    display_name: str
    category: str
    domain: str
    subcategory: str | None
    description: str | None
    datasheet_paths: list[str]
    source_urls: list[str]
    ru_number: str | None
    ru_status: str
    imported_from: str | None

    @property
    def pdf_count(self) -> int:
        return len(self.datasheet_paths or [])


@dataclass
class BrandCount:
    brand: str
    total: int
    with_ds: int
    with_ru: int


@dataclass
class CategoryCount:
    category: str
    total: int


# ---------- pool ----------
class DB:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            dsn=self._settings.pg_dsn,
            min_size=2,
            max_size=8,
            command_timeout=30,
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()

    async def fetch(self, sql: str, *args) -> list[asyncpg.Record]:
        assert self._pool is not None
        return await self._pool.fetch(sql, *args)

    async def fetchrow(self, sql: str, *args) -> asyncpg.Record | None:
        assert self._pool is not None
        return await self._pool.fetchrow(sql, *args)

    # ---------- statistics ----------
    async def brand_counts(self, top: int = 30) -> list[BrandCount]:
        rows = await self.fetch(
            """
            SELECT
              brand,
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE array_length(datasheet_paths, 1) > 0) AS with_ds,
              COUNT(*) FILTER (WHERE ru_status = 'active') AS with_ru
            FROM product
            WHERE brand IS NOT NULL AND brand <> ''
            GROUP BY brand
            ORDER BY total DESC
            LIMIT $1
            """,
            top,
        )
        return [BrandCount(brand=r["brand"], total=r["total"],
                           with_ds=r["with_ds"], with_ru=r["with_ru"]) for r in rows]

    async def category_counts(self, brand: str | None = None) -> list[CategoryCount]:
        if brand:
            rows = await self.fetch(
                """
                SELECT category::text AS category, COUNT(*) AS total
                FROM product WHERE brand = $1
                GROUP BY category ORDER BY total DESC
                """,
                brand,
            )
        else:
            rows = await self.fetch(
                """
                SELECT category::text AS category, COUNT(*) AS total
                FROM product GROUP BY category ORDER BY total DESC
                """
            )
        return [CategoryCount(category=r["category"], total=r["total"]) for r in rows]

    async def totals(self) -> dict[str, int]:
        row = await self.fetchrow(
            """
            SELECT
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE array_length(datasheet_paths, 1) > 0) AS with_ds,
              COUNT(DISTINCT brand) AS brands,
              COUNT(*) FILTER (WHERE imported_from = 'agilent_sitemap') AS agilent_stubs,
              (SELECT COALESCE(SUM(array_length(datasheet_paths, 1)), 0) FROM product) AS total_pdfs
            FROM product
            """
        )
        return dict(row)

    # ---------- search ----------
    async def search_products(
        self,
        *,
        brand: str | None = None,
        category: str | None = None,
        keywords: list[str] | None = None,
        has_pdf: bool | None = None,
        has_ru: bool | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[Product]:
        clauses: list[str] = []
        args: list[Any] = []

        def add(cond: str, val: Any) -> None:
            args.append(val)
            clauses.append(cond.format(idx=len(args)))

        if brand:
            # case-insensitive partial match по brand
            add("LOWER(brand) LIKE LOWER(${idx})", f"%{brand}%")

        if category:
            # category — это enum; матчим по text-cast
            add("category::text = ${idx}", category)

        if keywords:
            # каждый keyword — должен встретиться в display_name OR model OR subcategory OR description
            for kw in keywords:
                pat = f"%{kw.lower()}%"
                add(
                    "(LOWER(display_name) LIKE ${idx} "
                    "OR LOWER(model) LIKE ${idx} "
                    "OR LOWER(COALESCE(subcategory,'')) LIKE ${idx} "
                    "OR LOWER(COALESCE(description,'')) LIKE ${idx})",
                    pat,
                )

        if has_pdf is True:
            clauses.append("array_length(datasheet_paths, 1) > 0")
        elif has_pdf is False:
            clauses.append("(datasheet_paths IS NULL OR array_length(datasheet_paths, 1) = 0)")

        if has_ru is True:
            clauses.append("ru_status = 'active'")
        elif has_ru is False:
            clauses.append("ru_status <> 'active'")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = (
            "SELECT id, brand, model, vendor_code, display_name, category::text AS category, "
            "domain::text AS domain, subcategory, description, "
            "COALESCE(datasheet_paths, ARRAY[]::text[]) AS datasheet_paths, "
            "COALESCE(source_urls, ARRAY[]::text[]) AS source_urls, "
            "ru_number, ru_status::text AS ru_status, imported_from "
            f"FROM product {where} "
            "ORDER BY (array_length(datasheet_paths, 1) IS NOT NULL) DESC, brand, model "
            f"LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}"
        )
        args += [limit, offset]
        rows = await self.fetch(sql, *args)
        return [self._row_to_product(r) for r in rows]

    async def search_count(
        self,
        *,
        brand: str | None = None,
        category: str | None = None,
        keywords: list[str] | None = None,
        has_pdf: bool | None = None,
        has_ru: bool | None = None,
    ) -> int:
        # повторяем условия search_products но для COUNT(*)
        clauses: list[str] = []
        args: list[Any] = []

        def add(cond: str, val: Any) -> None:
            args.append(val)
            clauses.append(cond.format(idx=len(args)))

        if brand:
            add("LOWER(brand) LIKE LOWER(${idx})", f"%{brand}%")
        if category:
            add("category::text = ${idx}", category)
        if keywords:
            for kw in keywords:
                pat = f"%{kw.lower()}%"
                add(
                    "(LOWER(display_name) LIKE ${idx} "
                    "OR LOWER(model) LIKE ${idx} "
                    "OR LOWER(COALESCE(subcategory,'')) LIKE ${idx} "
                    "OR LOWER(COALESCE(description,'')) LIKE ${idx})",
                    pat,
                )
        if has_pdf is True:
            clauses.append("array_length(datasheet_paths, 1) > 0")
        elif has_pdf is False:
            clauses.append("(datasheet_paths IS NULL OR array_length(datasheet_paths, 1) = 0)")
        if has_ru is True:
            clauses.append("ru_status = 'active'")
        elif has_ru is False:
            clauses.append("ru_status <> 'active'")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT COUNT(*) AS n FROM product {where}"
        row = await self.fetchrow(sql, *args)
        return int(row["n"]) if row else 0

    async def get_product(self, product_id: UUID) -> Product | None:
        row = await self.fetchrow(
            """
            SELECT id, brand, model, vendor_code, display_name, category::text AS category,
                   domain::text AS domain, subcategory, description,
                   COALESCE(datasheet_paths, ARRAY[]::text[]) AS datasheet_paths,
                   COALESCE(source_urls, ARRAY[]::text[]) AS source_urls,
                   ru_number, ru_status::text AS ru_status, imported_from
            FROM product WHERE id = $1
            """,
            product_id,
        )
        return self._row_to_product(row) if row else None

    @staticmethod
    def _row_to_product(r: asyncpg.Record) -> Product:
        return Product(
            id=r["id"],
            brand=r["brand"],
            model=r["model"],
            vendor_code=r["vendor_code"],
            display_name=r["display_name"],
            category=r["category"],
            domain=r["domain"],
            subcategory=r["subcategory"],
            description=r["description"],
            datasheet_paths=list(r["datasheet_paths"] or []),
            source_urls=list(r["source_urls"] or []),
            ru_number=r["ru_number"],
            ru_status=r["ru_status"],
            imported_from=r["imported_from"],
        )
