#!/usr/bin/env bash
# Gluvex Tender Machine — управление стеком
# Использование:
#   ./manage.sh up | down | restart | status | logs [<service>] | update | shell <service>

set -euo pipefail
STACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$STACK_DIR"

cmd="${1:-status}"
shift || true

case "$cmd" in
  up)        docker compose up -d "$@" ;;
  down)      docker compose down ;;
  restart)   docker compose restart "$@" ;;
  status|ps) docker compose ps ;;
  logs)      docker compose logs -f --tail 100 "$@" ;;
  update)
    echo "==> pull новые образы"
    docker compose pull
    echo "==> перезапуск с новыми образами"
    docker compose up -d
    echo "==> очистка старых"
    docker image prune -f
    ;;
  shell)
    [ -z "${1:-}" ] && { echo "usage: $0 shell <service>"; exit 1; }
    docker compose exec "$1" /bin/sh
    ;;
  health)
    for url in https://crm.gluvex.com/healthz https://litellm.gluvex.com/health/liveliness https://bot.gluvex.com/; do
      printf "%-50s %s\n" "$url" "$(curl -sS -o /dev/null -w "HTTP %{http_code}  %{time_total}s" "$url" 2>&1)"
    done
    ;;
  *)
    echo "unknown command: $cmd"
    echo "usage: $0 {up|down|restart|status|logs|update|shell|health}"
    exit 1
    ;;
esac
