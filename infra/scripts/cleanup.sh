#!/usr/bin/env bash
# Удаляет старые контейнеры и их volumes/сети.
# Twenty (пустой) и hollama сносятся вместе с данными.
# OpenClaw, n8n, qdrant, litellm — переразвернём чисто.

set -euo pipefail

echo "==> 1. Stopping & removing containers"
docker rm -f \
  twenty-server-1 twenty-worker-1 twenty-db-1 twenty-redis-1 \
  openclaw-gateway \
  hollama \
  litellm \
  n8n \
  qdrant \
  open-webui openwebui \
  2>/dev/null || true

echo
echo "==> 2. Volumes that will be removed:"
docker volume ls --format '{{.Name}}' \
  | grep -E '^(twenty|hollama|n8n|qdrant|litellm|openclaw|open-webui|openwebui)' || true

read -r -p "Type YES to delete the volumes above (or anything else to skip): " confirm
if [[ "${confirm}" == "YES" ]]; then
  docker volume ls --format '{{.Name}}' \
    | grep -E '^(twenty|hollama|n8n|qdrant|litellm|openclaw|open-webui|openwebui)' \
    | xargs -r docker volume rm
fi

echo
echo "==> 3. Removing custom networks (keeping bridge/host/none/proxy)"
docker network ls --format '{{.Name}}' \
  | grep -vE '^(bridge|host|none|proxy)$' \
  | xargs -r -I{} docker network rm {} 2>/dev/null || true

echo
echo "==> 4. Pruning unused images (optional, frees disk)"
read -r -p "Run 'docker image prune -a' to free disk? (y/N): " imgconfirm
if [[ "${imgconfirm}" == "y" || "${imgconfirm}" == "Y" ]]; then
  docker image prune -a -f
fi

echo
echo "==> 5. Final state:"
docker ps -a
docker volume ls
docker network ls
