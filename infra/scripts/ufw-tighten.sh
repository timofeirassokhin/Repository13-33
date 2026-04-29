#!/usr/bin/env bash
# Закрывает лишние порты, которые торчали при старой установке.
# Оставляет только 22, 80, 443 наружу + Ollama (11434) с твоего постоянного IP.

set -euo pipefail

ADMIN_IP="80.250.237.232"

echo "==> Текущее состояние UFW:"
sudo ufw status numbered

cat <<EOF

Сейчас удалю следующие правила (они открывают сервисы голым в интернет):
  - 3000              (Twenty server, открытым быть не должен)
  - 3000/tcp          (дубль)
  - 4173/tcp          (Vite preview, не нужен наружу)
  - 5678/tcp          (n8n, должен ходить через Traefik)
  - 11434/tcp from 213.87.140.252  (старый VPN IP, динамический)
  - 4000/tcp  from 213.87.140.252  (старый VPN IP)

И добавлю:
  - 11434/tcp from ${ADMIN_IP}     (Ollama только с постоянного IP)

Останется наружу: 22 (SSH), 80, 443.
EOF

read -r -p "Продолжить? (y/N): " confirm
[[ "${confirm}" == "y" || "${confirm}" == "Y" ]] || { echo "Отмена."; exit 0; }

# delete by exact rule text (UFW принимает тот же синтаксис, что и allow)
sudo ufw --force delete allow 3000 || true
sudo ufw --force delete allow 3000/tcp || true
sudo ufw --force delete allow 4173/tcp || true
sudo ufw --force delete allow 5678/tcp || true
sudo ufw --force delete allow from 213.87.140.252 to any port 11434 proto tcp || true
sudo ufw --force delete allow from 213.87.140.252 to any port 4000 proto tcp || true

# add ollama from permanent IP
sudo ufw allow from "${ADMIN_IP}" to any port 11434 proto tcp comment 'Ollama from admin IP'

sudo ufw reload
echo
echo "==> Итоговое состояние:"
sudo ufw status verbose
