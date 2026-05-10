#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
stamp="$(date +%Y%m%d_%H%M%S)"
docker exec gluvex-tender-db-1 pg_dump -U "${TENDER_DATABASE_USER:-tender}" "${TENDER_DATABASE_NAME:-tender_monitor}" > "backups/tender_monitor_${stamp}.sql"
echo "Created backups/tender_monitor_${stamp}.sql"

