#!/usr/bin/env bash
# Gluvex Tender Machine — Phase 2: security hardening
# Run as root after bootstrap_phase1.sh has succeeded.
#
# - Creates non-root sudo user `gluvex` (groups: sudo, docker, NOPASSWD sudo)
# - Copies authorized_keys from root to gluvex
# - Configures UFW (deny incoming, allow 22/80/443)
# - Enables fail2ban jail for sshd (3 attempts → 1h ban)

set -euo pipefail

NEW_USER="gluvex"

echo "=========================================="
echo "PHASE 2: security hardening"
echo "=========================================="

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: must be run as root" >&2
  exit 1
fi

echo ""
echo "[1/4] Creating non-root sudo user '$NEW_USER'..."
if id "$NEW_USER" &>/dev/null; then
  echo "  user already exists"
else
  useradd -m -s /bin/bash -G sudo,docker "$NEW_USER"
  echo "$NEW_USER ALL=(ALL) NOPASSWD:ALL" > "/etc/sudoers.d/$NEW_USER"
  chmod 440 "/etc/sudoers.d/$NEW_USER"

  if [ -f /root/.ssh/authorized_keys ]; then
    mkdir -p "/home/$NEW_USER/.ssh"
    chmod 700 "/home/$NEW_USER/.ssh"
    cp /root/.ssh/authorized_keys "/home/$NEW_USER/.ssh/"
    chmod 600 "/home/$NEW_USER/.ssh/authorized_keys"
    chown -R "$NEW_USER:$NEW_USER" "/home/$NEW_USER/.ssh"
    echo "  authorized_keys copied from root"
  else
    echo "  WARNING: no /root/.ssh/authorized_keys to copy"
  fi
  echo "  groups: $(id "$NEW_USER")"
fi

echo ""
echo "[2/4] Configuring UFW firewall..."
ufw --force reset > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH comment "SSH access"
ufw allow 80/tcp comment "HTTP for Caddy + Lets Encrypt"
ufw allow 443/tcp comment "HTTPS for all services via Caddy"

echo ""
echo "[3/4] Enabling UFW (active SSH connections preserved)..."
echo "y" | ufw enable
ufw status numbered

echo ""
echo "[4/4] Configuring fail2ban jail for SSH..."
cat > /etc/fail2ban/jail.d/sshd-custom.conf <<'EOF'
[sshd]
enabled = true
port    = ssh
logpath = %(sshd_log)s
backend = %(sshd_backend)s
maxretry = 3
findtime = 10m
bantime = 1h
EOF
systemctl restart fail2ban
sleep 1
fail2ban-client status sshd 2>&1 | head -8

echo ""
echo "=========================================="
echo "PHASE 2 COMPLETE"
echo "=========================================="
echo ""
echo "Verify before disabling root SSH:"
echo "  From your laptop:  ssh $NEW_USER@<SERVER_IP>"
echo ""
echo "Once you confirm $NEW_USER access works, disable root SSH manually:"
echo "  sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config"
echo "  sudo systemctl reload ssh"
