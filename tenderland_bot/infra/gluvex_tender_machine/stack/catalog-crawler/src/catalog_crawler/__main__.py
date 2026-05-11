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
    limit: int = typer.Option(0, help="Ограничить число товаров (0 = без ограничения)"),
    brand: str = typer.Option("", help="Только товары конкретного бренда (slug)"),
):
    """Парсит карточки товаров gluvexlab.com → таблица product."""
    typer.echo("TODO: будет в следующей итерации после изучения структуры.")
    sys.exit(2)


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
