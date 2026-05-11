FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1

# CLI entrypoint
ENTRYPOINT ["python", "-m", "catalog_crawler"]
CMD ["--help"]
