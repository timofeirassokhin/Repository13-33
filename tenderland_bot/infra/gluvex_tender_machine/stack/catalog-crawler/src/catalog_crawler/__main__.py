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
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/gas-chromatography-gc/gc-systems.html",
            "https://www.thermofisher.com/us/en/home/industrial/chromatography/ion-chromatography-ic/ion-chromatography-systems.html",
            # Spectroscopy / Elemental hub
            "https://www.thermofisher.com/us/en/home/industrial/spectroscopy-elemental-isotope-analysis.html",
            # Life Science / NGS Ion Torrent hub
            "https://www.thermofisher.com/us/en/home/life-science/sequencing/next-generation-sequencing/ion-torrent-next-generation-sequencing-technology.html",
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
