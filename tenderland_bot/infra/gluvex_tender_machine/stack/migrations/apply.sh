#!/usr/bin/env bash
# Apply gluvex_documents migrations against app-db container.
#
# Usage:
#   ./apply.sh                  # применяет все *.sql из текущей папки
#   ./apply.sh 001_initial_schema.sql   # одна миграция
#
# Идемпотентно: каждая миграция использует IF NOT EXISTS / ON CONFLICT.
#
# В будущем можно мигрировать на alembic с version_tracking — пока хватает
# простого SQL-based подхода.

set -euo pipefail

MIGRATIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS="${SECRETS:-/opt/gluvex/secrets/.env}"
DB_CONTAINER="${DB_CONTAINER:-app-db}"
DB_NAME="${DB_NAME:-gluvex_documents}"
DB_USER="${DB_USER:-postgres}"          # postgres = master, чтобы было право на GRANT/REVOKE и CREATE EXTENSION

if [ ! -f "$SECRETS" ]; then
  echo "error: secrets file $SECRETS not found" >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "error: container ${DB_CONTAINER} is not running" >&2
  exit 1
fi

# собираем список миграций — либо переданный аргумент, либо все *.sql отсортированные
if [ $# -gt 0 ]; then
  files=("$@")
else
  mapfile -t files < <(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | sort)
fi

if [ ${#files[@]} -eq 0 ]; then
  echo "error: no .sql files found in $MIGRATIONS_DIR" >&2
  exit 1
fi

echo "==> applying ${#files[@]} migration(s) to ${DB_NAME} via container ${DB_CONTAINER}"

for f in "${files[@]}"; do
  basename=$(basename "$f")
  full="$MIGRATIONS_DIR/$basename"
  [ -f "$full" ] || { echo "error: $full not found" >&2; exit 1; }
  echo ""
  echo "==> $basename"
  docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$full"
done

echo ""
echo "==> tables after migration:"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c '\dt'
