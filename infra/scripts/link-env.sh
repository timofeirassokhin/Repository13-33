#!/usr/bin/env bash
# Создаёт симлинк .env во всех директориях сервисов,
# чтобы docker compose в каждой подпапке подхватывал общий .env без флагов.
# Использует абсолютный путь — работает даже для вложенных каталогов.

set -euo pipefail

cd "$(dirname "$0")/.."
INFRA_ROOT="$(pwd)"
ENV_PATH="$INFRA_ROOT/.env"

if [[ ! -f "$ENV_PATH" ]]; then
  echo "ERROR: $ENV_PATH not found. Run 'cp .env.example .env' first." >&2
  exit 1
fi

# Подпапки которые получают общий infra/.env
# tr-com подпапки тоже получают общий .env (через симлинк) — для tr-com-специфичных
# переменных используем флаг --env-file infra/tr-com/.env на докомпоузе при запуске.
DIRS=(
  traefik twenty n8n qdrant litellm openwebui openclaw bot whisper mempalace webdav uploader
  sites/13-33.pro sites/timofeirassokhin.com
  tr-com/twenty tr-com/listmonk tr-com/bot tr-com/glue
)

for d in "${DIRS[@]}"; do
  if [[ ! -d "$d" ]]; then
    echo "skip $d (no such directory)"
    continue
  fi

  target="$d/.env"

  # Снести существующий (валидный или битый), чтобы пересоздать корректно
  if [[ -L "$target" || -e "$target" ]]; then
    rm -f "$target"
  fi

  ln -s "$ENV_PATH" "$target"
  echo "linked $target -> $ENV_PATH"
done
