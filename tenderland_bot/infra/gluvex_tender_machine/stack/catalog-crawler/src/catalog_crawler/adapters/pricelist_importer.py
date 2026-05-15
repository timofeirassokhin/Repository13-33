"""Pricelist JSON → product table importer.

Принимает JSON созданный `tools/parse_pricelist_pdf.py`, маппит category_section
на product_category_t и UPSERT'ит каждую запись в `product` таблицу.

Use case (главный): Illumina ScientiGen Pricelist Feb 2026 — 2896 артикулов
с реальными ценами + категорийная классификация. После импорта эти продукты
становятся целью для brochure-web pipeline (PDF datasheet search).

Запуск:
  docker compose run --rm \
      -v /opt/gluvex/pricelists:/pricelists:ro \
      catalog-crawler pricelist-import /pricelists/scientigen.json --brand Illumina
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

import asyncpg

from catalog_crawler.core.db import audit_event, get_conn
from catalog_crawler.settings import Settings

log = logging.getLogger(__name__)


# === Маппинг ScientiGen-категорий на product_category_t ===
#
# Illumina-специфичные категории (можем дополнять по мере появления новых
# pricelist'ов от других дистрибьюторов).
#
# Все остальные категории → 'other' (попадают как stub с category_section в metadata).

CATEGORY_MAP: dict[str, str] = {
    # Главные приборы
    "systems and instruments": "sequencer_platform",
    "instruments": "sequencer_platform",
    "sequencer": "sequencer_platform",
    "system": "sequencer_platform",
    # Реагентные наборы для секвенирования
    "library prep core": "ngs_library_prep_kit",
    "ampliseq lib prep": "ngs_amplicon_panel",
    "rna lib prep": "ngs_library_prep_kit",
    "single cell lib prep": "ngs_library_prep_kit",
    "targeted enrichment sequencing lib prep": "ngs_target_capture_panel",
    "tso 500 / 170 library prep reagents": "ngs_target_capture_panel",
    "tso 500": "ngs_target_capture_panel",
    "tso 170": "ngs_target_capture_panel",
    "pillar library prep": "ngs_library_prep_kit",
    "custom/semi-custom products": "ngs_target_capture_panel",
    "trusight": "ngs_target_capture_panel",
    "truseq": "ngs_library_prep_kit",
    "nextera": "ngs_library_prep_kit",
    # Reagent kits специфичные для платформ
    "miseq reagent kit": "sequencer_reagent_kit",
    "novaseq reagent kit": "sequencer_reagent_kit",
    "nextseq reagent kit": "sequencer_reagent_kit",
    "iseq reagent kit": "sequencer_reagent_kit",
    "reagent": "sequencer_reagent_kit",
    "reagent kit": "sequencer_reagent_kit",
    # Flow cells
    "flow cell": "sequencer_flowcell",
    "flowcell": "sequencer_flowcell",
    # Microarray
    "global genotyping arrays": "other",       # пока нет microarray category
    "infinium": "other",
    "bead chip": "other",
    "beadchip": "other",
    "iscan": "sequencer_platform",
    # Software
    "dragen sw lic and subsriptions": "software",
    "dragen": "software",
    "partek software": "software",
    "software": "software",
    "license": "software",
    # Services
    "bronze service contract": "service",
    "silver service contract": "service",
    "gold service contract": "service",
    "platinum service contract": "service",
    "support plan": "service",
    "qualification services": "service",
    "training": "service",
    "channel partner services": "service",
    "billable services": "service",
    "product care plans": "service",
    "service": "service",
    "warranty": "service",
    # Расходники / запчасти
    "spares": "spare_part",
    "spare": "spare_part",
    "consumable": "consumable",
    "consumables": "consumable",
    "accessory": "accessory",
    "accessories": "accessory",
}


def map_category(section: str) -> tuple[str, str]:
    """Returns (product_category, subcategory) tuple.

    product_category — значение `product_category_t` ENUM (default 'other').
    subcategory — оригинальный section текст (raw, для filtering позже).
    """
    if not section:
        return ("other", "")
    s = section.lower().strip()
    if s in CATEGORY_MAP:
        return (CATEGORY_MAP[s], section)
    # Подстрока — например "MiSeq Reagent Kit v3" должен match "reagent kit"
    for key, cat in CATEGORY_MAP.items():
        if key in s:
            return (cat, section)
    return ("other", section)


# === Model extraction из description ===

# Эвристика: первые 2-5 слов до запятой или скобки.
# "AmpliSeq™ Library PLUS (24 Reactions) for Illumina®" → "AmpliSeq Library PLUS"
# "NovaSeq 6000Dx Bronze Support Plan" → "NovaSeq 6000Dx"

_TRADEMARK_RE = re.compile(r"[™®©]")


def extract_model(description: str) -> str:
    if not description:
        return ""
    d = _TRADEMARK_RE.sub("", description)
    # Берём до первой "(" или ","
    m = re.match(r"^([^(,]+)", d)
    if m:
        d = m.group(1).strip()
    # Чистим артефакты "for Illumina" в конце
    d = re.sub(r"\s+for\s+Illumina\s*$", "", d, flags=re.IGNORECASE)
    d = re.sub(r"\s+", " ", d).strip()
    # Обрезаем до 80 символов
    return d[:80]


# === Main import pipeline ===

async def import_pricelist_json(
    settings: Settings,
    *,
    json_path: Path,
    brand: str = "Illumina",
    imported_from: str = "scientigen_pricelist",
    distributor_name: str = "ScientiGen",
    dry_run: bool = False,
):
    """Импорт списка артикулов из JSON в `product` таблицу.

    UPSERT: при коллизии по (tenant_id, brand, model) — обновляются vendor_code,
    metadata, source_urls. content_hash используется для dedup при ре-импорте.
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    log.info("imported_from=%s brand=%s items=%d", imported_from, brand, len(items))

    if not items:
        log.warning("no items in JSON, exit")
        return

    if dry_run:
        log.info("DRY-RUN — first 5 records preview:")
        for it in items[:5]:
            cat, sub = map_category(it.get("category_section", ""))
            model = extract_model(it.get("description", ""))
            log.info("  vendor_code=%s model=%r category=%s section=%r price=%s",
                     it["catalog_number"], model, cat, sub,
                     it.get("customer_price_usd"))
        return

    conn: asyncpg.Connection = await get_conn()
    stats = {"inserted": 0, "updated": 0, "errors": 0, "skipped": 0}

    # tenant_id — константа (как в adapters/vendors/base.py:69)
    # У нас single-tenant система, нет таблицы tenant.
    tenant_id = "11111111-1111-1111-1111-111111111111"
    log.info("tenant_id=%s", tenant_id)

    try:

        for it in items:
            vendor_code = it["catalog_number"]
            description = (it.get("description") or "").strip()
            section = it.get("category_section", "")
            extracted_model = extract_model(description) or vendor_code
            # Unique constraint в БД на (tenant_id, brand, model). Каждый
            # vendor_code — отдельный товар → append vendor_code в model:
            # "AmpliSeq Library PLUS [20019101]" — гарантирует уникальность.
            model = f"{extracted_model} [{vendor_code}]"[:200]
            display_name = f"{brand} {extracted_model} ({vendor_code})"[:200]

            category, subcategory = map_category(section)
            list_price = it.get("list_price_usd")
            cust_price = it.get("customer_price_usd")
            is_quote = it.get("is_quote_only", False)
            page = it.get("page", 0)

            metadata = {
                "list_price_usd": list_price,
                "customer_price_usd": cust_price,
                "is_quote_only": is_quote,
                "source_pdf": data.get("source_pdf", ""),
                "source_page": page,
                "category_section": section,
                "distributor": distributor_name,
                "stub_from_pricelist": True,
                "needs_brochure": True,
            }

            try:
                # UPSERT через (tenant_id, brand, vendor_code) — если уже есть запись
                # с этим vendor_code в каталоге — обновляем metadata, иначе создаём.
                # Используем INSERT ... ON CONFLICT DO UPDATE pattern.
                existing = await conn.fetchrow(
                    """
                    SELECT id, datasheet_paths, metadata
                    FROM product
                    WHERE tenant_id = $1 AND brand = $2 AND vendor_code = $3
                    LIMIT 1
                    """,
                    tenant_id, brand, vendor_code,
                )

                if existing:
                    # Update — сохраняем существующие datasheet_paths, мерджим metadata
                    raw_meta = existing["metadata"] or {}
                    if isinstance(raw_meta, str):
                        try:
                            raw_meta = json.loads(raw_meta)
                        except Exception:
                            raw_meta = {}
                    merged_metadata = {**raw_meta, **metadata}
                    await conn.execute(
                        """
                        UPDATE product
                        SET model = COALESCE(NULLIF(model, ''), $2),
                            display_name = COALESCE(NULLIF(display_name, ''), $3),
                            description = COALESCE(NULLIF(description, ''), $4),
                            category = $5::product_category_t,
                            subcategory = $6,
                            metadata = $7::jsonb,
                            updated_at = now()
                        WHERE id = $1
                        """,
                        existing["id"],
                        model, display_name, description, category, subcategory,
                        json.dumps(merged_metadata, ensure_ascii=False),
                    )
                    stats["updated"] += 1
                else:
                    await conn.execute(
                        """
                        INSERT INTO product (
                            tenant_id, brand, model, vendor_code,
                            display_name, description,
                            category, subcategory, domain,
                            metadata, source_urls,
                            imported_at, imported_from
                        ) VALUES (
                            $1, $2, $3, $4,
                            $5, $6,
                            $7::product_category_t, $8, $9::product_domain_t,
                            $10, $11,
                            now(), $12
                        )
                        """,
                        tenant_id, brand, model, vendor_code,
                        display_name, description,
                        category, subcategory, "genetics_ngs",
                        json.dumps(metadata, ensure_ascii=False),
                        [data.get("source_pdf", "")],
                        imported_from,
                    )
                    stats["inserted"] += 1

                if (stats["inserted"] + stats["updated"]) % 200 == 0:
                    log.info("progress: %s", stats)

            except Exception as exc:
                stats["errors"] += 1
                log.warning("failed for %s: %s", vendor_code, exc)

        # Final audit event (open separate conn — audit_event opens own connection)
        log.info("DONE. Final stats: %s", stats)

    finally:
        await conn.close()

    # Audit event после закрытия — audit_event имеет свой conn
    try:
        await audit_event(
            action="pricelist_imported",
            actor_type="catalog_crawler",
            actor_id="pricelist_importer",
            payload={
                "imported_from": imported_from,
                "brand": brand,
                "distributor": distributor_name,
                "source_pdf": data.get("source_pdf", ""),
                "stats": stats,
            },
        )
    except Exception as exc:
        log.warning("audit_event failed: %s", exc)
