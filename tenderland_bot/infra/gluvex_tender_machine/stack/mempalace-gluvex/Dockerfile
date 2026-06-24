FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

# Python deps. Sentence-transformers тянет torch (~700MB) — отдельным слоем для кеша.
RUN pip install --no-cache-dir \
    mempalace==3.3.5 \
    qdrant-client>=1.10 \
    sentence-transformers>=3.0 \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    pydantic

COPY qdrant_backend.py service.py init_wings.py ./

# Prefetch модели embedding в образ (~400MB → не качаем при старте контейнера)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')" \
    2>&1 | tail -5

ENV MEMPALACE_PALACE_PATH=/data/palace
ENV MEMPALACE_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
ENV QDRANT_URL=http://qdrant:6333
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# При старте: ensure палата + wings → запустить FastAPI
CMD ["bash", "-c", "python init_wings.py && uvicorn service:app --host 0.0.0.0 --port 8080"]
