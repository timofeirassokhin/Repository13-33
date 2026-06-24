FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libxml2-dev libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

# Playwright + Chromium headless (~250MB) — для JS-render и stealth crawl
RUN pip install --no-cache-dir playwright>=1.50 playwright-stealth>=1.0.6 \
 && playwright install --with-deps chromium

ENV PYTHONUNBUFFERED=1

# CLI entrypoint
ENTRYPOINT ["python", "-m", "catalog_crawler"]
CMD ["--help"]
