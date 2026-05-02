FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
 && rm -rf /var/lib/apt/lists/*

# Python deps — отдельным слоем для кеша
RUN pip install --no-cache-dir \
    mempalace \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    pydantic

COPY service.py init_wings.py ./

ENV MEMPALACE_PALACE_PATH=/data/palace
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

# При старте: ensure палата + wing'и инициализированы → запустить FastAPI
CMD ["bash", "-c", "python init_wings.py && uvicorn service:app --host 0.0.0.0 --port 8080"]
