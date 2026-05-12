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


# ============================================================
# Generic-based vendor commands — для брендов с простой open-структурой
# ============================================================
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36"
)


def _run_generic(**kw):
    """Helper — создать GenericVendorAdapter и запустить."""
    from catalog_crawler.adapters.vendors.generic import GenericVendorAdapter
    limit = kw.pop("limit", 0)
    skip = kw.pop("skip_fresh_days", 30)
    adapter = GenericVendorAdapter(settings, **kw)
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip))


@vendor_app.command("sotax")
def vendor_sotax(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl sotax.com — pharma testing (dissolution/hardness/friability)."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="SOTAX", brand_slug="sotax",
        base_url="https://www.sotax.com",
        entry_urls=["https://www.sotax.com/products/"],
        category_keyword_map={
            "dissolution": "accessory", "tablet-hardness": "accessory",
            "friability": "accessory", "disintegration": "accessory",
            "sample-preparation": "accessory", "tablet": "accessory",
        },
        domain_hint="pharmaceutical",
        default_category="accessory",
        max_depth=4, max_urls=400,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("bandelin")
def vendor_bandelin(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl bandelin.com — ultrasonic (sonorex, sonopuls)."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="BANDELIN", brand_slug="bandelin",
        base_url="https://bandelin.com",
        entry_urls=["https://bandelin.com/en/products/"],
        category_keyword_map={
            "sonorex": "shaker_vortex", "sonopuls": "shaker_vortex",
            "ultrasonic-bath": "shaker_vortex", "homogeniser": "shaker_vortex",
            "industry": "accessory",
        },
        domain_hint="general_lab",
        default_category="shaker_vortex",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("retsch")
def vendor_retsch(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl retsch.com — mills, sieves, sample dividers."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Retsch", brand_slug="retsch",
        base_url="https://www.retsch.com",
        entry_urls=[
            "https://www.retsch.com/products/milling/",
            "https://www.retsch.com/products/sieving/",
            "https://www.retsch.com/products/assisting/",
        ],
        category_keyword_map={
            "milling": "accessory", "mill": "accessory",
            "sieving": "accessory", "sieve": "accessory",
            "crusher": "accessory", "shaker": "shaker_vortex",
            "divider": "accessory", "press": "accessory",
        },
        domain_hint="analytical",
        default_category="accessory",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("metrohm")
def vendor_metrohm(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl metrohm.com — titration, ion chromatography."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Metrohm", brand_slug="metrohm",
        base_url="https://www.metrohm.com",
        entry_urls=[
            "https://www.metrohm.com/en/products.html",
            "https://www.metrohm.com/en/products/",
        ],
        category_keyword_map={
            "titrator": "titrator", "titration": "titrator",
            "ion-chromatography": "hplc_system",
            "voltammetry": "other",
            "ph-meter": "accessory", "conductivity": "accessory",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=4, max_urls=400,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("huber")
def vendor_huber(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl huber-online.com — circulating thermostats, chillers."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Huber", brand_slug="huber",
        base_url="https://www.huber-online.com",
        entry_urls=[
            "https://www.huber-online.com/en/products.aspx",
            "https://www.huber-online.com/en/products/",
        ],
        category_keyword_map={
            "unichiller": "climate_chamber", "unistat": "climate_chamber",
            "chiller": "climate_chamber", "circulating": "climate_chamber",
            "thermostat": "climate_chamber", "bath": "drying_oven",
        },
        domain_hint="general_lab",
        default_category="climate_chamber",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("heidolph")
def vendor_heidolph(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl heidolph.com — rotary evaporators, shakers, plates."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Heidolph", brand_slug="heidolph",
        base_url="https://heidolph.com",
        entry_urls=["https://heidolph.com/emea/en/Products"],
        category_keyword_map={
            "rotary-evaporator": "accessory", "rotavap": "accessory",
            "evaporator": "accessory",
            "shaker": "shaker_vortex", "stirrer": "shaker_vortex",
            "magnetic": "shaker_vortex", "overhead": "shaker_vortex",
            "hot-plate": "drying_oven", "heating-plate": "drying_oven",
            "pump": "accessory", "homogenizer": "shaker_vortex",
        },
        domain_hint="general_lab",
        default_category="other",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
    )


@vendor_app.command("camag")
def vendor_camag(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl camag.com — TLC (thin-layer chromatography)."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="CAMAG", brand_slug="camag",
        base_url="https://www.camag.com",
        entry_urls=[
            "https://www.camag.com/en/products",
            "https://www.camag.com/en/products/",
        ],
        category_keyword_map={
            "tlc": "accessory", "thin-layer": "accessory",
            "scanner": "accessory", "applicator": "accessory",
            "ats": "accessory", "linomat": "accessory",
        },
        domain_hint="analytical",
        default_category="accessory",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
    )


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
