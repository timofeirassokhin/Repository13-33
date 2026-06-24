#!/usr/bin/env python3
"""Wave 2 — LLM extraction of structured instrument specs from RAG brochure text into product.base_specs.

For each anchor instrument (category filter) that has linked datasheets but empty base_specs:
  1. gather chunk_text of its linked brochures (document_chunks via object_key in datasheet_paths)
  2. ask LiteLLM (model 'creative'=Sonnet) to extract a strict JSON of specs (ranges+units, part numbers,
     throughput, wavelength/mass/temp, applications, RU summary) using ONLY facts from the text
  3. write JSON into product.base_specs (+ metadata.specs_extracted), set description if empty

Idempotent: processes only rows with empty base_specs unless FORCE=1.
Env: PGHOST/PGUSER/PGPASSWORD/PGDATABASE, LITELLM_URL, LITELLM_KEY, MODEL, CATEGORY, LIMIT, DRY, CONCURRENCY.
"""
from __future__ import annotations
import os, re, json, asyncio
import asyncpg, httpx

TENANT = os.environ.get("TENANT_ID", "11111111-1111-1111-1111-111111111111")
LITELLM_URL = os.environ.get("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY = os.environ["LITELLM_KEY"]
MODEL = os.environ.get("MODEL", "creative")
CATEGORY = os.environ.get("CATEGORY", "")          # comma-separated categories; empty = default anchor set
BRANDS = os.environ.get("BRANDS", "")              # comma-separated brand filter (optional)
MODE = os.environ.get("MODE", "datasheet")          # 'datasheet' (RAG brochure text) | 'names' (model+desc)
LIMIT = int(os.environ.get("LIMIT", "0"))           # 0 = no limit
DRY = os.environ.get("DRY", "0") == "1"
CONC = int(os.environ.get("CONCURRENCY", "4"))
MAX_TEXT = int(os.environ.get("MAX_TEXT", "14000"))

ANCHORS = ["hplc_system", "hplc_pump", "hplc_autosampler", "hplc_column_oven", "hplc_detector",
           "gc_system", "gc_module", "mass_spectrometer", "icp_ms", "icp_oes", "aas_system",
           "uv_vis_spectrometer", "ftir_spectrometer", "nir_spectrometer",
           "balance", "centrifuge", "climate_chamber", "drying_oven", "incubator", "titrator"]

SYS_PROMPT = (
    "You extract structured technical specifications of laboratory/analytical instruments AND consumables "
    "(syringe/membrane filters, vials, septa, caps, SPE cartridges, columns, glassware, fume-hood filters) "
    "from product names/descriptions or brochure text for a distributor catalog used by a configurator agent. "
    "For consumables capture keys like membrane_material, pore_size_um, diameter_mm, sterile (bool), "
    "volume_ml, pack_size, filter_type, vial_size_ml, thread_mm, septum_material, column_phase, "
    "particle_size_um, column_dimensions_mm, carbon_filter_type. RULES: (1) Use ONLY facts "
    "explicitly present in the provided text — never invent or infer beyond it. (2) Output STRICT minified "
    "JSON, no markdown, no commentary. (3) Put units into key names (e.g. pressure_max_bar, "
    "wavelength_range_nm, mass_range_mz, temp_range_c, flow_rate_ml_min, samples_per_run, scan_speed_nm_min). "
    "(4) Values may be numbers, strings, ranges as [min,max], or arrays. Use null/omit if absent. "
    "(5) ALWAYS include arrays \"catalog_numbers\" (part/order numbers found) and \"applications\" "
    "(methods/uses), and \"summary_ru\" (1-2 sentence Russian description of the instrument and its niche). "
    "(6) Capture every spec relevant to choosing the instrument for a method: ranges, throughput, "
    "detectors, channels, resolution, detection limits, sensitivity, options/modules."
)


def _clean_json(s: str) -> dict:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s).strip()
    # grab outermost braces
    i, j = s.find("{"), s.rfind("}")
    if i >= 0 and j > i:
        s = s[i:j + 1]
    return json.loads(s)


async def _gather_text(pool, object_keys: list[str]) -> str:
    if not object_keys:
        return ""
    rows = await pool.fetch("""
        SELECT c.chunk_text FROM document_chunks c
        JOIN document_registry dr ON dr.id = c.document_id
        WHERE dr.object_key = ANY($1::text[])
           OR (dr.bucket || '/' || dr.object_key) = ANY($1::text[])
        ORDER BY dr.object_key, c.chunk_index
    """, object_keys)
    text = "\n".join(r["chunk_text"] for r in rows)
    return text[:MAX_TEXT]


async def _llm(client: httpx.AsyncClient, brand: str, model: str, cat: str, text: str) -> dict | None:
    user = (f"Instrument: {brand} {model} | category: {cat}\n\n"
            f"Brochure text:\n{text}\n\n"
            "Return the specifications JSON now.")
    r = await client.post(f"{LITELLM_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        json={"model": MODEL, "temperature": 0, "max_tokens": int(os.environ.get("MAX_TOKENS", "2000")),
              "messages": [{"role": "system", "content": SYS_PROMPT},
                           {"role": "user", "content": user}]})
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return _clean_json(content)


async def _worker(name, pool, client, queue, stats):
    while True:
        try:
            row = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        pid, brand, model, cat, keys = row["id"], row["brand"], row["model"], row["cat"], row["datasheet_paths"]
        try:
            if MODE == "names":
                text = "\n".join(filter(None, [row.get("model"), row.get("display_name"), row.get("description")]))
                min_len = 8
            else:
                text = await _gather_text(pool, list(keys or []))
                min_len = 120
            if len(text.strip()) < min_len:
                stats["no_text"] += 1
                continue
            specs = await _llm(client, brand, model, cat, text)
            if not isinstance(specs, dict) or not specs:
                stats["empty"] += 1
                continue
            summary = specs.get("summary_ru")
            if not DRY:
                await pool.execute("""
                    UPDATE product SET
                      base_specs = coalesce(base_specs,'{}'::jsonb) || $2::jsonb,
                      description = coalesce(NULLIF(description,''), $3),
                      metadata = coalesce(metadata,'{}'::jsonb) || jsonb_build_object('specs_extracted','wave2_v1'),
                      updated_at = now()
                    WHERE id = $1
                """, pid, json.dumps(specs, ensure_ascii=False), summary)
            stats["done"] += 1
            if stats["done"] <= 3 or stats["done"] % 25 == 0:
                print(f"  [{stats['done']}] {brand} {model[:40]} -> {len(specs)} fields; cat#={len(specs.get('catalog_numbers',[]))}", flush=True)
        except Exception as e:
            stats["errors"] += 1
            print(f"  ERR {brand} {model[:30]}: {type(e).__name__}: {str(e)[:120]}", flush=True)


async def main():
    cats = [c.strip() for c in CATEGORY.split(",") if c.strip()] or ANCHORS
    pool = await asyncpg.create_pool(host=os.environ.get("PGHOST", "app-db"),
        user=os.environ.get("PGUSER", "postgres"), password=os.environ["PGPASSWORD"],
        database=os.environ.get("PGDATABASE", "gluvex_documents"), min_size=2, max_size=max(CONC + 1, 4))
    brands = [b.strip() for b in BRANDS.split(",") if b.strip()]
    exclude = [c.strip() for c in os.environ.get("EXCLUDE_CAT", "").split(",") if c.strip()]
    all_cats = "__all__" in cats
    where_force = "" if os.environ.get("FORCE") == "1" else "AND (base_specs IS NULL OR base_specs='{}'::jsonb)"
    ds_req = "" if MODE == "names" else "AND coalesce(array_length(datasheet_paths,1),0) > 0"
    args = [TENANT]
    cat_req = ""
    if not all_cats:
        args.append(cats); cat_req = f"AND category::text = ANY(${len(args)}::text[])"
    brand_req = ""
    if brands:
        args.append(brands); brand_req = f"AND brand = ANY(${len(args)}::text[])"
    excl_req = ""
    if exclude:
        args.append(exclude); excl_req = f"AND category::text <> ALL(${len(args)}::text[])"
    min_model = "AND length(coalesce(model,''))>6" if MODE == "names" else ""
    sql = f"""
        SELECT id, brand, model, category::text AS cat, datasheet_paths, display_name, description
        FROM product
        WHERE tenant_id=$1 {cat_req} {ds_req} {brand_req} {excl_req} {min_model} {where_force}
        ORDER BY brand, category, model
        {('LIMIT ' + str(LIMIT)) if LIMIT else ''}
    """
    rows = await pool.fetch(sql, *args)
    print(f"targets: {len(rows)} | mode={MODE} | model={MODEL} | dry={DRY} | cats={cats} | brands={brands}", flush=True)
    queue: asyncio.Queue = asyncio.Queue()
    for r in rows:
        queue.put_nowait(r)
    stats = {"done": 0, "no_text": 0, "empty": 0, "errors": 0}
    async with httpx.AsyncClient(timeout=120) as client:
        await asyncio.gather(*[_worker(i, pool, client, queue, stats) for i in range(CONC)])
    await pool.close()
    print("=== SUMMARY ===", flush=True)
    print(json.dumps(stats, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
