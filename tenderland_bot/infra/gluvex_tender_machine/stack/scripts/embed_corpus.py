#!/usr/bin/env python3
"""Bulk semantic embedding of the ENTIRE RAG corpus into Qdrant 'memories' (MemPalace backend).

Reads all document_chunks (+ registry metadata), batch-embeds with the SAME model MemPalace uses
(paraphrase-multilingual-MiniLM-L12-v2, 384-d cosine), and bulk-upserts to Qdrant — far faster than
the per-chunk HTTP /drawer path. Recreates the collection from document_chunks as the single source
of truth (point id = document_chunks.id → idempotent, no duplicates).

Run inside mempalace-gluvex (has model cached + qdrant_client); needs asyncpg.
Env: PGPASSWORD (app-db), QDRANT_URL (default http://qdrant:6333), EMB_MODEL.
"""
import os, asyncio, datetime
import asyncpg
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

MODEL = os.environ.get("EMB_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
COLL = os.environ.get("QDRANT_COLLECTION", "memories")
QURL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
BATCH = int(os.environ.get("BATCH", "512"))
ENCODE_BS = int(os.environ.get("ENCODE_BS", "64"))


def wing_for(dt: str) -> str:
    if dt in ("tz", "offer", "kp_template", "kp_generated"):
        return "gluvex-tenders" if dt in ("tz", "offer") else "gluvex-kp"
    if dt == "brochure":
        return "gluvex-products"
    return "gluvex-knowledge"


async def main():
    pool = await asyncpg.create_pool(host=os.environ.get("PGHOST", "app-db"),
        user=os.environ.get("PGUSER", "postgres"), password=os.environ["PGPASSWORD"],
        database=os.environ.get("PGDATABASE", "gluvex_documents"), min_size=1, max_size=2)
    rows = await pool.fetch("""
        SELECT c.id::text AS id, c.chunk_text AS txt, c.chunk_index AS idx,
               dr.object_key, dr.filename, dr.document_type::text AS dt,
               coalesce(dr.metadata->>'brand', dr.bucket, '?') AS brand
        FROM document_chunks c JOIN document_registry dr ON dr.id = c.document_id
    """)
    await pool.close()
    print(f"chunks to embed: {len(rows)}", flush=True)

    model = SentenceTransformer(MODEL)
    dim = model.get_sentence_embedding_dimension()
    qc = QdrantClient(url=QURL, timeout=180)
    try:
        qc.delete_collection(COLL)
    except Exception:
        pass
    qc.create_collection(COLL, vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE))
    print(f"collection '{COLL}' recreated (dim={dim})", flush=True)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    total = 0
    for i in range(0, len(rows), BATCH):
        b = rows[i:i + BATCH]
        vecs = model.encode([r["txt"] for r in b], convert_to_numpy=True,
                            show_progress_bar=False, batch_size=ENCODE_BS).tolist()
        pts = []
        for r, v in zip(b, vecs):
            pts.append(qm.PointStruct(id=r["id"], vector=v, payload={
                "_document": r["txt"], "_id_str": r["id"],
                "wing": wing_for(r["dt"]), "room": r["brand"],
                "source_file": r["object_key"], "chunk_index": r["idx"],
                "title": r["filename"], "added_by": "embed_corpus", "filed_at": now}))
        qc.upsert(collection_name=COLL, points=pts, wait=False)
        total += len(pts)
        if (i // BATCH) % 10 == 0:
            print(f"  embedded {total}/{len(rows)}", flush=True)
    print(f"DONE embedded {total}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
