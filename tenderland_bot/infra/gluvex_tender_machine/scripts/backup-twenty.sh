#!/usr/bin/env bash
# Gluvex Tender Machine — ночной бэкап Twenty Postgres
#
# Запуск через cron на @daily (03:00 МСК):
#   0 3 * * * /opt/gluvex/repos/Repository13-33/tenderland_bot/infra/gluvex_tender_machine/scripts/backup-twenty.sh
#
# Что делает:
#   - pg_dump базы default из контейнера twenty-db
#   - сжимает gzip
#   - кладёт в /opt/gluvex/backups/twenty/twenty_YYYYMMDD_HHMMSS.sql.gz
#   - удаляет файлы старше KEEP_DAYS дней (по умолчанию 14)
#   - пишет лог в /opt/gluvex/logs/backup-twenty.log

set -euo pipefail

CONTAINER="${TWENTY_DB_CONTAINER:-twenty-db}"
DB_NAME="${TWENTY_DB_NAME:-default}"
DB_USER="${TWENTY_DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/opt/gluvex/backups/twenty}"
LOG_FILE="${LOG_FILE:-/opt/gluvex/logs/backup-twenty.log}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

stamp="$(date +%Y%m%d_%H%M%S)"
out="$BACKUP_DIR/twenty_${stamp}.sql.gz"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG_FILE"; }

log "==> backup start: $out"

# контейнер должен быть жив
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  log "ERROR: container ${CONTAINER} is not running"
  exit 1
fi

# pg_dump | gzip → файл
if docker exec -e PGPASSWORD="" "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --clean --if-exists 2>>"$LOG_FILE" | gzip > "$out"; then
  size=$(du -h "$out" | cut -f1)
  log "    OK ${size}"
else
  log "ERROR: pg_dump failed, удаляю файл"
  rm -f "$out"
  exit 1
fi

# ротация
old=$(find "$BACKUP_DIR" -type f -name 'twenty_*.sql.gz' -mtime +"$KEEP_DAYS" | wc -l)
if [ "$old" -gt 0 ]; then
  find "$BACKUP_DIR" -type f -name 'twenty_*.sql.gz' -mtime +"$KEEP_DAYS" -delete
  log "    rotated $old старых файлов (>${KEEP_DAYS}д)"
fi

current=$(find "$BACKUP_DIR" -type f -name 'twenty_*.sql.gz' | wc -l)
total_size=$(du -sh "$BACKUP_DIR" | cut -f1)
log "    в ${BACKUP_DIR}: ${current} файлов, всего ${total_size}"
log "==> backup OK"
