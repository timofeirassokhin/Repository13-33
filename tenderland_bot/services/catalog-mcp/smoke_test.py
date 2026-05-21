"""Smoke test: exercise all MCP tools against live DB + MemPalace."""
import asyncio, json
from gluvex_catalog_mcp import server as s


def show(label, raw, keys=None):
    try:
        d = json.loads(raw)
    except Exception:
        print(f"{label}: <non-json> {raw[:200]}"); return
    if isinstance(d, dict) and "error" in d:
        print(f"{label}: ERROR {d['error']}"); return
    if keys:
        print(f"{label}: " + " | ".join(f"{k}={d.get(k)}" for k in keys))
    else:
        print(f"{label}: {json.dumps(d, ensure_ascii=False)[:240]}")


async def main():
    show("overview(category)", await s.gluvex_catalog_overview(s.OverviewInput(by="category", top=5)))
    show("spec_fields(syringe_filter)", await s.gluvex_list_spec_fields(s.SpecFieldsInput(category="syringe_filter", top=8)))
    print("\n-- query by spec: PTFE 0.22um 25mm syringe filters --")
    r = await s.gluvex_query_products_by_spec(s.SpecQueryInput(
        category="syringe_filter",
        filters=[s.SpecFilter(key="membrane_material", op=s.SpecOp.ilike, value="PTFE"),
                 s.SpecFilter(key="pore_size_um", op=s.SpecOp.eq, value="0.22")], limit=5))
    show("  by_spec", r, keys=["count"]); print("   ", json.loads(r).get("results", [])[:2])
    print("\n-- query by spec: UV-Vis covering 340 nm --")
    r = await s.gluvex_query_products_by_spec(s.SpecQueryInput(
        category="uv_vis_spectrometer",
        filters=[s.SpecFilter(key="wavelength_range_nm", op=s.SpecOp.range_covers, value="340")], limit=3))
    show("  uv_by_spec", r, keys=["count"])
    print("\n-- get_product: a Hawach filter & a sequencer --")
    show("  get(Cary 3500)", await s.gluvex_get_product(s.GetProductInput(model="Cary 3500 Flexible")), keys=["brand","model","category"])
    show("  get(NovaSeq 6000)", await s.gluvex_get_product(s.GetProductInput(model="NovaSeq 6000")))[: ] if False else None
    np = json.loads(await s.gluvex_get_product(s.GetProductInput(model="NovaSeq 6000")))
    print(f"   NovaSeq: configs={len(np.get('configurations',[]))} metrics={len(np.get('runtime_metrics',[]))} slots={len(np.get('slots',[]))} ru_eq={'ru_equivalents' in np}")
    show("\nfind_sequencer(WGS,ru_only)", await s.gluvex_find_sequencer(s.FindSeqInput(application="WGS", read_mode_like="150", ru_only=True, limit=3)), keys=["count"])
    show("resolve_oem(Геноскан 4000)", await s.gluvex_resolve_oem(s.OemInput(model="Геноскан 4000")))
    show("search_documents(септы силикон)", await s.gluvex_search_documents(s.SearchDocsInput(query="септы силикон PTFE виалы", scope=s.Scope.products, n_results=2)), keys=["count"])
    show("search_products(шприцевой фильтр)", await s.gluvex_search_products(s.ProductSearchInput(query="шприцевой фильтр", has_specs=True, limit=3)), keys=["count","has_more"])
    if s._pool:
        await s._pool.close()


asyncio.run(main())
