#!/usr/bin/env python3
"""RAG-ingestion брошюр из MinIO -> document_registry + document_chunks + MemPalace.

Идемпотентно: дедуп по (tenant_id, content_hash) в document_registry.
Запуск (транзиентный контейнер на сети gluvex_app_internal):

  docker run --rm --network gluvex_app_internal \
    -e PGHOST=app-db -e PGUSER=postgres -e PGDATABASE=gluvex_documents -e PGPASSWORD=*** \
    -e MINIO_ENDPOINT=minio:9000 -e MINIO_ACCESS=*** -e MINIO_SECRET=*** \
    -e MEMPALACE_URL=http://mempalace-gluvex:8080 \
    -e BUCKET=product-brochures -e PREFIX=agilent/ -e WING=gluvex-products -e ROOM=agilent \
    -v /tmp/ingest_rag.py:/ingest_rag.py python:3.12-slim \
    sh -c "pip install -q pdfplumber asyncpg minio httpx && python /ingest_rag.py"
"""
from __future__ import annotations
import os, io, re, sys, json, hashlib, asyncio
import asyncpg, httpx
from minio import Minio
import pdfplumber

TENANT = os.environ.get("TENANT_ID", "11111111-1111-1111-1111-111111111111")
OWNER  = os.environ.get("OWNER_ID",  "11111111-1111-1111-1111-111111111111")
EMB_MODEL = os.environ.get("EMB_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
BUCKET = os.environ.get("BUCKET", "product-brochures")
PREFIX = os.environ.get("PREFIX", "agilent/")
WING   = os.environ.get("WING", "gluvex-products")
ROOM   = os.environ.get("ROOM", "agilent")
BRAND  = os.environ.get("BRAND", "Agilent Technologies")
MEMPALACE = os.environ.get("MEMPALACE_URL", "http://mempalace-gluvex:8080")
CHUNK = int(os.environ.get("CHUNK_CHARS", "1200"))
OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "150"))
PUSH_MP = os.environ.get("PUSH_MEMPALACE", "1") == "1"

CYR = re.compile(r"[А-Яа-яЁё]")
MODEL_TOK = re.compile(r"\b(1260|1290|8860|8890|Intuvo|5977|7000|7010|7250|6470|6475|6495|6545|6546|Ultivo|4210|5800|5900|7850|7900|8900|Cary\s?\d{2,4}|ZORBAX|Poroshell|Bond\s?Elut|Captiva)\b", re.I)


def extract_pdf(data: bytes) -> tuple[str, int]:
    # fast path: PyMuPDF (fitz) — ~10-20x faster than pdfplumber
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        n = doc.page_count
        parts = [p.get_text() for p in doc]
        doc.close()
        txt = "\n\n".join(t for t in parts if t.strip())
        if len(txt.strip()) >= 40:
            return txt, n
    except Exception:
        pass
    # fallback: pdfplumber (scanned/odd PDFs)
    parts = []
    n = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        n = len(pdf.pages)
        for pg in pdf.pages:
            t = pg.extract_text() or ""
            if t.strip():
                parts.append(t)
    return ("\n\n".join(parts), n)


def chunk_text(text: str, size: int = CHUNK, overlap: int = OVERLAP) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, cur = [], ""
    for p in paras:
        if len(cur) + len(p) + 1 <= size:
            cur = (cur + "\n" + p).strip()
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= size:
                cur = p
            else:
                # very long paragraph -> hard split
                for i in range(0, len(p), size - overlap):
                    chunks.append(p[i:i + size])
                cur = ""
    if cur:
        chunks.append(cur)
    # add overlap tail between consecutive chunks
    if overlap > 0 and len(chunks) > 1:
        out = [chunks[0]]
        for i in range(1, len(chunks)):
            tail = chunks[i - 1][-overlap:]
            out.append((tail + " " + chunks[i]).strip())
        chunks = out
    return chunks


async def main() -> int:
    mc = Minio(os.environ["MINIO_ENDPOINT"], access_key=os.environ["MINIO_ACCESS"],
               secret_key=os.environ["MINIO_SECRET"], secure=False)
    pg = await asyncpg.connect(host=os.environ.get("PGHOST", "app-db"),
                               user=os.environ.get("PGUSER", "postgres"),
                               password=os.environ["PGPASSWORD"],
                               database=os.environ.get("PGDATABASE", "gluvex_documents"))
    objs = [o.object_name for o in mc.list_objects(BUCKET, prefix=PREFIX, recursive=True)
            if o.object_name.lower().endswith((".pdf", ".md"))]
    print(f"found {len(objs)} docs (pdf+md) under {BUCKET}/{PREFIX}", flush=True)

    stats = {"docs": 0, "skipped_dup": 0, "no_text": 0, "chunks": 0, "mp_pushed": 0, "errors": 0}
    client = httpx.Client(timeout=120) if PUSH_MP else None

    for key in objs:
        try:
            data = mc.get_object(BUCKET, key).read()
            chash = hashlib.sha256(data).digest()
            dup = await pg.fetchval(
                "SELECT id FROM document_registry WHERE tenant_id=$1 AND content_hash=$2", TENANT, chash)
            if dup:
                stats["skipped_dup"] += 1
                continue
            if key.lower().endswith(".md"):
                text, npages = data.decode("utf-8", "ignore"), 0
            else:
                text, npages = extract_pdf(data)
            if len(text.strip()) < 40:
                stats["no_text"] += 1
                print(f"  NO TEXT (scanned?): {key}", flush=True)
                continue
            lang = "ru" if len(CYR.findall(text)) > 50 else "en"
            filename = key.rsplit("/", 1)[-1]
            brand_slug = key.split("/")[0] if "/" in key else (ROOM or "misc")
            toks = sorted({m.group(0).replace(" ", "") for m in MODEL_TOK.finditer(filename)})
            meta = {"brand": brand_slug, "lang": lang, "object_key": key,
                    "model_tokens": toks, "ingest": "rag_ingest_v1"}
            doc_id = await pg.fetchval("""
                INSERT INTO document_registry
                  (tenant_id, source_type, bucket, object_key, filename, content_type,
                   content_hash, document_type, language, status, access_level,
                   embedding_model, ocr_applied, owner_id, metadata, indexed_at)
                VALUES ($1,'manual_upload',$2,$3,$4,'application/pdf',$5,'brochure',$6,
                        'actual','internal',$7,false,$8,$9, now())
                RETURNING id
            """, TENANT, BUCKET, key, filename, chash, lang, EMB_MODEL, OWNER, json.dumps(meta))

            chunks = chunk_text(text)
            for i, ch in enumerate(chunks):
                ch_hash = hashlib.sha256(ch.encode("utf-8")).digest()
                await pg.execute("""
                    INSERT INTO document_chunks
                      (document_id, version_id, chunk_index, chunk_text, chunk_hash, embedding_model, metadata)
                    VALUES ($1,$1,$2,$3,$4,$5,$6)
                    ON CONFLICT (document_id, version_id, chunk_index) DO NOTHING
                """, doc_id, i, ch, ch_hash, EMB_MODEL, json.dumps({"object_key": key, "lang": lang}))
                stats["chunks"] += 1
                if PUSH_MP:
                    try:
                        r = client.post(f"{MEMPALACE}/drawer", json={
                            "content": ch, "wing": WING, "room": brand_slug,
                            "title": f"{filename} #{i}", "source_file": key,
                            "added_by": "rag_ingest", "tags": [brand_slug, lang] + toks,
                        })
                        if r.status_code < 300:
                            stats["mp_pushed"] += 1
                    except Exception as e:
                        print(f"  mp push err {key}#{i}: {e}", flush=True)

            await pg.execute("UPDATE document_registry SET chunk_count=$2, updated_at=now() WHERE id=$1",
                             doc_id, len(chunks))
            stats["docs"] += 1
            print(f"  [{stats['docs']}] {filename}  pages={npages} lang={lang} chunks={len(chunks)} toks={toks}", flush=True)
        except Exception as e:
            stats["errors"] += 1
            print(f"  ERROR {key}: {e}", flush=True)

    await pg.close()
    if client:
        client.close()
    print("=== SUMMARY ===", flush=True)
    print(json.dumps(stats, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
