#!/usr/bin/env bash
# Первичная настройка бэкапов через restic.
# Запускать один раз. Идемпотентен — повторный запуск не сломает.

set -euo pipefail

REPO=/opt/backups/restic
PASSFILE=/opt/backups/.restic-password

echo "==> Установка restic, если ещё не стоит"
if ! command -v restic >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y restic
fi
restic version

echo "==> Создание каталогов"
sudo mkdir -p /opt/backups/restic /opt/backups/dumps /opt/backups/logs
sudo chown -R "$USER:$USER" /opt/backups
chmod 700 /opt/backups

echo "==> Генерация пароля для шифрования (если ещё нет)"
if [[ ! -f "$PASSFILE" ]]; then
  openssl rand -base64 48 > "$PASSFILE"
  chmod 600 "$PASSFILE"
  echo
  echo "  ⚠️  ВАЖНО: запиши пароль ниже куда-нибудь надёжно (1Password / Bitwarden):"
  echo "  ---"
  cat "$PASSFILE"
  echo "  ---"
  echo "  Без него бэкапы НЕВОЗМОЖНО восстановить."
  echo
fi

echo "==> Инициализация restic-репозитория"
export RESTIC_REPOSITORY="$REPO"
export RESTIC_PASSWORD_FILE="$PASSFILE"

if restic snapshots >/dev/null 2>&1; then
  echo "  репозиторий уже инициализирован"
else
  restic init
fi

echo
echo "==> Готово. Дальше:"
echo "    ./scripts/backup.sh                                — запустить бэкап вручную"
echo "    crontab -l                                          — посмотреть текущий cron"
echo "    Добавить в cron (sudo crontab -e):"
echo "    0 3 * * * /opt/stack/Repository13-33/infra/scripts/backup.sh >> /opt/backups/logs/backup-\$(date +\\%Y-\\%m-\\%d).log 2>&1"
