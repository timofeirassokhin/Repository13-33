#!/usr/bin/env bash
# Ежедневный бэкап через restic.
# Делает дамп Postgres из контейнеров, потом инкрементальный снэпшот всех volumes + infra.
# Локальный репозиторий на том же диске — переноси на внешнее хранилище, когда сможешь.

set -euo pipefail

# Бэкапу нужен root, чтобы читать /var/lib/docker/volumes и acme.json
if [[ "${EUID}" -ne 0 ]]; then
  echo "Запускай через sudo: sudo $0" >&2
  exit 1
fi

# --- Настройки ---
export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-/opt/backups/restic}"
export RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/opt/backups/.restic-password}"

DUMPS_DIR=/opt/backups/dumps
LOG_DIR=/opt/backups/logs
DATE=$(date -u +%Y-%m-%dT%H-%M-%SZ)

mkdir -p "$DUMPS_DIR" "$LOG_DIR"

echo "==> Backup started at $DATE"

# --- Postgres дампы из контейнеров ---
# Сами контейнеры остаются работать; pg_dump делает консистентный снимок.
dump_pg() {
  local container="$1"
  local user="$2"
  local out="$DUMPS_DIR/${container}-latest.sql.gz"
  if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
    echo "  pg_dumpall ${container} (user=${user})"
    docker exec "$container" pg_dumpall -U "$user" | gzip > "$out"
  else
    echo "  skip ${container} (не запущен)"
  fi
}

dump_pg twenty-db postgres
dump_pg n8n-db   n8n

# --- SQLite бот (просто файл из volume) ---
# Берётся restic-ом ниже как часть /var/lib/docker/volumes

# --- Restic snapshot ---
echo "==> restic backup"
restic backup \
  /var/lib/docker/volumes \
  /opt/stack/Repository13-33/infra \
  "$DUMPS_DIR" \
  --tag daily \
  --exclude='*.tmp' \
  --exclude='**/node_modules' \
  --exclude='**/dist' \
  --exclude='**/.cache'

# --- Retention ---
echo "==> retention (keep 7 daily, 4 weekly, 6 monthly)"
restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 6 \
  --prune

# --- Stats ---
echo "==> repo stats"
restic stats latest

echo "==> Backup finished at $(date -u +%Y-%m-%dT%H-%M-%SZ)"
