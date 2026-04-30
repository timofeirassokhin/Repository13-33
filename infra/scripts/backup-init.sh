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

echo "==> Создание каталогов (root-owned, чтобы бэкап мог читать volumes)"
sudo mkdir -p /opt/backups/restic /opt/backups/dumps /opt/backups/logs
sudo chown -R root:root /opt/backups
sudo chmod 700 /opt/backups

echo "==> Генерация пароля для шифрования (если ещё нет)"
if ! sudo test -f "$PASSFILE"; then
  sudo bash -c "openssl rand -base64 48 > '$PASSFILE'"
  sudo chmod 600 "$PASSFILE"
  echo
  echo "  ⚠️  ВАЖНО: запиши пароль ниже куда-нибудь надёжно (1Password / Bitwarden):"
  echo "  ---"
  sudo cat "$PASSFILE"
  echo "  ---"
  echo "  Без него бэкапы НЕВОЗМОЖНО восстановить."
  echo
fi

echo "==> Инициализация restic-репозитория"
export RESTIC_REPOSITORY="$REPO"
export RESTIC_PASSWORD_FILE="$PASSFILE"

if sudo -E restic snapshots >/dev/null 2>&1; then
  echo "  репозиторий уже инициализирован"
else
  sudo -E restic init
fi

echo
echo "==> Готово. Дальше:"
echo "    sudo ./scripts/backup.sh                          — запустить бэкап вручную"
echo "    sudo crontab -l                                    — посмотреть текущий root-cron"
echo "    Добавить в cron (sudo crontab -e):"
echo "    0 3 * * * /opt/stack/Repository13-33/infra/scripts/backup.sh >> /opt/backups/logs/backup-\$(date +\\%Y-\\%m-\\%d).log 2>&1"
