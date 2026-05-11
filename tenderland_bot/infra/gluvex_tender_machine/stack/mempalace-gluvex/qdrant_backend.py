"""Qdrant backend для MemPalace.

Реализует контракт `mempalace.backends.base.BaseBackend` / `BaseCollection`
поверх Qdrant + sentence-transformers (для embedding).

Используется в `service.py` и `init_wings.py` вместо стандартного ChromaBackend:

    from qdrant_backend import QdrantBackend
    client = QdrantBackend.make_client(...)
    col = client.get_or_create_collection("memories")

Совместимость:
    Возвращает `mempalace.backends.base.QueryResult` и `GetResult` —
    что service.py ожидает.
"""
from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Any, Optional

from mempalace.backends.base import (
    BaseBackend, BaseCollection, GetResult, HealthStatus, PalaceRef, QueryResult,
)
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm
from sentence_transformers import SentenceTransformer


log = logging.getLogger(__name__)


# ============================================================
# Embedder — sentence-transformers, ленивая инициализация (модель ~400MB)
# ============================================================
_embedder: Optional[SentenceTransformer] = None
_embedder_lock = threading.Lock()

DEFAULT_MODEL = os.environ.get(
    "MEMPALACE_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                log.info("Loading embedding model %s ...", DEFAULT_MODEL)
                _embedder = SentenceTransformer(DEFAULT_MODEL)
                log.info("  dim=%d", _embedder.get_embedding_dimension())
    return _embedder


def _embed(texts: list[str]) -> list[list[float]]:
    model = _get_embedder()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False).tolist()


# ============================================================
# QdrantCollection — implements BaseCollection ABC
# ============================================================
class QdrantCollection(BaseCollection):
    """Одна Qdrant collection ↔ один MemPalace "memories" container."""

    def __init__(self, client: QdrantClient, collection_name: str):
        self._client = client
        self._collection_name = collection_name

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------
    def add(self, *, documents, ids, metadatas=None, embeddings=None):
        return self.upsert(
            documents=documents, ids=ids, metadatas=metadatas, embeddings=embeddings,
        )

    def upsert(self, *, documents, ids, metadatas=None, embeddings=None):
        if embeddings is None:
            embeddings = _embed(list(documents))
        if metadatas is None:
            metadatas = [{} for _ in ids]

        points = []
        for i, (id_, text, vector, meta) in enumerate(zip(ids, documents, embeddings, metadatas)):
            # сохраняем оригинальный текстовый ID в payload — Qdrant требует UUID или int
            payload = {"_document": text, "_id_str": str(id_), **(meta or {})}
            points.append(
                qm.PointStruct(id=_id_to_qdrant(id_), vector=vector, payload=payload)
            )

        self._client.upsert(collection_name=self._collection_name, points=points, wait=True)

    def update(self, *, ids, documents=None, metadatas=None, embeddings=None):
        if documents is None and metadatas is None and embeddings is None:
            raise ValueError("update requires at least one of documents, metadatas, embeddings")
        # Qdrant doesn't have partial update for points — re-upsert with new data.
        # Сначала достанем существующие points для непереданных полей.
        existing = self._client.retrieve(
            collection_name=self._collection_name,
            ids=[_id_to_qdrant(i) for i in ids],
            with_payload=True,
            with_vectors=True,
        )
        existing_by_id = {p.id: p for p in existing}

        new_docs, new_metas, new_embeds = [], [], []
        for i, id_ in enumerate(ids):
            qid = _id_to_qdrant(id_)
            ex = existing_by_id.get(qid)
            doc = documents[i] if documents is not None else (ex.payload.get("_document") if ex else "")
            meta_input = metadatas[i] if metadatas is not None else (
                {k: v for k, v in (ex.payload or {}).items() if k != "_document"} if ex else {}
            )
            emb = embeddings[i] if embeddings is not None else (ex.vector if ex else None)
            if emb is None:
                emb = _embed([doc])[0]
            new_docs.append(doc)
            new_metas.append(meta_input)
            new_embeds.append(emb)

        self.upsert(documents=new_docs, ids=ids, metadatas=new_metas, embeddings=new_embeds)

    def delete(self, *, ids=None, where=None):
        if ids is not None:
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qm.PointIdsList(points=[_id_to_qdrant(i) for i in ids]),
                wait=True,
            )
        elif where is not None:
            filt = _where_to_filter(where)
            self._client.delete(
                collection_name=self._collection_name,
                points_selector=qm.FilterSelector(filter=filt),
                wait=True,
            )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def query(
        self, *,
        query_texts=None, query_embeddings=None,
        n_results=10, where=None, where_document=None, include=None,
    ) -> QueryResult:
        if (query_texts is None) == (query_embeddings is None):
            raise ValueError("query requires exactly one of query_texts or query_embeddings")
        if query_texts is not None:
            query_vectors = _embed(list(query_texts))
        else:
            query_vectors = list(query_embeddings)

        qdrant_filter = _where_to_filter(where) if where else None

        all_ids, all_docs, all_metas, all_dists = [], [], [], []
        for qv in query_vectors:
            # qdrant-client v1.11+: search → query_points
            response = self._client.query_points(
                collection_name=self._collection_name,
                query=qv,
                limit=n_results,
                query_filter=qdrant_filter,
                with_payload=True,
            )
            hits = response.points
            ids_, docs_, metas_, dists_ = [], [], [], []
            for h in hits:
                ids_.append(h.payload.get("_id_str", str(h.id)) if h.payload else str(h.id))
                doc_text = h.payload.get("_document", "") if h.payload else ""
                docs_.append(doc_text)
                meta = {k: v for k, v in (h.payload or {}).items() if k not in ("_document", "_id_str")}
                metas_.append(meta)
                # Qdrant возвращает cosine SIMILARITY (если distance=Cosine). Конвертируем в "distance" формат Chroma.
                # Chroma cosine distance = 1 - cosine similarity
                dists_.append(float(1.0 - h.score))
            all_ids.append(ids_)
            all_docs.append(docs_)
            all_metas.append(metas_)
            all_dists.append(dists_)

        return QueryResult(
            ids=all_ids,
            documents=all_docs,
            metadatas=all_metas,
            distances=all_dists,
            embeddings=None,
        )

    def get(self, *, ids=None, where=None, include=None, limit=None, offset=None):
        if ids is not None:
            qids = [_id_to_qdrant(i) for i in ids]
            recs = self._client.retrieve(
                collection_name=self._collection_name,
                ids=qids,
                with_payload=True,
            )
        else:
            qdrant_filter = _where_to_filter(where) if where else None
            scroll, _ = self._client.scroll(
                collection_name=self._collection_name,
                scroll_filter=qdrant_filter,
                limit=limit or 100,
                offset=offset,
                with_payload=True,
            )
            recs = scroll

        ids_out, docs_out, metas_out = [], [], []
        for r in recs:
            ids_out.append(r.payload.get("_id_str", str(r.id)) if r.payload else str(r.id))
            docs_out.append(r.payload.get("_document", "") if r.payload else "")
            meta = {k: v for k, v in (r.payload or {}).items() if k not in ("_document", "_id_str")}
            metas_out.append(meta)

        return GetResult(
            ids=ids_out,
            documents=docs_out,
            metadatas=metas_out,
            embeddings=None,
        )

    def count(self) -> int:
        return self._client.count(collection_name=self._collection_name, exact=True).count

    def health(self) -> HealthStatus:
        try:
            self._client.get_collection(self._collection_name)
            return HealthStatus.healthy(f"qdrant collection '{self._collection_name}' OK")
        except Exception as e:
            return HealthStatus.unhealthy(f"qdrant collection error: {e}")


# ============================================================
# QdrantBackend — implements BaseBackend ABC
# ============================================================
class QdrantBackend(BaseBackend):
    """Backend — singleton клиент к Qdrant, один на процесс."""

    _instance: Optional["QdrantBackend"] = None
    _lock = threading.Lock()

    def __init__(self, client: QdrantClient):
        self._client = client
        self._known_dim: Optional[int] = None

    # legacy-style factory совместимый с ChromaBackend.make_client(path) использованием
    @classmethod
    def make_client(cls, _palace_path: str | None = None) -> "QdrantClientAdapter":
        url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
        api_key = os.environ.get("QDRANT_API_KEY") or None
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    client = QdrantClient(url=url, api_key=api_key, timeout=30)
                    cls._instance = cls(client)
        return QdrantClientAdapter(cls._instance)

    def get_collection(self, palace: PalaceRef, name: str, *, create: bool = True, metadata=None):
        # palace ref игнорируем — у нас один Qdrant, namespaces через collection name
        try:
            self._client.get_collection(name)
        except Exception:
            if not create:
                from mempalace.backends.base import PalaceNotFoundError
                raise PalaceNotFoundError(f"collection {name} not found")
            dim = _get_embedder().get_embedding_dimension()
            self._client.create_collection(
                collection_name=name,
                vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE),
            )
            log.info("Created Qdrant collection '%s' (dim=%d)", name, dim)
        return QdrantCollection(self._client, name)

    def health(self, palace: Optional[PalaceRef] = None) -> HealthStatus:
        try:
            collections = self._client.get_collections()
            return HealthStatus.healthy(f"qdrant OK, {len(collections.collections)} collections")
        except Exception as e:
            return HealthStatus.unhealthy(f"qdrant connection error: {e}")


# ============================================================
# QdrantClientAdapter — совместимость с chromadb-like make_client API
# ============================================================
# Старый код делает:
#   client = ChromaBackend.make_client(path)
#   col = client.get_or_create_collection("memories")
# Мы эмулируем get_or_create_collection через get_collection с create=True.
class QdrantClientAdapter:
    def __init__(self, backend: QdrantBackend):
        self._backend = backend

    def get_or_create_collection(self, name: str, metadata=None) -> QdrantCollection:
        # Передаём пустой PalaceRef — Qdrant игнорирует palace pointer
        return self._backend.get_collection(PalaceRef(id="gluvex"), name, create=True, metadata=metadata)

    def get_collection(self, name: str) -> QdrantCollection:
        return self._backend.get_collection(PalaceRef(id="gluvex"), name, create=False)


# ============================================================
# Helpers
# ============================================================
def _id_to_qdrant(id_: str | int) -> str | int:
    """Qdrant принимает либо int, либо UUID-строку. Конвертируем произвольную строку в детерминистский UUID."""
    if isinstance(id_, int):
        return id_
    try:
        # если уже валидный UUID — оставляем
        uuid.UUID(id_)
        return id_
    except (ValueError, AttributeError):
        # детерминистский UUID из произвольной строки
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, str(id_)))


def _where_to_filter(where: dict | None) -> qm.Filter | None:
    """Конвертирует Chroma-style where (метаданные) в Qdrant Filter.

    Поддерживает только простой плоский формат: {"field": "value", "field2": {"$eq": value}}.
    Сложные операторы пока не поддержаны — выбросит UnsupportedFilterError.
    """
    if not where:
        return None
    from mempalace.backends.base import UnsupportedFilterError

    must = []
    for field, condition in where.items():
        if isinstance(condition, (str, int, float, bool)):
            must.append(qm.FieldCondition(key=field, match=qm.MatchValue(value=condition)))
        elif isinstance(condition, dict) and len(condition) == 1:
            op, val = next(iter(condition.items()))
            if op == "$eq":
                must.append(qm.FieldCondition(key=field, match=qm.MatchValue(value=val)))
            elif op == "$ne":
                # not equal — через must_not
                must.append(qm.FieldCondition(key=field, match=qm.MatchExcept(**{"except": [val]})))
            elif op in ("$gt", "$gte", "$lt", "$lte"):
                op_map = {"$gt": "gt", "$gte": "gte", "$lt": "lt", "$lte": "lte"}
                range_kwargs = {op_map[op]: val}
                must.append(qm.FieldCondition(key=field, range=qm.Range(**range_kwargs)))
            elif op == "$in":
                must.append(qm.FieldCondition(key=field, match=qm.MatchAny(any=val)))
            else:
                raise UnsupportedFilterError(f"operator {op} not supported in Qdrant adapter")
        else:
            raise UnsupportedFilterError(f"complex where for field {field}: {condition}")
    return qm.Filter(must=must)
