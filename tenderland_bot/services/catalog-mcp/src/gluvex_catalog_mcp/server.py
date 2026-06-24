#!/usr/bin/env python3
"""Gluvex Catalog MCP server — universal read-only access to the Gluvex catalog + RAG layer.

Powers sales/tender/product-manager agents. Backends:
  - PostgreSQL (app-db / gluvex_documents): products, base_specs (JSONB), configurations,
    sequencer runtime metrics, compatibility, document_registry/chunks (RU+EN FTS)
  - MemPalace HTTP (Qdrant, multilingual embeddings): full-corpus semantic search

Transport: stdio (default) or streamable HTTP (MCP_TRANSPORT=http).

Tool groups:
  Retrieval ........ gluvex_search_documents (semantic), gluvex_search_chunks_fts (keyword)
  Catalog .......... gluvex_search_products, gluvex_query_products_by_spec, gluvex_get_product,
                     gluvex_get_datasheets
  Sequencers ....... gluvex_find_sequencer, gluvex_resolve_oem
  Orientation ...... gluvex_catalog_overview, gluvex_list_spec_fields
"""
from __future__ import annotations

import json
import os
import re
from enum import Enum
from typing import Any, Optional

import asyncpg
import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# --------------------------------------------------------------------------- #
# Config & shared infra
# --------------------------------------------------------------------------- #
PGHOST = os.environ.get("PGHOST", "app-db")
PGUSER = os.environ.get("PGUSER", "postgres")
PGPASSWORD = os.environ.get("PGPASSWORD", "")
PGDATABASE = os.environ.get("PGDATABASE", "gluvex_documents")
MEMPALACE_URL = os.environ.get("MEMPALACE_URL", "http://mempalace-gluvex:8080")
TENANT_ID = os.environ.get("TENANT_ID", "11111111-1111-1111-1111-111111111111")

try:  # disable DNS-rebinding host check (internal stack network only)
    from mcp.server.transport_security import TransportSecuritySettings
    _ts = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    mcp = FastMCP("gluvex_catalog_mcp", transport_security=_ts)
except Exception:
    mcp = FastMCP("gluvex_catalog_mcp")
_pool: Optional[asyncpg.Pool] = None

WING_MAP = {"products": "gluvex-products", "tenders": "gluvex-tenders",
            "kp": "gluvex-kp", "clients": "gluvex-clients", "knowledge": "gluvex-knowledge"}
_KEY_RE = re.compile(r"^[A-Za-z0-9_]{1,60}$")          # safe JSONB key (anti-injection)
RO = {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(host=PGHOST, user=PGUSER, password=PGPASSWORD,
                                          database=PGDATABASE, min_size=1, max_size=6, command_timeout=40)
    return _pool


def _err(e: Exception) -> str:
    return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str, indent=2)


def _num(v):
    return float(v) if v is not None else None


class Scope(str, Enum):
    products = "products"
    tenders = "tenders"
    kp = "kp"
    clients = "clients"
    knowledge = "knowledge"
    all = "all"


class SpecOp(str, Enum):
    eq = "eq"                      # base_specs->>key == value (string-equal)
    ilike = "ilike"                # base_specs->>key ILIKE %value%
    gte = "gte"                    # numeric base_specs->>key >= value
    lte = "lte"                    # numeric base_specs->>key <= value
    range_covers = "range_covers"  # base_specs->key is [min,max]; min<=value<=max
    has_key = "has_key"            # key is present


# --------------------------------------------------------------------------- #
# 1. Semantic retrieval
# --------------------------------------------------------------------------- #
class SearchDocsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(..., min_length=2, description="Natural-language query (RU/EN). Conceptual/fuzzy. "
                       "E.g. 'фильтр для органических растворителей 0.22 мкм', 'masс-спектрометр для пестицидов'")
    scope: Scope = Field(default=Scope.all, description="Knowledge wing: 'products' (брошюры/datasheet всех 18 брендов), "
                         "'tenders' (ТЗ/закупки/предложения), 'kp','clients','knowledge','all'")
    n_results: int = Field(default=6, ge=1, le=25, description="Max chunks")


@mcp.tool(name="gluvex_search_documents", annotations={"title": "Semantic search over the whole corpus", **RO})
async def gluvex_search_documents(params: SearchDocsInput) -> str:
    """Vector/semantic search across the ENTIRE Gluvex RAG corpus (brochures of 18 vendors + tenders),
    multilingual. Best for conceptual queries. For exact part numbers/codes use gluvex_search_chunks_fts.

    Returns JSON {count, results:[{content, wing, room(brand), source_file, title, distance}]} (lower distance = closer).
    """
    try:
        wings = list(WING_MAP.values()) if params.scope == Scope.all else [WING_MAP[params.scope.value]]
        out: list[dict] = []
        async with httpx.AsyncClient(timeout=60) as c:
            for wing in wings:
                r = await c.post(f"{MEMPALACE_URL}/search",
                                 json={"query": params.query, "wing": wing, "n_results": params.n_results})
                if r.status_code >= 300:
                    continue
                for h in r.json().get("results", []):
                    m = h.get("metadata", {}) or {}
                    out.append({"content": h.get("content", ""), "wing": m.get("wing", wing),
                                "room": m.get("room", ""), "source_file": m.get("source_file", ""),
                                "title": m.get("title", ""), "distance": round(h.get("distance", 1.0), 4)})
        out.sort(key=lambda x: x["distance"])
        return _dumps({"count": len(out[:params.n_results]), "results": out[:params.n_results]})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 2. Full-text (keyword) search
# --------------------------------------------------------------------------- #
class FtsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(..., min_length=2, description="Keywords / exact terms / part numbers (RU FTS). E.g. 'MS-102-3003'")
    doc_type: Optional[str] = Field(default=None, description="Filter: 'brochure','tz','offer','price','sop','contract'...")
    brand: Optional[str] = Field(default=None, description="Brand/source filter (matches registry metadata brand or bucket)")
    limit: int = Field(default=8, ge=1, le=30)


@mcp.tool(name="gluvex_search_chunks_fts", annotations={"title": "Keyword full-text search over chunks", **RO})
async def gluvex_search_chunks_fts(params: FtsInput) -> str:
    """Russian full-text search over indexed document chunks (Postgres tsvector). Best for exact terms,
    part numbers, codes. Returns JSON {count, results:[{chunk, document_type, brand, filename, object_key, rank}]}.
    """
    try:
        rows = await (await _get_pool()).fetch("""
            SELECT c.chunk_text, dr.document_type::text dt, dr.filename, dr.object_key,
                   coalesce(dr.metadata->>'brand', dr.bucket) AS brand,
                   ts_rank(c.tsv, plainto_tsquery('russian', $1)) AS rank
            FROM document_chunks c JOIN document_registry dr ON dr.id = c.document_id
            WHERE c.tsv @@ plainto_tsquery('russian', $1)
              AND ($2::text IS NULL OR dr.document_type::text = $2)
              AND ($3::text IS NULL OR coalesce(dr.metadata->>'brand', dr.bucket) ILIKE '%'||$3||'%')
            ORDER BY rank DESC LIMIT $4
        """, params.query, params.doc_type, params.brand, params.limit)
        res = [{"chunk": r["chunk_text"][:1100], "document_type": r["dt"], "brand": r["brand"],
                "filename": r["filename"], "object_key": r["object_key"], "rank": round(float(r["rank"]), 4)} for r in rows]
        return _dumps({"count": len(res), "results": res})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 3. Product catalog search
# --------------------------------------------------------------------------- #
class ProductSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(..., min_length=1, description="Model / vendor_code / display_name substring")
    brand: Optional[str] = Field(default=None, description="Brand filter, e.g. 'Agilent Technologies','Hawach Scientific'")
    category: Optional[str] = Field(default=None, description="product_category_t, e.g. 'hplc_system','syringe_filter'")
    has_specs: bool = Field(default=False, description="Only products that have structured base_specs")
    has_datasheets: bool = Field(default=False, description="Only products with linked datasheet/brochure files")
    limit: int = Field(default=15, ge=1, le=50)
    offset: int = Field(default=0, ge=0)


@mcp.tool(name="gluvex_search_products", annotations={"title": "Search the product catalog", **RO})
async def gluvex_search_products(params: ProductSearchInput) -> str:
    """Search the catalog by text (model/vendor_code/display_name) with brand/category/has_specs/has_datasheets
    filters and pagination. Returns JSON {count, offset, has_more, results:[{brand,model,vendor_code,category,
    ru_status,display_name,has_specs,datasheet_count}]}. Use gluvex_get_product for full detail.
    """
    try:
        rows = await (await _get_pool()).fetch("""
            SELECT brand, model, vendor_code, category::text cat, ru_status::text rs, display_name,
                   (base_specs IS NOT NULL AND base_specs<>'{}'::jsonb) AS has_specs,
                   coalesce(array_length(datasheet_paths,1),0) AS ds
            FROM product
            WHERE tenant_id=$1
              AND (model ILIKE '%'||$2||'%' OR vendor_code ILIKE '%'||$2||'%' OR display_name ILIKE '%'||$2||'%')
              AND ($3::text IS NULL OR brand=$3)
              AND ($4::text IS NULL OR category::text=$4)
              AND (NOT $5 OR (base_specs IS NOT NULL AND base_specs<>'{}'::jsonb))
              AND (NOT $6 OR coalesce(array_length(datasheet_paths,1),0)>0)
            ORDER BY has_specs DESC, ds DESC, brand, model
            LIMIT $7 OFFSET $8
        """, TENANT_ID, params.query, params.brand, params.category,
             params.has_specs, params.has_datasheets, params.limit + 1, params.offset)
        more = len(rows) > params.limit
        rows = rows[:params.limit]
        res = [{"brand": r["brand"], "model": r["model"], "vendor_code": r["vendor_code"], "category": r["cat"],
                "ru_status": r["rs"], "display_name": r["display_name"], "has_specs": r["has_specs"],
                "datasheet_count": r["ds"]} for r in rows]
        return _dumps({"count": len(res), "offset": params.offset, "has_more": more, "results": res})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 4. Structured spec query (the power tool)
# --------------------------------------------------------------------------- #
class SpecFilter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(..., description="base_specs JSON key, e.g. 'membrane_material','pore_size_um','wavelength_range_nm','mass_range_mz'")
    op: SpecOp = Field(..., description="eq|ilike|gte|lte|range_covers|has_key")
    value: Optional[str] = Field(default=None, description="Comparison value (number as string for gte/lte/range_covers; omit for has_key)")


class SpecQueryInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    filters: list[SpecFilter] = Field(..., min_length=1, max_length=8,
                                       description="AND-combined conditions on base_specs (discover keys via gluvex_list_spec_fields)")
    category: Optional[str] = Field(default=None, description="Restrict to a product_category_t")
    brand: Optional[str] = Field(default=None, description="Restrict to a brand")
    text: Optional[str] = Field(default=None, description="Optional model/display_name substring narrowing")
    limit: int = Field(default=20, ge=1, le=80)


@mcp.tool(name="gluvex_query_products_by_spec", annotations={"title": "Filter products by structured specs", **RO})
async def gluvex_query_products_by_spec(params: SpecQueryInput) -> str:
    """Filter the catalog by structured base_specs conditions (AND-combined). The core tool for matching a
    method/requirement to products: e.g. syringe filters with membrane_material=PTFE & pore_size_um=0.22 &
    diameter_mm=25; UV-Vis whose wavelength_range_nm covers 340; MS with mass_range_mz>=2000.

    Ops: eq (string-equal), ilike (substring), gte/lte (numeric), range_covers (key is [min,max] array, value within),
    has_key (key present). Discover available keys per category with gluvex_list_spec_fields.

    Returns JSON {count, results:[{brand,model,vendor_code,category,ru_status, matched_specs:{...requested keys...}}]}.
    """
    try:
        clauses, args = [], [TENANT_ID]
        for f in params.filters:
            if not _KEY_RE.match(f.key):
                return _dumps({"error": f"invalid spec key: {f.key}"})
            k = f.key
            if f.op == SpecOp.has_key:
                clauses.append(f"base_specs ? '{k}'")
            elif f.op == SpecOp.eq:
                args.append(f.value); clauses.append(f"base_specs->>'{k}' = ${len(args)}")
            elif f.op == SpecOp.ilike:
                args.append(f"%{f.value}%"); clauses.append(f"base_specs->>'{k}' ILIKE ${len(args)}")
            elif f.op in (SpecOp.gte, SpecOp.lte):
                args.append(f.value)
                cmp = ">=" if f.op == SpecOp.gte else "<="
                clauses.append(f"(base_specs->>'{k}' ~ '^-?[0-9.]+$' AND (base_specs->>'{k}')::numeric {cmp} ${len(args)}::numeric)")
            elif f.op == SpecOp.range_covers:
                args.append(f.value)
                clauses.append(
                    f"(jsonb_typeof(base_specs->'{k}')='array' "
                    f"AND (base_specs->'{k}'->>0) ~ '^-?[0-9.]+$' AND (base_specs->'{k}'->>1) ~ '^-?[0-9.]+$' "
                    f"AND (base_specs->'{k}'->>0)::numeric <= ${len(args)}::numeric "
                    f"AND (base_specs->'{k}'->>1)::numeric >= ${len(args)}::numeric)")
        where = " AND ".join(clauses)
        cat_arg = bra_arg = txt_arg = "NULL"
        args.append(params.category); cat_i = len(args)
        args.append(params.brand); bra_i = len(args)
        args.append(params.text); txt_i = len(args)
        args.append(params.limit); lim_i = len(args)
        keys = [f.key for f in params.filters]
        sql = f"""
            SELECT brand, model, vendor_code, category::text cat, ru_status::text rs,
                   jsonb_object_agg(kv.k, base_specs->kv.k) FILTER (WHERE base_specs ? kv.k) AS matched
            FROM product, unnest($%d::text[]) AS kv(k)
            WHERE tenant_id=$1 AND base_specs IS NOT NULL AND base_specs<>'{{}}'::jsonb
              AND ({where})
              AND (${cat_i}::text IS NULL OR category::text=${cat_i})
              AND (${bra_i}::text IS NULL OR brand=${bra_i})
              AND (${txt_i}::text IS NULL OR model ILIKE '%%'||${txt_i}||'%%' OR display_name ILIKE '%%'||${txt_i}||'%%')
            GROUP BY brand, model, vendor_code, category, ru_status
            ORDER BY brand, model
            LIMIT ${lim_i}
        """ % (len(args) + 1)
        args.append(keys)
        rows = await (await _get_pool()).fetch(sql, *args)
        res = [{"brand": r["brand"], "model": r["model"], "vendor_code": r["vendor_code"], "category": r["cat"],
                "ru_status": r["rs"], "matched_specs": json.loads(r["matched"]) if r["matched"] else {}} for r in rows]
        return _dumps({"count": len(res), "filters": [f.model_dump() for f in params.filters], "results": res})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 5. Full product detail (universal)
# --------------------------------------------------------------------------- #
class GetProductInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    vendor_code: Optional[str] = Field(default=None, description="Exact vendor part number (preferred)")
    model: Optional[str] = Field(default=None, description="Model name/substring (used if vendor_code absent)")
    brand: Optional[str] = Field(default=None, description="Optional brand to disambiguate")


@mcp.tool(name="gluvex_get_product", annotations={"title": "Full product detail (specs, configs, OEM, datasheets)", **RO})
async def gluvex_get_product(params: GetProductInput) -> str:
    """Full detail for one product (any category): base_specs, datasheets, configurations (with specs),
    sequencer runtime metrics (if a platform), compatibility, OEM resolution + RU equivalents, РУ status.
    Look up by vendor_code (exact) or model (best match). Returns a rich JSON object.
    """
    try:
        pool = await _get_pool()
        if params.vendor_code:
            p = await pool.fetchrow("""SELECT * FROM product WHERE tenant_id=$1 AND vendor_code=$2
                AND ($3::text IS NULL OR brand=$3) LIMIT 1""", TENANT_ID, params.vendor_code, params.brand)
        else:
            p = await pool.fetchrow("""SELECT * FROM product WHERE tenant_id=$1
                AND (model ILIKE $2 OR model ILIKE '%'||$2||'%')
                AND ($3::text IS NULL OR brand=$3)
                ORDER BY (model ILIKE $2) DESC, (base_specs<>'{}'::jsonb) DESC LIMIT 1""",
                TENANT_ID, params.model or "", params.brand)
        if not p:
            return _dumps({"error": "product not found"})
        out: dict = {"brand": p["brand"], "model": p["model"], "vendor_code": p["vendor_code"],
                     "category": p["category"], "display_name": p["display_name"], "description": p["description"],
                     "ru_status": p["ru_status"], "ru_number": p["ru_number"],
                     "base_specs": p["base_specs"], "datasheets": list(p["datasheet_paths"] or [])}
        # OEM
        if p["oem_of_id"]:
            orig = await pool.fetchrow("SELECT brand, model FROM product WHERE id=$1", p["oem_of_id"])
            out["oem_of"] = {"brand": orig["brand"], "model": orig["model"]} if orig else None
        ru_eq = await pool.fetch("SELECT brand, model, ru_status::text rs, ru_number FROM product WHERE oem_of_id=$1", p["id"])
        if ru_eq:
            out["ru_equivalents"] = [{"brand": r["brand"], "model": r["model"], "ru_status": r["rs"], "ru_number": r["ru_number"]} for r in ru_eq]
        # configurations
        cfgs = await pool.fetch("""SELECT config_type::text ct, configuration_code, name, specs
            FROM product_configuration WHERE product_id=$1 ORDER BY name LIMIT 60""", p["id"])
        if cfgs:
            out["configurations"] = [{"type": c["ct"], "code": c["configuration_code"], "name": c["name"], "specs": c["specs"]} for c in cfgs]
        # sequencer runtime metrics
        mets = await pool.fetch("""SELECT read_mode, cycles, total_reads_million_typ rm, total_output_gb_max gb,
            q30_pct q30, q40_pct q40, run_time_hours_max rt, applications, source_confidence conf
            FROM sequencer_runtime_metric WHERE sequencer_id=$1 ORDER BY total_output_gb_max NULLS LAST LIMIT 60""", p["id"])
        if mets:
            out["runtime_metrics"] = [{"read_mode": m["read_mode"], "cycles": m["cycles"],
                "reads_million": _num(m["rm"]), "output_gb_max": _num(m["gb"]), "q30": _num(m["q30"]),
                "q40": _num(m["q40"]), "run_time_h": _num(m["rt"]), "applications": list(m["applications"] or []),
                "source_confidence": _num(m["conf"])} for m in mets]
        # slots
        slots = await pool.fetch("SELECT slot_name, slot_role, min_count, max_count, required FROM product_slot WHERE product_id=$1", p["id"])
        if slots:
            out["slots"] = [dict(s) for s in slots]
        return _dumps(out)
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 6. Datasheets
# --------------------------------------------------------------------------- #
class DatasheetInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    vendor_code: Optional[str] = Field(default=None, description="Exact vendor part number")
    model: Optional[str] = Field(default=None, description="Model substring (if vendor_code absent)")


@mcp.tool(name="gluvex_get_datasheets", annotations={"title": "Datasheet/brochure file paths for a product", **RO})
async def gluvex_get_datasheets(params: DatasheetInput) -> str:
    """Return MinIO object keys of datasheet/brochure PDFs linked to a product. Look up by vendor_code or model.
    Returns JSON {count, products:[{brand,model,vendor_code,datasheets:[object_key,...]}]}.
    """
    try:
        if not params.vendor_code and not params.model:
            return _dumps({"error": "provide vendor_code or model"})
        rows = await (await _get_pool()).fetch("""
            SELECT brand, model, vendor_code, datasheet_paths FROM product
            WHERE tenant_id=$1 AND coalesce(array_length(datasheet_paths,1),0)>0
              AND ( ($2::text IS NOT NULL AND vendor_code=$2) OR ($2::text IS NULL AND model ILIKE '%'||$3||'%') )
            LIMIT 25
        """, TENANT_ID, params.vendor_code, params.model)
        res = [{"brand": r["brand"], "model": r["model"], "vendor_code": r["vendor_code"],
                "datasheets": list(r["datasheet_paths"] or [])} for r in rows]
        return _dumps({"count": len(res), "products": res})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 7. Sequencer configurator
# --------------------------------------------------------------------------- #
class FindSeqInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    min_output_gb: Optional[float] = Field(default=None, ge=0, description="Min output per run (Gb, on max value)")
    max_output_gb: Optional[float] = Field(default=None, ge=0, description="Max output cap (Gb)")
    read_mode_like: Optional[str] = Field(default=None, description="Read-mode substring: '150','PE150','2x150','SE100'")
    application: Optional[str] = Field(default=None, description="App keyword: 'WGS','exome','RNA','amplicon','NIPT','single-cell'")
    brand: Optional[str] = Field(default=None, description="'Illumina','MGI Tech','GeneMind','Salus BioMed'")
    ru_only: bool = Field(default=False, description="Only platforms with a Russian-registered OEM equivalent")
    min_q30: Optional[float] = Field(default=None, ge=0, le=100)
    limit: int = Field(default=15, ge=1, le=50)


@mcp.tool(name="gluvex_find_sequencer", annotations={"title": "Find sequencer configurations by requirements", **RO})
async def gluvex_find_sequencer(params: FindSeqInput) -> str:
    """Sequencer configurator: find platform + reagent-kit/flow-cell configs matching output, read mode,
    application, brand, %Q30, RU registration. Ranked by output ascending (smallest sufficient first). Resolves
    RU OEM equivalents (Геноскан/Helicon/БиоФьюжн). source_confidence<0.8 = interpolated/unconfirmed value.

    Returns JSON {count, results:[{brand,platform,kit,part_code,read_mode,cycles,reads_million,output_gb_typ,
    output_gb_max,q30,q40,run_time_h,applications,ru_equivalent,ru_status,ru_number,source_confidence}]}.
    """
    try:
        rows = await (await _get_pool()).fetch("""
        WITH ru AS (SELECT oem_of_id, brand AS rb, model AS rm, ru_status::text rs, ru_number FROM product
                    WHERE tenant_id=$1 AND category='sequencer_platform' AND oem_of_id IS NOT NULL)
        SELECT p.brand, p.model platform, pc.name kit, pc.configuration_code part_code, m.read_mode, m.cycles,
               m.total_reads_million_typ rm, m.total_output_gb_typ gt, m.total_output_gb_max gx,
               m.q30_pct q30, m.q40_pct q40, m.run_time_hours_max rt, m.applications, m.source_confidence conf,
               ru.rb, ru.rm AS rmod, ru.rs, ru.ru_number
        FROM sequencer_runtime_metric m
        JOIN product p ON p.id=m.sequencer_id
        JOIN product_configuration pc ON pc.id=m.reagent_kit_id
        LEFT JOIN ru ON ru.oem_of_id=p.id
        WHERE m.notes='ngs_seed_v2'
          AND ($2::numeric IS NULL OR m.total_output_gb_max>=$2)
          AND ($3::numeric IS NULL OR m.total_output_gb_max<=$3)
          AND ($4::text IS NULL OR m.read_mode ILIKE '%'||$4||'%')
          AND ($5::text IS NULL OR EXISTS(SELECT 1 FROM unnest(m.applications) a WHERE a ILIKE '%'||$5||'%'))
          AND ($6::text IS NULL OR p.brand=$6)
          AND ($7::numeric IS NULL OR m.q30_pct>=$7)
          AND (NOT $8 OR ru.rb IS NOT NULL)
        ORDER BY m.total_output_gb_max ASC, p.brand LIMIT $9
        """, TENANT_ID, params.min_output_gb, params.max_output_gb, params.read_mode_like,
             params.application, params.brand, params.min_q30, params.ru_only, params.limit)
        res = [{"brand": r["brand"], "platform": r["platform"], "kit": r["kit"], "part_code": r["part_code"],
                "read_mode": r["read_mode"], "cycles": r["cycles"], "reads_million": _num(r["rm"]),
                "output_gb_typ": _num(r["gt"]), "output_gb_max": _num(r["gx"]), "q30": _num(r["q30"]),
                "q40": _num(r["q40"]), "run_time_h": _num(r["rt"]), "applications": list(r["applications"] or []),
                "ru_equivalent": (f"{r['rb']} {r['rmod']}" if r["rb"] else None), "ru_status": r["rs"],
                "ru_number": r["ru_number"], "source_confidence": _num(r["conf"])} for r in rows]
        return _dumps({"count": len(res), "results": res})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 8. OEM resolution
# --------------------------------------------------------------------------- #
class OemInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    model: str = Field(..., min_length=2, description="Any model (original or RU rebrand)")


@mcp.tool(name="gluvex_resolve_oem", annotations={"title": "Resolve OEM rebrand <-> original", **RO})
async def gluvex_resolve_oem(params: OemInput) -> str:
    """Resolve OEM relations for a model: maps a Russian rebrand to the original manufacturer model and lists all
    RU equivalents with РУ. Returns JSON {query, original:{brand,model}, ru_equivalents:[{brand,model,ru_status,ru_number}]}.
    """
    try:
        pool = await _get_pool()
        row = await pool.fetchrow("""SELECT id, brand, model, oem_of_id FROM product
            WHERE tenant_id=$1 AND category='sequencer_platform' AND (model ILIKE $2 OR model ILIKE '%'||$2||'%')
            ORDER BY (model ILIKE $2) DESC LIMIT 1""", TENANT_ID, params.model)
        if not row:
            return _dumps({"error": f"model not found: {params.model}"})
        oid = row["oem_of_id"] or row["id"]
        orig = await pool.fetchrow("SELECT brand, model FROM product WHERE id=$1", oid)
        ru = await pool.fetch("SELECT brand, model, ru_status::text rs, ru_number FROM product WHERE oem_of_id=$1", oid)
        return _dumps({"query": params.model, "original": {"brand": orig["brand"], "model": orig["model"]},
                       "ru_equivalents": [{"brand": r["brand"], "model": r["model"], "ru_status": r["rs"], "ru_number": r["ru_number"]} for r in ru]})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 9. Catalog overview (orientation)
# --------------------------------------------------------------------------- #
class OverviewInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    by: str = Field(default="category", description="Group products by 'category' or 'brand'")
    brand: Optional[str] = Field(default=None, description="Optional brand filter (when by='category')")
    top: int = Field(default=30, ge=1, le=100)


@mcp.tool(name="gluvex_catalog_overview", annotations={"title": "Catalog & corpus coverage overview", **RO})
async def gluvex_catalog_overview(params: OverviewInput) -> str:
    """Orientation map of the base: product counts with spec/datasheet coverage grouped by category or brand,
    plus RAG corpus size (documents by type). Use first to understand what's available before querying.

    Returns JSON {products:[{group,total,with_specs,with_datasheets}], rag:{by_type:{...}, total_chunks}}.
    """
    try:
        pool = await _get_pool()
        col = "brand" if params.by == "brand" else "category::text"
        prod = await pool.fetch(f"""
            SELECT {col} AS grp, count(*) total,
                   count(*) FILTER (WHERE base_specs IS NOT NULL AND base_specs<>'{{}}'::jsonb) ws,
                   count(*) FILTER (WHERE coalesce(array_length(datasheet_paths,1),0)>0) wd
            FROM product WHERE tenant_id=$1 AND ($2::text IS NULL OR brand=$2)
            GROUP BY 1 ORDER BY total DESC LIMIT $3""", TENANT_ID, params.brand, params.top)
        rag = await pool.fetch("SELECT document_type::text dt, count(*) n FROM document_registry GROUP BY 1 ORDER BY 2 DESC")
        chunks = await pool.fetchval("SELECT count(*) FROM document_chunks")
        return _dumps({"products": [{"group": r["grp"], "total": r["total"], "with_specs": r["ws"], "with_datasheets": r["wd"]} for r in prod],
                       "rag": {"by_type": {r["dt"]: r["n"] for r in rag}, "total_chunks": chunks}})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
# 10. Discover spec fields
# --------------------------------------------------------------------------- #
class SpecFieldsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    category: str = Field(..., description="product_category_t, e.g. 'syringe_filter','uv_vis_spectrometer','mass_spectrometer'")
    brand: Optional[str] = Field(default=None)
    top: int = Field(default=30, ge=1, le=80)


@mcp.tool(name="gluvex_list_spec_fields", annotations={"title": "Discover base_specs keys for a category", **RO})
async def gluvex_list_spec_fields(params: SpecFieldsInput) -> str:
    """List the most common base_specs keys (with frequency and sample values) for a category — so you know what
    is filterable before calling gluvex_query_products_by_spec. Returns JSON {category, products_with_specs,
    fields:[{key, freq, samples:[..]}]}.
    """
    try:
        pool = await _get_pool()
        n = await pool.fetchval("""SELECT count(*) FROM product WHERE tenant_id=$1 AND category::text=$2
            AND base_specs<>'{}'::jsonb AND ($3::text IS NULL OR brand=$3)""", TENANT_ID, params.category, params.brand)
        rows = await pool.fetch("""
            WITH kv AS (
              SELECT key, value FROM product, jsonb_each(base_specs)
              WHERE tenant_id=$1 AND category::text=$2 AND base_specs<>'{}'::jsonb AND ($3::text IS NULL OR brand=$3)
            )
            SELECT key, count(*) freq, (array_agg(DISTINCT left(value::text,40)))[1:4] samples
            FROM kv GROUP BY key ORDER BY freq DESC LIMIT $4
        """, TENANT_ID, params.category, params.brand, params.top)
        return _dumps({"category": params.category, "products_with_specs": n,
                       "fields": [{"key": r["key"], "freq": r["freq"], "samples": list(r["samples"] or [])} for r in rows]})
    except Exception as e:
        return _err(e)


# --------------------------------------------------------------------------- #
def main() -> None:
    if os.environ.get("MCP_TRANSPORT", "stdio") == "http":
        mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.environ.get("MCP_PORT", "8090"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()
