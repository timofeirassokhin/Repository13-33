FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Python-зависимости (отдельным слоем, чтобы кэшировались)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Код бота
COPY src/ ./src/

# Каталоги для данных
RUN mkdir -p /app/data /app/data/logs

ENV PYTHONUNBUFFERED=1 \
    PA_DB_PATH=/app/data/assistant.db \
    PA_LOG_FILE=/app/data/logs/assistant.log \
    PA_WEBHOOK_HOST=0.0.0.0 \
    PA_WEBHOOK_PORT=8443

EXPOSE 8443

# Healthcheck — OAuth callback должен отвечать 404 на /, иначе бот мёртв
HEALTHCHECK --interval=60s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS -o /dev/null -w '%{http_code}' http://localhost:8443/ | grep -E '^(200|404)$' || exit 1

CMD ["python", "-m", "src"]
