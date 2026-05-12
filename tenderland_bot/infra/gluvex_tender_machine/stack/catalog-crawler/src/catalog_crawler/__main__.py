"""CLI entrypoint:

  python -m catalog_crawler gluvexlab structure   # парсит sitemap → JSON dump в MinIO
  python -m catalog_crawler gluvexlab products    # парсит детальные карточки → product таблица
"""
from __future__ import annotations

import asyncio
import sys

import typer

from catalog_crawler.adapters.gluvexlab import GluvexLabAdapter
from catalog_crawler.settings import settings


app = typer.Typer(no_args_is_help=True, add_completion=False)
gluvex_app = typer.Typer(no_args_is_help=True)
app.add_typer(gluvex_app, name="gluvexlab")

vendor_app = typer.Typer(no_args_is_help=True)
app.add_typer(vendor_app, name="vendor")


@vendor_app.command("memmert")
def vendor_memmert(
    limit: int = typer.Option(0, help="Ограничить число моделей (0 = все)"),
    skip_fresh_days: int = typer.Option(30, help="Skip товары обновлённые менее N дней назад"),
):
    """Crawl memmert.com — официальный сайт."""
    from catalog_crawler.adapters.vendors.memmert import MemmertAdapter
    adapter = MemmertAdapter(settings)
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip_fresh_days))


@vendor_app.command("sartorius")
def vendor_sartorius(
    limit: int = typer.Option(0, help="Ограничить число товаров (0 = все)"),
    skip_fresh_days: int = typer.Option(30, help="Skip товары обновлённые менее N дней назад"),
):
    """Crawl sartorius.com — официальный сайт."""
    from catalog_crawler.adapters.vendors.sartorius import SartoriusAdapter
    adapter = SartoriusAdapter(settings)
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip_fresh_days))


@gluvex_app.command("structure")
def gluvex_structure(
    upload: bool = typer.Option(True, help="Загрузить дамп в MinIO"),
    save_local: str = typer.Option("", help="Сохранить локально (путь)"),
):
    """Парсит sitemap-index gluvexlab.com → dump структуры (бренды/категории/счётчики)."""
    adapter = GluvexLabAdapter(settings)
    asyncio.run(adapter.crawl_structure(upload_to_minio=upload, local_path=save_local or None))


@gluvex_app.command("products")
def gluvex_products(
    limit: int = typer.Option(0, help="Ограничить число товаров (0 = все ~57k)"),
    shards: str = typer.Option("", help="Comma-separated индексы sitemap-шардов (0..56). Пусто=все."),
):
    """Парсит карточки товаров gluvexlab.com → таблица product."""
    from catalog_crawler.adapters.gluvexlab_products import crawl_products
    shard_list = [int(x) for x in shards.split(",") if x.strip()] if shards else None
    asyncio.run(crawl_products(settings, limit=limit, sitemap_shards=shard_list))


@app.command("ping")
def ping():
    """Проверка коннектов к Postgres / MinIO."""
    asyncio.run(_ping())


async def _ping():
    from catalog_crawler.core.db import check_pg
    from catalog_crawler.core.storage import check_minio

    pg_ok = await check_pg()
    minio_ok = check_minio()
    typer.echo(f"postgres: {'ok' if pg_ok else 'FAIL'}")
    typer.echo(f"minio:    {'ok' if minio_ok else 'FAIL'}")
    sys.exit(0 if (pg_ok and minio_ok) else 1)


if __name__ == "__main__":
    app()
