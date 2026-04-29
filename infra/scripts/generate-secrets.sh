#!/usr/bin/env bash
# Печатает свежие секреты для .env.
# Использование:
#   ./scripts/generate-secrets.sh
# Скопируй вывод и вставь поверх соответствующих строк в .env.

set -euo pipefail

rand_hex() { openssl rand -hex "$1"; }
rand_b64() { openssl rand -base64 "$1" | tr -d '\n'; }

echo "# Сгенерированные секреты — вставь в .env"
echo
echo "TWENTY_APP_SECRET=$(rand_hex 32)"
echo "TWENTY_PG_PASSWORD=$(rand_hex 24)"
echo
echo "N8N_ENCRYPTION_KEY=$(rand_hex 32)"
echo "N8N_DB_PASSWORD=$(rand_hex 24)"
echo
echo "LITELLM_MASTER_KEY=sk-$(rand_hex 24)"
echo "LITELLM_SALT_KEY=$(rand_hex 32)"
echo
echo "WEBUI_SECRET_KEY=$(rand_hex 32)"
