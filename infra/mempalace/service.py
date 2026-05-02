"""HTTP-обёртка над MemPalace для интеграции с production-агентами 13-33.

Endpoints:
  GET  /health                       — alive-check + count drawers
  GET  /wings                        — список wings с количеством drawers
  POST /drawer                       — добавить drawer
  GET  /drawer/{id}                  — получить drawer по id
  DELETE /drawer/{id}                — удалить
  POST /search                       — семантический поиск
  POST /kg/add                       — добавить triple в knowledge graph
  POST /kg/query                     — запросить связи сущности
  GET  /kg/stats                     — статистика KG

Запуск (через Dockerfile): uvicorn service:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


PALACE_PATH = Path(os.environ.get("MEMPALACE_PALACE_PATH", "/data/palace"))


# Lazy init — некоторые модули mempalace тяжёлые
_palace_client = None
_palace_col = None
_kg = None


def _get_col():
    global _palace_client, _palace_col
    if _palace_col is None:
        from mempalace.backends.chroma import ChromaBackend  # type: ignore
        _palace_client = ChromaBackend.make_client(str(PALACE_PATH))
        _palace_col = _palace_client.get_or_create_collection("memories")
    return _palace_col


def _get_kg():
    global _kg
    if _kg is None:
        from mempalace.knowledge_graph import KnowledgeGraph  # type: ignore
        _kg = KnowledgeGraph()
    return _kg


# ----------------------------------------------------------------------------
# Pydantic models
# ----------------------------------------------------------------------------

class DrawerCreate(BaseModel):
    content: str
    wing: str
    room: str = "default"
    title: str | None = None
    source_file: str | None = ""
    added_by: str = "api"
    tags: list[str] = Field(default_factory=list)


class DrawerOut(BaseModel):
    id: str
    content: str
    wing: str
    room: str
    title: str | None
    source_file: str | None
    added_by: str
    filed_at: str


class SearchRequest(BaseModel):
    query: str
    wing: str | None = None
    room: str | None = None
    n_results: int = 5
    max_distance: float = 1.5


class SearchResult(BaseModel):
    id: str
    content: str
    wing: str
    room: str
    distance: float
    metadata: dict[str, Any]


class KGTriple(BaseModel):
    subject: str
    predicate: str
    object: str
    valid_from: str | None = None
    source_closet: str | None = None


class KGQuery(BaseModel):
    entity: str
    as_of: str | None = None
    direction: str = "both"


# ----------------------------------------------------------------------------
# App
# ----------------------------------------------------------------------------

app = FastAPI(
    title="MemPalace HTTP API for 13-33",
    description="Знание-база и контентный архив. Used by producer-agent для извлечения контекста.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        col = _get_col()
        count = col.count()
        return {
            "status": "ok",
            "palace_path": str(PALACE_PATH),
            "total_drawers": count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/wings")
def list_wings() -> dict[str, Any]:
    """Список wings + количество drawers в каждом."""
    col = _get_col()
    counts: dict[str, int] = {}
    offset = 0
    total = col.count()
    while offset < total:
        batch = col.get(include=["metadatas"], limit=1000, offset=offset)
        for meta in batch.get("metadatas") or []:
            wing = (meta or {}).get("wing", "_unknown")
            counts[wing] = counts.get(wing, 0) + 1
        got = len(batch.get("metadatas") or [])
        if got == 0:
            break
        offset += got
    wings = [{"wing": w, "drawer_count": c} for w, c in sorted(counts.items())]
    return {"wings": wings, "total": total}


@app.post("/drawer")
def add_drawer(payload: DrawerCreate) -> dict[str, Any]:
    """Добавить drawer. ID автогенерируется."""
    col = _get_col()
    drawer_id = str(uuid.uuid4())
    metadata: dict[str, Any] = {
        "wing": payload.wing,
        "room": payload.room,
        "source_file": payload.source_file or "",
        "chunk_index": 0,
        "added_by": payload.added_by,
        "filed_at": datetime.now(timezone.utc).isoformat(),
    }
    if payload.title:
        metadata["title"] = payload.title
    if payload.tags:
        metadata["tags"] = ",".join(payload.tags)

    col.upsert(
        ids=[drawer_id],
        documents=[payload.content],
        metadatas=[metadata],
    )
    return {"id": drawer_id, "wing": payload.wing, "room": payload.room}


@app.get("/drawer/{drawer_id}")
def get_drawer(drawer_id: str) -> dict[str, Any]:
    col = _get_col()
    res = col.get(ids=[drawer_id], include=["metadatas", "documents"])
    if not res or not res.get("ids") or len(res["ids"]) == 0:
        raise HTTPException(status_code=404, detail="drawer not found")
    return {
        "id": res["ids"][0],
        "content": (res.get("documents") or [""])[0],
        "metadata": (res.get("metadatas") or [{}])[0],
    }


@app.delete("/drawer/{drawer_id}")
def delete_drawer(drawer_id: str) -> dict[str, Any]:
    col = _get_col()
    col.delete(ids=[drawer_id])
    return {"deleted": drawer_id}


@app.post("/search")
def search(req: SearchRequest) -> dict[str, Any]:
    """Семантический поиск через Chroma collection.query — стабильный формат ответа."""
    col = _get_col()
    where: dict[str, Any] = {}
    if req.wing:
        where["wing"] = req.wing
    if req.room:
        where["room"] = req.room
    kw: dict[str, Any] = {
        "query_texts": [req.query],
        "n_results": req.n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kw["where"] = where
    raw = col.query(**kw)
    ids = (raw.get("ids") or [[]])[0]
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    results = []
    for i, did in enumerate(ids):
        dist = dists[i] if i < len(dists) else 1.0
        # max_distance фильтр
        if dist > req.max_distance:
            continue
        results.append({
            "id": did,
            "content": docs[i] if i < len(docs) else "",
            "metadata": metas[i] if i < len(metas) else {},
            "distance": dist,
        })
    return {"results": results, "count": len(results)}


@app.post("/kg/add")
def kg_add(triple: KGTriple) -> dict[str, Any]:
    kg = _get_kg()
    triple_id = kg.add_triple(
        subject=triple.subject,
        predicate=triple.predicate,
        object=triple.object,
        valid_from=triple.valid_from,
        source_closet=triple.source_closet,
    )
    return {"triple_id": triple_id}


@app.post("/kg/query")
def kg_query(req: KGQuery) -> dict[str, Any]:
    kg = _get_kg()
    facts = kg.query_entity(
        entity=req.entity,
        as_of=req.as_of,
        direction=req.direction,
    )
    return {"facts": facts, "count": len(facts) if facts else 0}


@app.get("/kg/stats")
def kg_stats() -> dict[str, Any]:
    kg = _get_kg()
    return kg.stats()
