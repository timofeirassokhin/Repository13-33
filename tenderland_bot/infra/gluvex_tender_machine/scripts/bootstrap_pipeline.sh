#!/usr/bin/env bash
# Bootstrap-скрипт для деплоя Tenderland-pipeline на VPS 45.66.117.251.
#
# Что делает:
#   1. Создаёт /opt/gluvex/ структуру.
#   2. Клонирует репо (или git pull) в /opt/gluvex/repo/.
#   3. Делает venv в /opt/gluvex/venv/.
#   4. Устанавливает зависимости.
#   5. Создаёт шаблон .env (с подсказками).
#   6. Регистрирует systemd-таймер для ежедневного прогона в 07:00 МСК Пн-Пт.
#
# Запуск на сервере:
#   ssh gluvex
#   curl -fsSL https://raw.githubusercontent.com/<repo>/main/tenderland_bot/infra/gluvex_tender_machine/scripts/bootstrap_pipeline.sh | bash
# или скопировать локально и:
#   bash bootstrap_pipeline.sh
set -euo pipefail

# ---------- настройки ----------
APP_USER="${APP_USER:-gluvex}"
BASE_DIR="${BASE_DIR:-/opt/gluvex}"
REPO_URL="${REPO_URL:-https://github.com/timofeirassokhin/Repository13-33.git}"
REPO_DIR="${BASE_DIR}/repo"
APP_DIR="${BASE_DIR}/tenderland_bot"   # symlink на repo/tenderland_bot
VENV_DIR="${BASE_DIR}/venv"
DATA_DIR="${BASE_DIR}/data"
LOG_DIR="${BASE_DIR}/logs"
ENV_FILE="${BASE_DIR}/.env"
SERVICE_NAME="gluvex-tender-pipeline"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"

# ---------- helpers ----------
log() { echo "[bootstrap] $*"; }
fail() { echo "[bootstrap] ERROR: $*" >&2; exit 1; }

require_root_or_sudo() {
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        fail "нужны sudo-права (запусти от root или как gluvex с sudo NOPASSWD)"
    fi
}

# ---------- проверки ----------
log "проверяю окружение..."
require_root_or_sudo
command -v "$PYTHON_BIN" >/dev/null 2>&1 || \
    fail "$PYTHON_BIN не найден. Установи: sudo apt install python3.11 python3.11-venv python3-pip"
command -v git >/dev/null 2>&1 || fail "git не найден"

# ---------- структура папок ----------
log "создаю $BASE_DIR ..."
sudo mkdir -p "$BASE_DIR" "$DATA_DIR" "$LOG_DIR"
sudo chown -R "$APP_USER:$APP_USER" "$BASE_DIR"

# ---------- репо ----------
if [[ -d "$REPO_DIR/.git" ]]; then
    log "обновляю существующий репо..."
    cd "$REPO_DIR" && git pull --ff-only
else
    log "клонирую репо из $REPO_URL ..."
    git clone "$REPO_URL" "$REPO_DIR"
fi
# symlink на tenderland_bot для удобства
ln -snf "$REPO_DIR/tenderland_bot" "$APP_DIR"

# ---------- venv + deps ----------
if [[ ! -d "$VENV_DIR" ]]; then
    log "создаю venv ($PYTHON_BIN) ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
log "устанавливаю зависимости..."
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -e "$APP_DIR" >/dev/null
# Дополнительно — pydantic + openpyxl + anthropic если не подтянулись
"$VENV_DIR/bin/pip" install pydantic openpyxl anthropic httpx typer rich python-slugify pydantic-settings >/dev/null

# ---------- .env шаблон ----------
if [[ ! -f "$ENV_FILE" ]]; then
    log "создаю шаблон .env (заполнить руками!)"
    cat > "$ENV_FILE" <<'ENV'
# Tenderland API
TL_API_KEY=ЗАМЕНИ_МЕНЯ
TL_OUTPUT_DIR=/opt/gluvex/data/tenders
TL_BASE_URL=https://tenderland.ru
TL_HTTP_TIMEOUT=120

# Anthropic для Tier-2/Tier-3
ANTHROPIC_API_KEY=ЗАМЕНИ_МЕНЯ

# (опц) Email-дайджест — Resend
RESEND_API_KEY=
DIGEST_FROM=tenders@gluvexlab.com
DIGEST_TO=rstim@gluvexlab.com
ENV
    chmod 600 "$ENV_FILE"
    chown "$APP_USER:$APP_USER" "$ENV_FILE"
    log "  → отредактируй $ENV_FILE и подставь ключи"
fi

# ---------- systemd service + timer ----------
log "регистрирую systemd-таймер $SERVICE_NAME.timer ..."

sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null <<EOF
[Unit]
Description=Gluvex Tenderland pipeline (Tier-1 → Tier-2 → Excel digest)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$VENV_DIR/bin/python -m tenderland_bot export-all --no-files --out $DATA_DIR/tenders
ExecStartPost=$VENV_DIR/bin/python $APP_DIR/scripts/run_tier2_and_excel.py
StandardOutput=append:$LOG_DIR/pipeline.log
StandardError=append:$LOG_DIR/pipeline.log
EOF

sudo tee "/etc/systemd/system/${SERVICE_NAME}.timer" > /dev/null <<EOF
[Unit]
Description=Daily Gluvex tender pipeline (07:00 MSK Mon-Fri)

[Timer]
OnCalendar=Mon..Fri *-*-* 07:00:00
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "${SERVICE_NAME}.timer"
sudo systemctl start "${SERVICE_NAME}.timer"

# ---------- logrotate ----------
sudo tee "/etc/logrotate.d/${SERVICE_NAME}" > /dev/null <<EOF
$LOG_DIR/pipeline.log {
    weekly
    rotate 12
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $APP_USER $APP_USER
}
EOF

# ---------- финал ----------
log ""
log "========================================"
log "  bootstrap завершён"
log "========================================"
log "Шаги:"
log "  1) отредактируй $ENV_FILE (ключи)"
log "  2) ручной прогон (smoke):"
log "       sudo systemctl start ${SERVICE_NAME}.service"
log "  3) логи:"
log "       tail -f $LOG_DIR/pipeline.log"
log "  4) таймер:"
log "       systemctl list-timers ${SERVICE_NAME}.timer"
log ""
log "Выгрузки → $DATA_DIR/tenders/<topic>/<DDMMYY>/"
log "Дайджесты → $DATA_DIR/tier2/Tenderland_digest_<date>.xlsx"
