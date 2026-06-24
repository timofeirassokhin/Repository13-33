"""Agilent sitemap-driven stub adapter.

Agilent.com product HTML pages и литература (.pdf на /cs/library/...) — все
блокируются DataDome. Подтверждено: US/GB/DE/FR residential exits = все 403,
Playwright со stealth тоже не пробивает (timeout в challenge loop).

Но **sitemap.xml и products0.xml отдаются под IPRoyal residential без блока**:
  - agilent.com/sitemap.xml → 200 (sitemap-index)
  - agilent.com/products0.xml → 200, 9,215 URLs
  - 3,844 unique products после dedup'а по locale (en / ja-jp / ko-kr / zh-cn)

Из одних только URL извлекаем:
  - Иерархию категорий: /product/<top-domain>/<sub>/<sub>/<leaf>
  - Модель: human-readable name из leaf slug
  - vendor_code: числовой суффикс `-228249` где есть (~1,400 продуктов)

Записи помечаются `imported_from='agilent_sitemap'`,
metadata `{stub_only: True, needs_enrichment: True}`.

Стратегически: дополняет 32,088 spare parts из gluvexlab.com (которые
instrument-level не покрывают) — даёт каталог приборов для tender matching.

Override `run()` — НЕ делаем HTTP fetch к product pages (все 403). Создаём
записи чисто из URL pattern.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

import asyncpg

from catalog_crawler.adapters.vendors.base import VendorAdapter, VendorProductData
from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.core.fetcher import Fetcher


BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130 Safari/537.36"
)


class AgilentSitemapAdapter(VendorAdapter):
    brand_name = "Agilent Technologies"
    brand_slug = "agilent_sitemap"
    base_url = "https://www.agilent.com"
    domain_hint = "analytical"
    rate_limit_seconds = 0.3
    user_agent_override = BROWSER_UA

    SITEMAP_URL = "https://www.agilent.com/products0.xml"
    CANONICAL_LOCALE = "en"

    # Top-level Agilent product domains (segment[2] of /product/<top>/...)
    # → (product_category_t default, product_domain_t)
    DOMAIN_MAP: dict[str, tuple[str, str]] = {
        # Analytical chromatography
        "liquid-chromatography": ("hplc_system", "analytical"),
        "liquid-chromatography-mass-spectrometry-lc-ms": ("mass_spectrometer", "analytical"),
        "gas-chromatography": ("gc_system", "analytical"),
        "gas-chromatography-mass-spectrometry-gc-ms": ("mass_spectrometer", "analytical"),
        "mass-spectrometry": ("mass_spectrometer", "analytical"),
        "gc-columns": ("gc_column", "analytical"),
        # Spectroscopy / atomic
        "atomic-spectroscopy": ("icp_ms", "analytical"),
        "molecular-spectroscopy": ("uv_vis_spectrometer", "analytical"),
        # Life Sciences / NGS / cell
        "next-generation-sequencing": ("ngs_target_capture_panel", "genetics_ngs"),
        "automated-electrophoresis": ("accessory", "genetics_ngs"),
        "polymerase-chain-reaction-(pcr)": ("realtime_pcr_kit", "life_science_general"),
        "mutagenesis-cloning": ("consumable", "life_science_general"),
        "cell-analysis": ("accessory", "life_science_general"),
        "microplate-instrumentation": ("accessory", "life_science_general"),
        "microbial-identification-mald-i-tof": ("mass_spectrometer", "analytical"),
        # Sample prep / supplies
        "sample-preparation": ("consumable", "analytical"),
        "vacuum-technologies": ("accessory", "other"),
        "software-informatics": ("software", "other"),
        "lab-supplies": ("consumable", "general_lab"),
        "chemstation": ("software", "analytical"),
        "automation-robotics": ("accessory", "life_science_general"),
        "dissolution-testing": ("accessory", "pharmaceutical"),
        "cell-imaging": ("accessory", "life_science_general"),
        # Diagnostics (Dako legacy)
        "pathology-cancer-diagnostics-research": ("other", "molecular_diagnostics"),
    }

    # Substring refinements. Checked against ENTIRE canonical path (lower).
    # Sorted longest-first at lookup — more-specific beats less-specific.
    SUBPATH_MAP: dict[str, str] = {
        # LC sub-types
        "hplc-systems": "hplc_system",
        "uhplc-systems": "hplc_system",
        "infinity-ii": "hplc_system",
        "1290-infinity": "hplc_system",
        "1260-infinity": "hplc_system",
        "1220-infinity": "hplc_system",
        "openlab-cds": "software",
        "sfc-solutions": "hplc_system",
        "gpc-sec-solutions": "hplc_system",
        "preparative-lc": "hplc_system",
        # GC sub-types
        "gc-inlets": "gc_module",
        "gc-detectors": "gc_module",
        "8890-gc": "gc_system",
        "8860-gc": "gc_system",
        "7890b-gc": "gc_system",
        "intuvo-9000": "gc_system",
        # MS sub-types
        "triple-quadrupole-lc-ms": "mass_spectrometer",
        "triple-quadrupole-gc-ms": "mass_spectrometer",
        "qtof-mass-spectrometers": "mass_spectrometer",
        "ion-mobility-mass-spectrometers": "mass_spectrometer",
        "single-quadrupole-lc-ms": "mass_spectrometer",
        "6495-triple-quadrupole-lc-ms": "mass_spectrometer",
        "6470-triple-quadrupole-lc-ms": "mass_spectrometer",
        "6230b-tof": "mass_spectrometer",
        # AAS / ICP / atomic
        "atomic-absorption-aa-spectrometers": "aas_system",
        "icp-ms-instruments": "icp_ms",
        "icp-oes-instruments": "icp_oes",
        "icp-oes": "icp_oes",
        "icp-ms": "icp_ms",
        "microwave-digestion-systems": "accessory",
        # Molecular spectroscopy
        "uv-vis-uv-vis-nir": "uv_vis_spectrometer",
        "uv-vis-spectrophotometers": "uv_vis_spectrometer",
        "cary-": "uv_vis_spectrometer",
        "ftir": "ftir_spectrometer",
        "raman": "uv_vis_spectrometer",
        # NGS
        "sureselect": "ngs_target_capture_panel",
        "ngs-library-prep-target-enrichment-reagents": "ngs_library_prep_kit",
        "bioanalyzer-systems": "accessory",
        "bioanalyzer": "accessory",
        "tapestation-systems": "accessory",
        "tapestation": "accessory",
        "magnis-ngs-prep": "accessory",
        "avenio": "ngs_target_capture_panel",
        # PCR
        "real-time-pcr-systems": "realtime_pcr_kit",
        "pcr-plastics-supplies": "consumable",
        # Sample prep / SPE
        "solid-phase-extraction-spe": "spe_cartridge",
        "spe": "spe_cartridge",
        "qa-quechers": "spe_cartridge",
        "bond-elut": "spe_cartridge",
        # Columns / vials
        "hplc-columns": "hplc_column",
        "gc-columns": "gc_column",
        "vials": "vial",
        "syringe-filter": "syringe_filter",
        "syringe-filters": "syringe_filter",
        # Vacuum
        "diffusion-pumps": "accessory",
        "rotary-vane-pumps": "accessory",
        "ion-pumps-controllers": "accessory",
        "roots-pumps-rp": "accessory",
    }

    # ---------- override run() ----------
    async def run(self, limit: int = 0, skip_existing_fresh_days: int = 30) -> dict[str, Any]:
        """Custom run — без per-URL HTTP fetch (все Agilent product pages 403).

        1. Fetch products0.xml → 9,215 URLs
        2. Dedup по locale-stripped path → ~3,844 unique
        3. Для каждого URL: parse path → VendorProductData → upsert stub
        """
        print(f"==> {self.brand_name}: sitemap-driven stub crawl")
        print(f"    sitemap URL: {self.SITEMAP_URL}")
        if self.proxy_url:
            print(f"    proxy: ***@{self.proxy_url.rsplit('@', 1)[-1] if '@' in self.proxy_url else '?'}")

        async with Fetcher(
            user_agent=self.user_agent_override,
            proxy_url=self.proxy_url,
        ) as fetcher:
            text = await fetcher.get(self.SITEMAP_URL)

        raw_urls = re.findall(r"<loc>([^<]+)</loc>", text)
        canonical_urls = self._dedup_by_locale(raw_urls)
        print(f"    sitemap: {len(raw_urls)} raw → {len(canonical_urls)} unique (locale-deduped)")

        if limit and limit > 0:
            canonical_urls = canonical_urls[:limit]
            print(f"    limited to: {len(canonical_urls)}")

        stats: dict[str, Any] = {
            "vendor": self.brand_name,
            "total": len(canonical_urls),
            "ok": 0,
            "errors": 0,
            "created_new": 0,
            "matched_existing": 0,
            "skipped_fresh": 0,
            "skipped_invalid_path": 0,
        }

        conn: asyncpg.Connection = await get_conn()
        try:
            for i, url in enumerate(canonical_urls, 1):
                try:
                    if skip_existing_fresh_days > 0:
                        existing = await conn.fetchrow(
                            """
                            SELECT id FROM product
                            WHERE brand=$1 AND source_urls @> ARRAY[$2]::text[]
                            AND updated_at > now() - ($3 || ' days')::interval
                            LIMIT 1
                            """,
                            self.brand_name, url, str(skip_existing_fresh_days),
                        )
                        if existing:
                            stats["skipped_fresh"] += 1
                            continue

                    data = self._parse_url(url)
                    if data is None:
                        stats["skipped_invalid_path"] += 1
                        continue
                    was_new = await self._upsert_stub(conn, data, url)
                    if was_new:
                        stats["created_new"] += 1
                    else:
                        stats["matched_existing"] += 1
                    stats["ok"] += 1
                    if i <= 5 or i % 500 == 0 or i == len(canonical_urls):
                        print(
                            f"  [{i:>5}/{len(canonical_urls)}] "
                            f"{(data.vendor_code or '—'):>8s}  "
                            f"{(data.group or '')[:30]:30s}  {data.model[:50]}"
                        )
                except Exception as e:
                    stats["errors"] += 1
                    if stats["errors"] <= 5:
                        print(f"  [{i:>5}] ERROR {url}: {e}")
        finally:
            await conn.close()

        await audit_event(
            action=f"vendor_crawl_complete:{self.brand_slug}",
            payload=stats,
        )

        print(f"\n==> SUMMARY {self.brand_name} (sitemap)")
        for k, v in stats.items():
            print(f"    {k}: {v}")
        return stats

    # ---------- helpers ----------
    def _dedup_by_locale(self, urls: list[str]) -> list[str]:
        """Strip /<locale>/ prefix; keep one canonical URL per product (locale=en)."""
        seen: set[str] = set()
        out: list[str] = []
        for u in urls:
            p = urlparse(u)
            parts = p.path.strip("/").split("/")
            if not parts:
                continue
            if re.fullmatch(r"[a-z]{2,3}([-_][a-z]{2,3})?", parts[0]):
                canonical_path = "/" + "/".join(parts[1:])
            else:
                canonical_path = "/" + "/".join(parts)
            if canonical_path in seen:
                continue
            seen.add(canonical_path)
            out.append(f"{self.base_url}/{self.CANONICAL_LOCALE}{canonical_path}")
        return out

    def _parse_url(self, url: str) -> VendorProductData | None:
        """Extract structured data purely from URL path — no HTTP fetch."""
        p = urlparse(url)
        parts = [s for s in p.path.strip("/").split("/") if s]
        # expect: ['en', 'product', '<top-domain>', ...intermediate, '<leaf>']
        if len(parts) < 4 or parts[1] != "product":
            return None

        top_domain = parts[2]
        leaf = parts[-1]
        intermediate = parts[3:-1]

        # numeric suffix on leaf → vendor_code  (Agilent product IDs are 4-7 digits)
        vendor_code = ""
        slug_no_id = leaf
        m = re.search(r"-(\d{4,})$", leaf)
        if m:
            vendor_code = m.group(1)
            slug_no_id = leaf[: m.start()]

        model = self._prettify_slug(slug_no_id)
        all_segments = [top_domain] + list(intermediate)
        group_full = " / ".join(self._prettify_slug(s) for s in all_segments)
        group = group_full if len(group_full) <= 200 else " / ".join(
            self._prettify_slug(s) for s in all_segments[-3:]
        )

        md_lines = [
            f"# {model}",
            "",
            f"**Производитель:** Agilent Technologies",
            f"**Артикул (sitemap-derived):** {vendor_code or '—'}",
            f"**Категория:** {self._prettify_slug(top_domain)}",
            f"**Иерархия:** {group}",
            f"**Источник:** {url}",
            "",
            "> **Stub-запись:** контент agilent.com закрыт DataDome (HTML и PDF литература).",
            "> Запись создана из публичного `products0.xml` sitemap. Описания и",
            "> технические спецификации требуют обогащения из стороннего источника",
            "> (RU дистрибьюторы — Millab, Дia-M, Хроматэк, или Labcompare через unlock-API).",
        ]
        description_md = "\n".join(md_lines)

        return VendorProductData(
            vendor_code=vendor_code[:50],
            name=model[:500],
            model=model[:200],
            group=group[:120],
            description_md=description_md,
            pdf_urls=[],
            image_urls=[],
            specs={},
            source_url=url,
            raw_metadata={
                "stub_only": True,
                "needs_enrichment": True,
                "top_domain": top_domain,
                "intermediate_path": intermediate,
                "leaf_slug": slug_no_id,
                "agilent_numeric_id": vendor_code,
            },
        )

    def _prettify_slug(self, slug: str) -> str:
        """`sample-preparation` → `Sample Preparation`, сохраняем aбревиатуры."""
        ACRONYMS = {
            "HPLC", "UHPLC", "GC", "MS", "LC", "ICP", "OES", "AAS",
            "UV", "NIR", "TOF", "QTOF", "DNA", "RNA", "PCR", "NGS",
            "SEC", "GPC", "SFC", "SPE", "II", "III", "IV",
        }
        out_parts: list[str] = []
        for tok in slug.replace("_", "-").split("-"):
            if not tok:
                continue
            if tok.isdigit():
                out_parts.append(tok)
            elif tok.upper() in ACRONYMS:
                out_parts.append(tok.upper())
            else:
                out_parts.append(tok.capitalize())
        return " ".join(out_parts)

    def _guess_category(self, data: VendorProductData) -> str:
        # 1. Substring lookup (most-specific first)
        path_lower = data.source_url.lower()
        for kw in sorted(self.SUBPATH_MAP.keys(), key=lambda s: -len(s)):
            if kw in path_lower:
                return self.SUBPATH_MAP[kw]
        # 2. Top-domain map
        top = data.raw_metadata.get("top_domain", "")
        if top in self.DOMAIN_MAP:
            return self.DOMAIN_MAP[top][0]
        return "other"

    def _guess_domain(self, data: VendorProductData) -> str:
        top = data.raw_metadata.get("top_domain", "")
        if top in self.DOMAIN_MAP:
            return self.DOMAIN_MAP[top][1]
        return self.domain_hint

    # ---------- upsert (stub-only, NO MinIO) ----------
    async def _upsert_stub(
        self,
        conn: asyncpg.Connection,
        data: VendorProductData,
        url: str,
    ) -> bool:
        """INSERT stub-only Agilent product, или UPDATE existing matched by (brand, model)."""
        category = self._guess_category(data)
        domain = self._guess_domain(data)
        content_hash = hashlib.sha256(
            f"{data.vendor_code}|{data.model}|stub".encode("utf-8")
        ).digest()

        existing = await conn.fetchrow(
            "SELECT id FROM product WHERE brand=$1 AND model=$2 LIMIT 1",
            self.brand_name, data.model[:200],
        )

        if existing:
            await conn.execute(
                """
                UPDATE product SET
                  vendor_code   = COALESCE(vendor_code, $2),
                  subcategory   = COALESCE(subcategory, $3),
                  source_urls   = (
                    SELECT array_agg(DISTINCT u)
                    FROM unnest(coalesce(source_urls, ARRAY[]::text[]) || ARRAY[$4]::text[]) AS u
                  ),
                  metadata      = coalesce(metadata, '{}'::jsonb) || $5::jsonb,
                  content_hash  = $6,
                  imported_at   = now(),
                  imported_from = COALESCE(imported_from, $7),
                  updated_at    = now()
                WHERE id = $1
                """,
                existing["id"],
                data.vendor_code or None,
                (data.group or "")[:120] or None,
                url,
                json.dumps({"agilent_sitemap": data.raw_metadata}),
                content_hash,
                self.brand_slug,
            )
            return False
        else:
            await conn.execute(
                """
                INSERT INTO product (
                  tenant_id, brand, model, vendor_code, category, domain,
                  display_name, description, subcategory,
                  source_urls, metadata, content_hash, imported_at, imported_from
                )
                VALUES ($1, $2, $3, $4, $5::product_category_t, $6::product_domain_t,
                        $7, $8, $9, $10::text[], $11::jsonb, $12, now(), $13)
                ON CONFLICT (tenant_id, brand, model) DO NOTHING
                """,
                self._tenant_id,
                self.brand_name,
                data.model[:200],
                data.vendor_code or None,
                category, domain,
                data.name[:500],
                (data.description_md or "")[:5000],
                (data.group or "")[:120] or None,
                [url],
                json.dumps(data.raw_metadata),
                content_hash,
                self.brand_slug,
            )
            return True

    # ---------- unused (override run() bypasses these) ----------
    async def list_product_urls(self, fetcher: Fetcher, limit: int = 0) -> list[str]:
        raise NotImplementedError("AgilentSitemapAdapter overrides run(); list_product_urls unused")

    async def parse_product(self, url: str, html: str) -> VendorProductData | None:
        # Not called by overridden run(), but available for tests.
        return self._parse_url(url)
