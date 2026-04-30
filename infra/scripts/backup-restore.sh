#!/usr/bin/env bash
# Восстановление из бэкапа. Использование:
#   ./scripts/backup-restore.sh list                   — показать снапшоты
#   ./scripts/backup-restore.sh latest /tmp/restore   — распаковать последний снапшот в /tmp/restore
#   ./scripts/backup-restore.sh <snapshot_id> /tmp/restore  — распаковать конкретный
#   ./scripts/backup-restore.sh mount /mnt/restic     — смонтировать репозиторий как FS (Ctrl+C чтобы отмонтировать)
#
# После распаковки SQL дампы лежат в /tmp/restore/opt/backups/dumps/
# Восстановить базу:  zcat <dump>.sql.gz | docker exec -i twenty-db psql -U postgres

set -euo pipefail

export RESTIC_REPOSITORY="${RESTIC_REPOSITORY:-/opt/backups/restic}"
export RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-/opt/backups/.restic-password}"

cmd="${1:-}"

case "$cmd" in
  list)
    restic snapshots
    ;;
  mount)
    target="${2:-/mnt/restic}"
    sudo mkdir -p "$target"
    echo "Монтирую в $target. Ctrl+C чтобы отмонтировать."
    restic mount "$target"
    ;;
  latest|"")
    target="${2:-/tmp/restic-restore}"
    mkdir -p "$target"
    echo "Распаковываю последний снапшот в $target ..."
    restic restore latest --target "$target"
    echo "Готово. Смотри $target/"
    ;;
  *)
    target="${2:-/tmp/restic-restore}"
    mkdir -p "$target"
    echo "Распаковываю снапшот $cmd в $target ..."
    restic restore "$cmd" --target "$target"
    echo "Готово."
    ;;
esac
