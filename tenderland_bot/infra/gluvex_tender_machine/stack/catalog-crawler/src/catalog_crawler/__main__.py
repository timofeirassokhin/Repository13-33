"""CLI entrypoint:

  python -m catalog_crawler gluvexlab structure   # парсит sitemap → JSON dump в MinIO
  python -m catalog_crawler gluvexlab products    # парсит детальные карточки → product таблица
"""
from __future__ import annotations

import asyncio
import os
import sys

import typer

from catalog_crawler.adapters.gluvexlab import GluvexLabAdapter
from catalog_crawler.settings import settings


app = typer.Typer(no_args_is_help=True, add_completion=False)
gluvex_app = typer.Typer(no_args_is_help=True)
app.add_typer(gluvex_app, name="gluvexlab")

vendor_app = typer.Typer(no_args_is_help=True)
app.add_typer(vendor_app, name="vendor")


@app.command("brochures")
def brochures_cmd(
    brand: str = typer.Argument(..., help="brand_slug (memmert/...)"),
    limit: int = typer.Option(0, help="Лимит на число PDF (0 = все)"),
):
    """Скачивает PDF datasheets с download-center страницы вендора."""
    from catalog_crawler.adapters.brochure_finder import run_brochures
    asyncio.run(run_brochures(settings, brand_slug=brand, limit=limit))


@app.command("pricelist-import")
def pricelist_import_cmd(
    json_path: str = typer.Argument(..., help="Путь к JSON-файлу (создан tools/parse_pricelist_pdf.py)"),
    brand: str = typer.Option("Illumina", help="Бренд для всех записей"),
    imported_from: str = typer.Option("scientigen_pricelist",
                                       help="Значение imported_from в БД"),
    distributor: str = typer.Option("ScientiGen", help="Название дистрибьютора"),
    dry_run: bool = typer.Option(False, "--dry-run",
                                  help="Показать что будет insert'нуто, не записывать"),
):
    """Import pricelist JSON → product table (создаёт stub-записи).

    Главный use case — Illumina ScientiGen Feb 2026 prelist (2896 артикулов).
    После импорта эти продукты становятся целью для brochure-web pipeline.

    Пример:
        docker compose run --rm \\
            -v /opt/gluvex/pricelists:/pricelists:ro \\
            catalog-crawler pricelist-import /pricelists/scientigen.json
    """
    from pathlib import Path
    from catalog_crawler.adapters.pricelist_importer import import_pricelist_json
    asyncio.run(import_pricelist_json(
        settings,
        json_path=Path(json_path),
        brand=brand,
        imported_from=imported_from,
        distributor_name=distributor,
        dry_run=dry_run,
    ))


@app.command("brochure-web")
def brochure_web_cmd(
    brand: str = typer.Argument(..., help="Точный product.brand (например 'Illumina')"),
    limit: int = typer.Option(0, help="Лимит продуктов (0 = все без datasheets)"),
    rate_limit: float = typer.Option(3.0, help="Пауза между поиск-запросами, сек."),
    max_pdfs: int = typer.Option(5, help="Максимум PDF на один продукт"),
    category: str = typer.Option(
        "", "--category",
        help="Filter по product_category_t (sequencer_platform/ngs_target_capture_panel/...)",
    ),
    include_with_existing: bool = typer.Option(
        False, "--include-existing",
        help="Включать продукты у которых уже есть datasheets (для дополнения)",
    ),
):
    """Multi-query web-search для PDF документов (datasheet/app-note/brochure/tech-note).

    Для каждого продукта генерирует 6-9 search-queries:
      - "<vendor_code>" <brand> datasheet pdf
      - "<vendor_code>" <brand> application note pdf
      - "<vendor_code>" <brand> brochure pdf
      - <brand> <model> datasheet pdf
      - site:<vendor_site> <vendor_code>
      - site:<distributor> <vendor_code> <brand>

    Каждый найденный PDF классифицируется (datasheet/application_note/brochure/
    technical_note/manual/compliance) по URL/title и сохраняется в MinIO:
      product-brochures/<brand_slug>/<vendor_code>__<doc_type>__<hash6>.pdf

    Engines (auto-fallback):
      1. SerpAPI (SERPAPI_KEY env, $50/5K)
      2. Bing API (BING_API_KEY env, $7/1K)
      3. DuckDuckGo HTML scrape (no key, ~3 sec/req)

    Примеры:
      # Illumina — только приборы (50 шт)
      docker compose run --rm catalog-crawler \\
          brochure-web 'Illumina' --category sequencer_platform --limit 10

      # Все онко-панели Illumina (TSO500, Pillar, и т.д.)
      docker compose run --rm catalog-crawler \\
          brochure-web 'Illumina' --category ngs_target_capture_panel

      # Polный pass — все продукты без datasheets
      docker compose run --rm catalog-crawler brochure-web 'Illumina'
    """
    from catalog_crawler.adapters.brochure_web_search import enrich_brand_brochures
    asyncio.run(enrich_brand_brochures(
        settings, brand=brand, limit=limit,
        rate_limit_seconds=rate_limit, max_pdfs_per_product=max_pdfs,
        category_filter=category or None,
        only_no_datasheet=not include_with_existing,
    ))


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
    """Helper — создать GenericVendorAdapter и запустить.

    Дополнительные env-управляемые опции:
      USE_PLAYWRIGHT=1 — использовать headless Chromium вместо curl
      PROXY_URL=http://user:pass@host:port — residential proxy для тяжёлых брендов
    """
    from catalog_crawler.adapters.vendors.generic import GenericVendorAdapter
    limit = kw.pop("limit", 0)
    skip = kw.pop("skip_fresh_days", 30)

    # env-overrides — позволяет включить через ENV без CLI флагов
    if os.environ.get("USE_PLAYWRIGHT") in ("1", "true", "yes"):
        kw["use_playwright"] = True
    proxy_url = os.environ.get("PROXY_URL")
    if proxy_url:
        kw["proxy_url"] = proxy_url

    adapter = GenericVendorAdapter(settings, **kw)
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip))


@vendor_app.command("sotax")
def vendor_sotax(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl sotax.com — pharma testing (dissolution/hardness/friability)."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="SOTAX", brand_slug="sotax",
        base_url="https://www.sotax.com",
        entry_urls=[
            # SOTAX использует underscore-slug (не dash)
            "https://www.sotax.com/products/dissolution_usp_1_2_5_6",
            "https://www.sotax.com/products/dissolution_usp_4",
            "https://www.sotax.com/products/physical_testing",
            "https://www.sotax.com/products/sample_preparation",
            "https://www.sotax.com/products/data_management",
        ],
        category_keyword_map={
            "dissolution": "accessory", "tablet-hardness": "accessory",
            "tablet_hardness": "accessory",
            "friability": "accessory", "disintegration": "accessory",
            "sample_preparation": "accessory", "physical_testing": "accessory",
        },
        domain_hint="pharmaceutical",
        default_category="accessory",
        max_depth=5, max_urls=400,
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
            "ball-mill": "accessory", "rotor-mill": "accessory",
            "cutting-mill": "accessory", "jaw-crusher": "accessory",
            "sieving": "accessory", "sieve": "accessory", "test-sieve": "accessory",
            "shaker": "shaker_vortex",
            "divider": "accessory", "press": "accessory", "feeder": "accessory",
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
            # Metrohm: /products/<category>.html (с расширением)
            "https://www.metrohm.com/en/products/titration.html",
            "https://www.metrohm.com/en/products/ion-chromatography.html",
            "https://www.metrohm.com/en/products/voltammetry.html",
            "https://www.metrohm.com/en/products/spectroscopy.html",
            "https://www.metrohm.com/en/products/stability-measurement.html",
            "https://www.metrohm.com/en/products/electroanalysis.html",
            "https://www.metrohm.com/en/products/ph-conductivity.html",
        ],
        category_keyword_map={
            "titrator": "titrator", "titration": "titrator",
            "ion-chromatography": "hplc_system",
            "voltammetry": "other",
            "ph-meter": "accessory", "conductivity": "accessory",
            "spectroscopy": "uv_vis_spectrometer",
            "raman": "raman_spectrometer", "nir": "nir_spectrometer",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=5, max_urls=400,
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
        entry_urls=[
            # явный список подкатегорий — иначе BFS идёт на /america/ /asia/ /dach/
            "https://heidolph.com/emea/en/Products/Stirring",
            "https://heidolph.com/emea/en/Products/LiquidHandling",
            "https://heidolph.com/emea/en/Products/Evaporation",
            "https://heidolph.com/emea/en/Products/VortexingAndShaking",
            "https://heidolph.com/emea/en/Products/ReactorSystems",
        ],
        category_keyword_map={
            "rotary-evaporator": "accessory", "rotavap": "accessory",
            "evaporator": "accessory", "evaporation": "accessory",
            "shaker": "shaker_vortex", "stirrer": "shaker_vortex", "stirring": "shaker_vortex",
            "magnetic": "shaker_vortex", "overhead": "shaker_vortex",
            "vortex": "shaker_vortex", "vortexing": "shaker_vortex",
            "hot-plate": "drying_oven", "heating-plate": "drying_oven",
            "pump": "accessory", "pumping": "accessory",
            "liquidhandling": "consumable",
            "homogenizer": "shaker_vortex",
            "reactor": "other",
        },
        domain_hint="general_lab",
        default_category="other",
        max_depth=5, max_urls=300,
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


# ============================================================
# Тяжёлые бренды — обязательно Playwright+proxy (anti-bot + JS challenge)
# ============================================================

@vendor_app.command("agilent")
def vendor_agilent(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl agilent.com — flagships only (HPLC/GC/MS/AAS/ICP-MS systems)."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Agilent Technologies", brand_slug="agilent",
        base_url="https://www.agilent.com",
        entry_urls=[
            # Аналитические разделы Agilent — узкие точки чтобы не парсить 50k запчастей
            "https://www.agilent.com/en/products/liquid-chromatography",
            "https://www.agilent.com/en/products/gas-chromatography",
            "https://www.agilent.com/en/products/mass-spectrometry",
            "https://www.agilent.com/en/products/atomic-spectroscopy",
            "https://www.agilent.com/en/products/icp-ms",
            "https://www.agilent.com/en/products/icp-oes",
            "https://www.agilent.com/en/products/molecular-spectroscopy",
        ],
        category_keyword_map={
            "liquid-chromatography": "hplc_system", "lc-": "hplc_system",
            "uhplc": "hplc_system", "hplc": "hplc_system",
            "gas-chromatography": "gc_system", "gc-": "gc_system",
            "mass-spectrometry": "mass_spectrometer", "lcms": "mass_spectrometer",
            "gcms": "mass_spectrometer", "tof": "mass_spectrometer",
            "atomic-absorption": "aas_system", "aas": "aas_system",
            "icp-ms": "icp_ms", "icp-oes": "icp_oes",
            "ftir": "ftir_spectrometer", "uv-vis": "uv_vis_spectrometer",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=3, max_urls=200,
        user_agent_override=BROWSER_UA,
        use_playwright=True,       # Agilent имеет DataDome — обязательно Chromium+stealth
    )


@vendor_app.command("thermofisher")
def vendor_thermo(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl thermofisher.com — family-level pages (Orbitrap, Vanquish, TSQ, ICP, FTIR + Ion Torrent NGS).

    Thermo runs on Adobe AEM (Komodo). Family/category .html pages are static-rendered
    с brochures, **но** индивидуальные инструменты подгружаются filter-tool-app.js
    через XHR (для них нужен Playwright). Этот adapter покрывает family-level —
    адекватно для tender-matching ("LC-MS triple quadrupole" → Thermo TSQ family).
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Thermo Fisher Scientific", brand_slug="thermofisher",
        base_url="https://www.thermofisher.com",
        entry_urls=[
            # Mass Spec families (200 OK, статика, содержат deep model links + assets.thermofisher.com PDFs)
            "https://www.thermofisher.com/us/en/home/industrial/mass-spectrometry/liquid-chromatography-mass-spectrometry-lc-ms/lc-ms-systems/orbitrap-lc-ms.html",
            "https://www.thermofisher.com/us/en/home/industrial/mass-spectrometry/liquid-chromatography-mass-spectrometry-lc-ms/lc-ms-systems/triple-quadrupole-lc-ms.html",
            "https://www.thermofisher.com/us/en/home/industrial/mass-spectrometry/gas-chromatography-mass-spectrometry-gc-ms/gc-ms-systems.html",
            # Chromatography families
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/liquid-chromatography-lc/hplc-uhplc-systems.html",
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/liquid-chromatography-lc/hplc-uhplc-systems/vanquish-uhplc-systems.html",
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/gas-chromatography-gc/gc-systems.html",
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/ion-chromatography-ic/ion-chromatography-systems.html",
            # Spectroscopy / Elemental hub
            "https://www.thermofisher.com/us/en/home/industrial/spectroscopy-elemental-isotope-analysis.html",
            # Life Science / NGS Ion Torrent hub
            "https://www.thermofisher.com/us/en/home/life-science/sequencing/next-generation-sequencing/ion-torrent-next-generation-sequencing-technology.html",
            # Sanger / Capillary Electrophoresis Genetic Analyzers (3500, 3500xl, SeqStudio,
            # 3730/3730xl) + Sanger reagents/kits/accessories — individual instrument pages
            # отдельно 404, но из этого хаба BFS подтягивает kits/reagents/accessories pages.
            # NB: individual 3500/SeqStudio appliance pages нужен Playwright (next session).
            "https://www.thermofisher.com/us/en/home/life-science/sequencing/sanger-sequencing.html",
        ],
        category_keyword_map={
            # HPLC / UHPLC
            "vanquish": "hplc_system", "ultimate-3000": "hplc_system",
            "hplc-uhplc-systems": "hplc_system", "hplc-uhplc": "hplc_system",
            "liquid-chromatography-lc": "hplc_system", "uhplc": "hplc_system",
            "hplc": "hplc_system",
            # GC
            "gc-systems": "gc_system", "gas-chromatography-gc": "gc_system",
            "trace-1300": "gc_system", "trace-1600": "gc_system",
            # IC (Ion Chromatography)
            "ion-chromatography-systems": "hplc_system",  # IC closest to HPLC bucket
            "dionex": "hplc_system",
            # MS — Orbitrap / TSQ / ISQ / LTQ / EM / GC-MS
            "orbitrap-lc-ms": "mass_spectrometer", "orbitrap": "mass_spectrometer",
            "tsq": "mass_spectrometer", "isq": "mass_spectrometer",
            "lc-ms": "mass_spectrometer", "gc-ms": "mass_spectrometer",
            "mass-spectrometry": "mass_spectrometer",
            "tribrid": "mass_spectrometer", "tof-ms": "mass_spectrometer",
            "altis": "mass_spectrometer", "stellar": "mass_spectrometer",
            "exploris": "mass_spectrometer", "ascend": "mass_spectrometer",
            "eclipse": "mass_spectrometer", "ardia": "mass_spectrometer",
            # AA / ICP
            "icap": "icp_ms", "icp-ms": "icp_ms", "icp-oes": "icp_oes",
            "atomic-absorption": "aas_system", "ice-3000": "aas_system",
            "elemental": "icp_ms",
            # FTIR / UV-Vis / Raman
            "nicolet": "ftir_spectrometer", "ftir": "ftir_spectrometer",
            "is50": "ftir_spectrometer",
            "evolution": "uv_vis_spectrometer", "uv-vis": "uv_vis_spectrometer",
            "raman": "uv_vis_spectrometer",
            # NGS / Ion Torrent
            "ion-torrent": "sequencer_platform", "genestudio": "sequencer_platform",
            "ion-gene-studio": "sequencer_platform", "ion-proton": "sequencer_platform",
            "ion-genexus": "sequencer_platform", "next-generation-sequencing": "sequencer_platform",
            # Sanger / Capillary Electrophoresis Genetic Analyzers
            # (3500, 3500xl, 3730, 3730xl, SeqStudio — capillary electrophoresis Sanger sequencers)
            "seqstudio": "sequencer_platform", "3500-genetic": "sequencer_platform",
            "3500xl-genetic": "sequencer_platform", "3730-dna": "sequencer_platform",
            "3730xl-dna": "sequencer_platform", "3730-3730xl": "sequencer_platform",
            "applied-biosystems-genetic-analyzers": "sequencer_platform",
            "sanger-sequencing-kits-reagents": "ngs_library_prep_kit",  # Sanger kits
            "sanger-sequencing-technology-accessories": "accessory",
            "fragment-analysis": "sequencer_platform",
            "capillary-electrophoresis": "sequencer_platform",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=2, max_urls=400,
        user_agent_override=BROWSER_UA,
        # CRITICAL: Thermo URL'ы — /us/en/home/industrial/... — default `/product` filter
        # отсекал бы всё. Переопределяем url_must_contain под Thermo namespace.
        # NB: /order/catalog/product НЕ включаем — это e-commerce SKU rabbit hole.
        url_must_contain=[
            "/us/en/home/industrial",
            "/us/en/home/life-science",
        ],
        url_must_not_contain=[
            # учебные / маркетинговые секции — НЕ продукты
            "/learning-center", "/applications-area", "/resource-library",
            "/resources-library", "/learning-resource", "/insights",
            # workflows / методические — не приборы
            "/workflows/", "/proteomics-mass-spectrometry/",
            "/metabolomics-mass-spectrometry/",
            "/translational-proteomics", "/quantitation",
            # industry verticals
            "/pharma-biopharma/", "/food-beverage/", "/forensics/",
            "/environmental/", "/clinical/", "/diagnostics/",
            "/industry/", "/services/", "/cdmo/",
            # forms / contact / privacy / events / careers
            "/forms/", "/contact", "/career", "/legal", "/imprint",
            "/privacy", "/about", "/news", "/event", "/webinar",
            "/cart", "/checkout", "/login", "/auth/",
            # explicit other-locale paths (всё что внутри Thermo не /us/en/)
            "/ar/", "/au/", "/br/", "/ca/", "/cl/", "/cn/", "/de/", "/es/",
            "/fr/", "/hk/", "/ht/", "/id/", "/in/", "/io/", "/jp/", "/kr/",
            "/mx/", "/ng/", "/ru/", "/sa/", "/sg/", "/tg/", "/tr/", "/tw/",
            "/uk/", "/za/", "/it/", "/nl/", "/pl/", "/se/", "/dk/", "/no/",
            "/fi/", "/cz/", "/hu/", "/sk/", "/ro/", "/bg/", "/my/", "/th/",
            "/vn/", "/ph/", "/pk/", "/lk/", "/bd/", "/np/", "/mn/",
        ],
        # NB: max_depth=2 — entry URLs визитятся (depth=0), их links фильтруются и
        # либо идут в found (>=3 segments в path — это и есть наш case), либо в очередь.
        # Глубже одного-двух хопов BFS не имеет смысла — Thermo deep instrument pages
        # уже найдены прямой ссылкой с family-страниц.
    )


@vendor_app.command("shimadzu")
def vendor_shimadzu(
    limit: int = typer.Option(0, help="Ограничить число товаров (0 = все ~631)"),
    skip_fresh_days: int = typer.Option(30, help="Skip товары обновлённые менее N дней назад"),
):
    """Crawl shimadzu.com — JSON-driven adapter, ~631 products (HPLC/LC-MS/GC/GC-MS/AA/ICP/UV-Vis/FTIR/...)."""
    from catalog_crawler.adapters.vendors.shimadzu import ShimadzuAdapter
    adapter = ShimadzuAdapter(settings)
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip_fresh_days))


@vendor_app.command("agilent-sitemap")
def vendor_agilent_sitemap(
    limit: int = typer.Option(0, help="Ограничить число товаров (0 = все ~3,844)"),
    skip_fresh_days: int = typer.Option(30, help="Skip товары обновлённые менее N дней назад"),
):
    """Agilent sitemap-only stubs (~3,844 products). HTML+PDF Agilent блокирует DataDome —
    создаём stub-записи чисто из products0.xml. Дополняет gluvexlab spare-parts catalog."""
    from catalog_crawler.adapters.vendors.agilent_sitemap import AgilentSitemapAdapter
    adapter = AgilentSitemapAdapter(settings)
    # PROXY_URL применяется адаптером самостоятельно (через self.proxy_url из base.py
    # __init__ — но base его не подхватывает; передадим явно через env override).
    proxy_url = os.environ.get("PROXY_URL")
    if proxy_url:
        adapter.proxy_url = proxy_url
    asyncio.run(adapter.run(limit=limit, skip_existing_fresh_days=skip_fresh_days))


@vendor_app.command("waters")
def vendor_waters(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl waters.com — UPLC, ACQUITY, Xevo, Synapt mass spec."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Waters", brand_slug="waters",
        base_url="https://www.waters.com",
        entry_urls=[
            "https://www.waters.com/nextgen/global/products.html",
            "https://www.waters.com/nextgen/global/products/chromatography.html",
            "https://www.waters.com/nextgen/global/products/mass-spectrometry.html",
        ],
        category_keyword_map={
            "acquity": "hplc_system", "uplc": "hplc_system", "hplc": "hplc_system",
            "xevo": "mass_spectrometer", "synapt": "mass_spectrometer",
            "select-series": "mass_spectrometer",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
        # Waters даёт HTTP/2 error при некоторых rendering — fallback на Playwright если надо
    )


@vendor_app.command("sciex")
def vendor_sciex(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl sciex.com — Triple Quad, QTRAP, ZenoTOF mass spec."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="AB Sciex", brand_slug="sciex",
        base_url="https://sciex.com",
        entry_urls=[
            "https://sciex.com/products",
            "https://sciex.com/products/",
        ],
        category_keyword_map={
            "triple-quad": "mass_spectrometer", "qtrap": "mass_spectrometer",
            "zenotof": "mass_spectrometer", "tof": "mass_spectrometer",
            "x-series": "mass_spectrometer",
        },
        domain_hint="analytical",
        default_category="mass_spectrometer",
        max_depth=4, max_urls=200,
        user_agent_override=BROWSER_UA,
        # Sciex полностью открыт через residential
    )


@vendor_app.command("bruker")
def vendor_bruker(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl bruker.com — timsTOF, MaXis, SCION GC, NMR."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Bruker", brand_slug="bruker",
        base_url="https://www.bruker.com",
        entry_urls=[
            "https://www.bruker.com/en/products-and-solutions.html",
            "https://www.bruker.com/en/products-and-solutions/mass-spectrometry.html",
        ],
        category_keyword_map={
            "timstof": "mass_spectrometer", "maxis": "mass_spectrometer",
            "amazon": "mass_spectrometer", "mass-spectro": "mass_spectrometer",
            "scion-gc": "gc_system", "gc-": "gc_system",
            "ftir": "ftir_spectrometer", "tensor": "ftir_spectrometer",
            "nmr": "other",
        },
        domain_hint="analytical",
        default_category="other",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
        # Bruker открыт через residential
    )


# ============================================================
# NGS / Genetics instruments — главный пробел в каталоге
# ============================================================
# По состоянию на 2026-05-14 в БД ноль datasheets от любого NGS вендора.
# План: 6 instrument-adapters + 6 reagent-adapters. Все enabled-by-default,
# но первый запуск требует --limit 5 для smoke-test (структура каждого сайта своя).
#
# IMPORTANT: для китайских вендоров (MGI, Genemind, Vazyme, Burning Rock,
# AmoyDx, Novogene) ставь USE_PLAYWRIGHT=1 — некоторые JS-heavy + Cloudflare.
# Российские (Хеликон, Сесана, Salus-bio, Parseq, OncoAtlas, Nanodigm,
# TestGen) — открыты напрямую, proxy не нужен.

@vendor_app.command("helicon")
def vendor_helicon(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl shop.helicon.ru — RU дистрибьютор MGI/Genemind/Illumina + расходники.

    Самый широкий русский каталог по NGS. Каждая product page содержит:
      - vendor_code артикул (например 900-001108-00 для DNBSEQ-T7+)
      - brand (MGI/Illumina/Genemind)
      - model
      - 5-10 ключевых technical specs (output, Q40, read mode, dimensions)
    PDF datasheets НЕТ (норма для distributor-shop), но technical text богатый.

    Verified URL map (WebFetch 2026-05-14):
      /catalog/equipment/science-and-analytics/sequencers/         — NGS + Sanger
      /catalog/equipment/science-and-analytics/pcr/                — амплификаторы / qPCR / digital PCR
      /catalog/equipment/science-and-analytics/automated-workstations/nucleic-acids-extraction/
      /catalog/equipment/gle/centrifuges/                          — общелабораторные центрифуги
      /catalog/reagents/reagents-and-kits/pcr-kits/                — реагенты PCR
      /catalog/reagents/reagents-and-kits/nucleic-acids-extraction-kits/
      /catalog/consumables/materials-for-equipment/materials-for-pcr/
      /catalog/consumables/laboratory/pcr-and-sequencing-plasticware/
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Хеликон", brand_slug="helicon",
        base_url="https://shop.helicon.ru",
        entry_urls=[
            "https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/",
            "https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/ngs/",
            "https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/sanger/",
            "https://shop.helicon.ru/catalog/equipment/science-and-analytics/pcr/",
            "https://shop.helicon.ru/catalog/equipment/science-and-analytics/automated-workstations/nucleic-acids-extraction/",
            "https://shop.helicon.ru/catalog/equipment/gle/centrifuges/",
            "https://shop.helicon.ru/catalog/reagents/reagents-and-kits/pcr-kits/",
            "https://shop.helicon.ru/catalog/reagents/reagents-and-kits/nucleic-acids-extraction-kits/",
            "https://shop.helicon.ru/catalog/consumables/materials-for-equipment/materials-for-pcr/",
            "https://shop.helicon.ru/catalog/consumables/laboratory/pcr-and-sequencing-plasticware/",
        ],
        category_keyword_map={
            "ngs": "sequencer_platform", "sequencer": "sequencer_platform",
            "sequencers": "sequencer_platform",
            "sanger": "sequencer_platform",
            "dnbseq": "sequencer_platform", "genoskan": "sequencer_platform",
            "library-prep": "ngs_library_prep_kit", "library": "ngs_library_prep_kit",
            "reagent": "ngs_library_prep_kit",
            "amplification": "pcr_kit", "amplifier": "pcr_kit",
            "pcr": "pcr_kit", "qpcr": "realtime_pcr_kit", "rt-pcr": "realtime_pcr_kit",
            "real-time-pcr": "realtime_pcr_kit",
            "digital-pcr": "pcr_kit",
            "isolation": "dna_extraction_kit", "extraction": "dna_extraction_kit",
            "centrifuge": "centrifuge", "centrifuges": "centrifuge",
            "flow-cell": "sequencer_flowcell", "flowcell": "sequencer_flowcell",
            "consumable": "consumable", "plasticware": "consumable",
            "tip": "consumable", "tube": "consumable", "tubes": "consumable",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_library_prep_kit",
        max_depth=4, max_urls=1500,           # Helicon — большой каталог
        user_agent_override=BROWSER_UA,
        # отключаем "/ru/" из default exclude — это и есть основной язык сайта
        url_must_contain=["/catalog/"],
        # отключим стандартные локальные исключения которые блокировали бы /ru/ /uk/
        url_must_not_contain=[
            "/news", "/career", "/contact", "/about", "/legal",
            "/imprint", "/privacy", "/login", "/cart", "/checkout",
            "/blog", "/event", "/whitepaper", "/webinar",
            "/personal/", "/auth/", "/search/", "/order/",
            "/help/", "/sitemap", "/promo", "/sale", "/discounts",
        ],
    )


@vendor_app.command("mgi-tech")
def vendor_mgi(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl global-mgitech.com — DNBSEQ платформы (G50/G99/G400/T1/T7/T10/T20) + reagents.

    Update 2026-05-14: en.mgi-tech.com → 301 redirect на global-mgitech.com.
    Структура: /seqall/, /gli/, /multiomics/ + конкретные модели /seqall/dnbseq-g99/.
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="MGI Tech", brand_slug="mgi_tech",
        base_url="https://global-mgitech.com",
        entry_urls=[
            "https://global-mgitech.com/products/",
            "https://global-mgitech.com/seqall/",
            "https://global-mgitech.com/gli/",
            "https://global-mgitech.com/multiomics/",
            "https://global-mgitech.com/seqall/dnbseq-g99/",
            "https://global-mgitech.com/seqall/dnbseq-g50/",
            "https://global-mgitech.com/seqall/dnbseq-g400/",
            "https://global-mgitech.com/seqall/dnbseq-t7/",
            "https://global-mgitech.com/seqall/dnbseq-t10/",
            "https://global-mgitech.com/seqall/dnbseq-t20/",
        ],
        category_keyword_map={
            "dnbseq": "sequencer_platform", "sequencer": "sequencer_platform",
            "g50": "sequencer_platform", "g99": "sequencer_platform",
            "g400": "sequencer_platform", "t1": "sequencer_platform",
            "t7": "sequencer_platform", "t10": "sequencer_platform",
            "t20": "sequencer_platform", "e25": "sequencer_platform",
            "mgieasy": "ngs_library_prep_kit", "easy": "ngs_library_prep_kit",
            "reagent": "ngs_library_prep_kit", "kit": "ngs_library_prep_kit",
            "flow-cell": "sequencer_flowcell", "flowcell": "sequencer_flowcell",
            "mgisp": "accessory", "stomatic": "accessory",
            "mgistp": "accessory", "ztron": "software",
            "automation": "accessory",
        },
        domain_hint="genetics_ngs",
        default_category="sequencer_platform",
        max_depth=4, max_urls=400,
        user_agent_override=BROWSER_UA,
        use_playwright=True,        # JS-heavy
        treat_entry_urls_as_products=True,  # явные модельные URLs из global-mgitech.com
    )


@vendor_app.command("illumina")
def vendor_illumina(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl illumina.com — MiSeq/NextSeq/NovaSeq/HiSeq/iSeq + reagent kits.

    У нас уже 483 stub-записи Illumina из gluvexlab — этот adapter обогатит
    их descriptions и (где найдёт) datasheet PDFs.
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Illumina", brand_slug="illumina",
        base_url="https://www.illumina.com",
        entry_urls=[
            "https://www.illumina.com/systems/sequencing-platforms.html",
            "https://www.illumina.com/systems/sequencing-platforms/novaseq.html",
            "https://www.illumina.com/systems/sequencing-platforms/nextseq.html",
            "https://www.illumina.com/systems/sequencing-platforms/miseq.html",
            "https://www.illumina.com/systems/sequencing-platforms/iseq.html",
            "https://www.illumina.com/systems/sequencing-platforms/miniseq.html",
            "https://www.illumina.com/products/by-type/sequencing-kits.html",
            "https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents.html",
            "https://www.illumina.com/products/by-type/sequencing-kits/library-prep-kits.html",
            "https://www.illumina.com/products/by-type/microarray-kits.html",
        ],
        category_keyword_map={
            "novaseq": "sequencer_platform", "nextseq": "sequencer_platform",
            "miseq": "sequencer_platform", "iseq": "sequencer_platform",
            "miniseq": "sequencer_platform", "hiseq": "sequencer_platform",
            "iscan": "sequencer_platform",
            "sequencing-platform": "sequencer_platform",
            "reagent-kit": "sequencer_reagent_kit",
            "library-prep": "ngs_library_prep_kit",
            "trueseq": "ngs_library_prep_kit", "nextera": "ngs_library_prep_kit",
            "amplisefor-illumina": "ngs_amplicon_panel",
            "truesight": "ngs_target_capture_panel",
            "microarray": "other", "beadchip": "other", "infinium": "other",
        },
        domain_hint="genetics_ngs",
        default_category="sequencer_platform",
        max_depth=4, max_urls=400,
        user_agent_override=BROWSER_UA,
        use_playwright=True,        # Illumina за Akamai, как и Agilent
    )


@vendor_app.command("genemind")
def vendor_genemind(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl en.genemind.com — GenoLab M / FASTASeq 300 / SURFSeq 5000."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Genemind", brand_slug="genemind",
        base_url="https://en.genemind.com",
        entry_urls=[
            "https://en.genemind.com/product/",
            "https://en.genemind.com/product/genolab-m",
            "https://en.genemind.com/product/fastaseq-300",
            "https://en.genemind.com/product/surfseq-5000",
            "https://en.genemind.com/product/surfseq-q",
            "https://en.genemind.com/product/genocare-1600",
        ],
        category_keyword_map={
            "genolab": "sequencer_platform", "fastaseq": "sequencer_platform",
            "surfseq": "sequencer_platform", "genocare": "sequencer_platform",
            "sequencer": "sequencer_platform",
            "reagent": "sequencer_reagent_kit", "kit": "sequencer_reagent_kit",
        },
        domain_hint="genetics_ngs",
        default_category="sequencer_platform",
        max_depth=4, max_urls=200,
        user_agent_override=BROWSER_UA,
        # url_must_contain не /product (на ./en.genemind /product без -s)
        url_must_contain=["/product"],
    )


@vendor_app.command("sesana")
def vendor_sesana(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl sesana.ru — RU OEM Genemind, линейка Геноскан 3700/4000/5000/6000.

    Корректные URL (проверено WebFetch 2026-05-14):
      /ngs_sequencers      — главный каталог
      /fastaseq300         — Genoskan 3700
      /genoLabm            — Genoskan 4000
      /surfseq             — Genoskan 5000
      /surfseqq            — Genoskan 6000
      /fastaseq_s          — FASTASeq S
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Сесана", brand_slug="sesana",
        base_url="https://sesana.ru",
        entry_urls=[
            "https://sesana.ru/ngs_sequencers",
            "https://sesana.ru/fastaseq300",
            "https://sesana.ru/genoLabm",
            "https://sesana.ru/surfseq",
            "https://sesana.ru/surfseqq",
            "https://sesana.ru/fastaseq_s",
        ],
        category_keyword_map={
            "genoskan": "sequencer_platform", "геноскан": "sequencer_platform",
            "fastaseq": "sequencer_platform", "genolabm": "sequencer_platform",
            "surfseq": "sequencer_platform",
            "sekvenator": "sequencer_platform", "секвенатор": "sequencer_platform",
            "ngs_sequencers": "sequencer_platform",
            "reagent": "ngs_library_prep_kit", "реаген": "ngs_library_prep_kit",
        },
        domain_hint="genetics_ngs",
        default_category="sequencer_platform",
        max_depth=2, max_urls=50,  # маленький сайт-визитка, BFS не нужно глубоко
        user_agent_override=BROWSER_UA,
        treat_entry_urls_as_products=True,  # flat URL = entry-уровень и есть товары
    )


@vendor_app.command("salus-bio")
def vendor_salus(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl salus-bio.ru — Salus Evo/Pro + RU OEM Биофьюжн (Р-Ген 2000).

    Корректные URL (проверено WebFetch 2026-05-14):
      /sequencers/              — главный список
      /sequencers/saluspro/     — Salus Pro RS / Р-Ген 2000
      /sequencers/salusevo/     — Salus Evo
      /sequencers/salusseqnimbo/— Saluseq Nimbo / Р-Ген 100
      /reagents/                — реагенты
      /chips/                   — чипы
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Salus / Биофьюжн", brand_slug="salus_bio",
        base_url="https://salus-bio.ru",
        entry_urls=[
            "https://salus-bio.ru/sequencers/",
            "https://salus-bio.ru/sequencers/saluspro/",
            "https://salus-bio.ru/sequencers/salusevo/",
            "https://salus-bio.ru/sequencers/salusseqnimbo/",
            "https://salus-bio.ru/reagents/",
            "https://salus-bio.ru/chips/",
        ],
        category_keyword_map={
            "salus": "sequencer_platform", "saluspro": "sequencer_platform",
            "salusevo": "sequencer_platform", "salusseqnimbo": "sequencer_platform",
            "р-ген": "sequencer_platform", "p-gen": "sequencer_platform",
            "biofusion": "sequencer_platform", "биофьюжн": "sequencer_platform",
            "sekvenator": "sequencer_platform", "секвенатор": "sequencer_platform",
            "sequencers": "sequencer_platform",
            "reagent": "ngs_library_prep_kit", "реаген": "ngs_library_prep_kit",
            "chip": "sequencer_flowcell", "чип": "sequencer_flowcell",
        },
        domain_hint="genetics_ngs",
        default_category="sequencer_platform",
        max_depth=3, max_urls=80,
        user_agent_override=BROWSER_UA,
        treat_entry_urls_as_products=True,  # каждый entry url — карточка прибора
    )


# ============================================================
# NGS reagents and panels
# ============================================================

@vendor_app.command("amoydx")
def vendor_amoydx(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl amoydiagnostics.com — HANDLE NGS-panel series + RT-qPCR kits.

    Verified URLs (WebFetch 2026-05-14):
      /products
      /products/amoydx-handle-classic-ngs-panel
      /products/amoydx-hrd-focus-panel
      /products/amoydx-hrd-complete-panel
      /products/amoydx-master-panel
      /products/amoydx-brca-pro-panel
      /products/amoydx-essential-ngs-panel
      /products/page/2..5#main  (pagination)
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="AmoyDx", brand_slug="amoydx",
        base_url="https://www.amoydiagnostics.com",
        entry_urls=[
            "https://www.amoydiagnostics.com/products",
            "https://www.amoydiagnostics.com/products/page/2",
            "https://www.amoydiagnostics.com/products/page/3",
            "https://www.amoydiagnostics.com/products/page/4",
            "https://www.amoydiagnostics.com/products/page/5",
            "https://www.amoydiagnostics.com/products/amoydx-handle-classic-ngs-panel",
            "https://www.amoydiagnostics.com/products/amoydx-hrd-focus-panel",
            "https://www.amoydiagnostics.com/products/amoydx-hrd-complete-panel",
            "https://www.amoydiagnostics.com/products/amoydx-master-panel",
            "https://www.amoydiagnostics.com/products/amoydx-brca-pro-panel",
            "https://www.amoydiagnostics.com/products/amoydx-essential-ngs-panel",
        ],
        category_keyword_map={
            "handle": "ngs_target_capture_panel",
            "ngs": "ngs_target_capture_panel",
            "amplicon": "ngs_amplicon_panel",
            "panel": "ngs_target_capture_panel",
            "qpcr": "realtime_pcr_kit", "rt-qpcr": "realtime_pcr_kit",
            "pcr": "pcr_kit",
            "andas": "ngs_target_capture_panel", "aras": "ngs_target_capture_panel",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_target_capture_panel",
        max_depth=4, max_urls=200,
        user_agent_override=BROWSER_UA,
        use_playwright=True,        # китайский, может Cloudflare
        treat_entry_urls_as_products=True,  # явные product URLs
    )


@vendor_app.command("pillar")
def vendor_pillar(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl pillar-biosciences.com — oncoReveal CDx, Heredity, Lung, Pan-Cancer."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Pillar Biosciences", brand_slug="pillar",
        base_url="https://www.pillar-biosciences.com",
        entry_urls=[
            "https://www.pillar-biosciences.com/products",
            "https://www.pillar-biosciences.com/clinical",
            "https://www.pillar-biosciences.com/research",
        ],
        category_keyword_map={
            "oncoreveal": "ngs_target_capture_panel",
            "reveal": "ngs_target_capture_panel",
            "heredity": "ngs_target_capture_panel",
            "pan-cancer": "ngs_target_capture_panel",
            "lung": "ngs_target_capture_panel",
            "amplicon": "ngs_amplicon_panel",
            "panel": "ngs_target_capture_panel",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_target_capture_panel",
        max_depth=4, max_urls=150,
        user_agent_override=BROWSER_UA,
        treat_entry_urls_as_products=True,  # явные product URLs
    )


@vendor_app.command("burning-rock")
def vendor_burning_rock(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl brbiotech.com — OncoScreen Plus / OncoCompass / OncoScreen Focus.

    Verified URLs (WebFetch 2026-05-14):
      Сайт использует PHP query-string URLs (/p_details.php?class_id=NNN).
      Корневая product страница: product.php
      Детальные:
        /p_details.php?class_id=102101101  (OncoScreen Focus CDx Tissue Kit CE-IVDD)
        /p_details.php?class_id=102101102  (OncoScreen Plus Cancer Profiling Tissue Kit CE-IVDD)
        /p_details.php?class_id=102101103  (OncoCompass Target Cancer Liquid Kit CE-IVDD)
        /p_details.php?class_id=102101104  (OncoScreen Focus)
        /p_details.php?class_id=102101105  (OncoScreen Plus / OncoCompass Plus)
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Burning Rock", brand_slug="burning_rock",
        base_url="https://www.brbiotech.com",
        entry_urls=[
            "https://www.brbiotech.com/en/product.php",
            "https://www.brbiotech.com/en/p_details.php?class_id=102101101",
            "https://www.brbiotech.com/en/p_details.php?class_id=102101102",
            "https://www.brbiotech.com/en/p_details.php?class_id=102101103",
            "https://www.brbiotech.com/en/p_details.php?class_id=102101104",
            "https://www.brbiotech.com/en/p_details.php?class_id=102101105",
        ],
        category_keyword_map={
            "oncoscreen": "ngs_target_capture_panel",
            "lungplasma": "ngs_target_capture_panel",
            "lungcore": "ngs_target_capture_panel",
            "oncocommons": "ngs_target_capture_panel",
            "oncomix": "ngs_target_capture_panel",
            "hrr": "ngs_target_capture_panel",
            "overc": "ngs_target_capture_panel",
            "multi-cancer": "ngs_target_capture_panel",
            "ctdna": "ngs_target_capture_panel",
            "panel": "ngs_target_capture_panel",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_target_capture_panel",
        max_depth=4, max_urls=200,
        user_agent_override=BROWSER_UA,
        use_playwright=True,        # китайский
        treat_entry_urls_as_products=True,  # явные product.php URLs с class_id
    )


@vendor_app.command("parseq")
def vendor_parseq(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl parseq.pro — Prep&Seq / Ready-U-Panel / OncoScope / PARallele / VariFind.

    Корректные URL (проверено WebFetch 2026-05-14):
      /products                   — главный
      /prep-and-seq               — модульная пробоподготовка
      /prep-and-seq/u-panel       — Prep&Seq U-panel
      /prep-and-seq/ready-u-panel — Ready-U-Panel
      /prep-and-seq/u-target-il-kit
      /parallele                  — HLA-типирование
      /oncoscope/nsclc-solution   — онкология (NSCLC)
      /pure-code/dna-rna-magnetic-ffpe — выделение НК
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Parseq Lab", brand_slug="parseq",
        base_url="https://parseq.pro",
        entry_urls=[
            "https://parseq.pro/products",
            "https://parseq.pro/prep-and-seq",
            "https://parseq.pro/prep-and-seq/u-panel",
            "https://parseq.pro/prep-and-seq/ready-u-panel",
            "https://parseq.pro/prep-and-seq/u-target-il-kit",
            "https://parseq.pro/parallele",
            "https://parseq.pro/oncoscope/nsclc-solution",
            "https://parseq.pro/pure-code/dna-rna-magnetic-ffpe",
        ],
        category_keyword_map={
            "prepseq": "ngs_library_prep_kit", "prep-and-seq": "ngs_library_prep_kit",
            "u-panel": "ngs_target_capture_panel",
            "ready-u-panel": "ngs_target_capture_panel",
            "ready-u": "ngs_target_capture_panel",
            "u-target": "ngs_target_capture_panel",
            "oncoscope": "ngs_target_capture_panel",
            "nsclc-solution": "ngs_target_capture_panel",
            "nsclc": "ngs_target_capture_panel",
            "parallele": "ngs_target_capture_panel",
            "varifind": "ngs_target_capture_panel",
            "pure-code": "dna_extraction_kit",
            "panel": "ngs_target_capture_panel",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_target_capture_panel",
        max_depth=3, max_urls=80,
        user_agent_override=BROWSER_UA,
        treat_entry_urls_as_products=True,  # flat URL продуктовых страниц
    )


@vendor_app.command("vazyme")
def vendor_vazyme(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl vazyme.com — VAHTS library prep + Hieff NGS reagents + auto stations."""
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Vazyme", brand_slug="vazyme",
        base_url="https://www.vazyme.com",
        entry_urls=[
            "https://en.vazyme.com/Product/",
            "https://en.vazyme.com/product/",
            "https://www.vazyme.com/en/Product/",
            "https://www.vazyme.com/Product/",
        ],
        category_keyword_map={
            "vahts": "ngs_library_prep_kit", "hieff": "ngs_library_prep_kit",
            "library-prep": "ngs_library_prep_kit",
            "rna-seq": "ngs_library_prep_kit",
            "exome": "ngs_target_capture_panel",
            "smart": "accessory",  # VAHTS Smart 8 — automation prep
            "maxup": "accessory", "ma-9000": "accessory",
            "kit": "ngs_library_prep_kit",
            "reagent": "ngs_library_prep_kit",
        },
        domain_hint="genetics_ngs",
        default_category="ngs_library_prep_kit",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
        use_playwright=True,        # китайский, JS-heavy
    )


@vendor_app.command("novogene")
def vendor_novogene(limit: int = 0, skip_fresh_days: int = 30):
    """Crawl novogene.com — services + WES/WGS reagents.

    Novogene преимущественно CRO-сервис, но имеет library prep kits.
    """
    _run_generic(
        limit=limit, skip_fresh_days=skip_fresh_days,
        brand_name="Novogene", brand_slug="novogene",
        base_url="https://en.novogene.com",
        entry_urls=[
            "https://en.novogene.com/services/",
            "https://en.novogene.com/products/",
            "https://en.novogene.com/clinical-services/",
        ],
        category_keyword_map={
            "wgs": "ngs_target_capture_panel", "whole-genome": "ngs_target_capture_panel",
            "wes": "ngs_target_capture_panel", "whole-exome": "ngs_target_capture_panel",
            "novapath": "ngs_target_capture_panel",
            "clinical": "ngs_target_capture_panel",
            "library-prep": "ngs_library_prep_kit",
            "kit": "ngs_library_prep_kit",
            "service": "service",
        },
        domain_hint="genetics_ngs",
        default_category="service",
        max_depth=4, max_urls=300,
        user_agent_override=BROWSER_UA,
        use_playwright=True,
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
