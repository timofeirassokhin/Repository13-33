#!/usr/bin/env bash
# Создаёт симлинк ../.env -> .env во всех директориях сервисов,
# чтобы docker compose в каждой подпапке подхватывал общий .env без флагов.

set -euo pipefail

cd "$(dirname "$0")/.."

for d in traefik twenty n8n qdrant litellm openwebui openclaw bot sites/13-33.pro; do
  if [[ -d "$d" ]]; then
    if [[ -L "$d/.env" || -e "$d/.env" ]]; then
      echo "skip $d/.env (уже есть)"
    else
      ln -s ../.env "$d/.env"
      echo "linked $d/.env -> ../.env"
    fi
  fi
done
