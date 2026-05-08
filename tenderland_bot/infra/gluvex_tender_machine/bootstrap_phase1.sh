#!/usr/bin/env bash
# Gluvex Tender Machine — Phase 1: baseline OS
# Run as root on a fresh Ubuntu 24.04 LTS server.
#
# Reproduces the initial setup applied 2026-05-08:
# - hostname, apt upgrade, base tools
# - Docker Compose V2 plugin
# - 8 GB swap
# - unattended-upgrades for security patches

set -euo pipefail

HOSTNAME_NEW="gluvex-tender-machine"
SWAP_SIZE_GB=8

echo "=========================================="
echo "PHASE 1: baseline OS setup"
echo "=========================================="

if [ "$(id -u)" -ne 0 ]; then
  echo "Error: must be run as root" >&2
  exit 1
fi

echo ""
echo "[1/6] Setting hostname to $HOSTNAME_NEW..."
hostnamectl set-hostname "$HOSTNAME_NEW"
if ! grep -q "$HOSTNAME_NEW" /etc/hosts; then
  echo "127.0.1.1 $HOSTNAME_NEW" >> /etc/hosts
fi
echo "  hostname: $(hostname)"

echo ""
echo "[2/6] Updating apt packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get -y \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
  upgrade < /dev/null 2>&1 | tail -5

echo ""
echo "[3/6] Installing baseline tools..."
apt-get install -y -qq \
  curl wget git jq htop tmux ca-certificates gnupg lsb-release \
  ufw fail2ban unattended-upgrades net-tools dnsutils unzip vim \
  < /dev/null 2>&1 | tail -3

echo ""
echo "[4/6] Installing Docker Compose V2 plugin..."
# Docker repo should already be configured (Selectel pre-installs Docker on Ubuntu).
# If not, uncomment the following block:
# install -m 0755 -d /etc/apt/keyrings
# curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
#   gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# chmod a+r /etc/apt/keyrings/docker.gpg
# echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
#   https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
#   tee /etc/apt/sources.list.d/docker.list > /dev/null
# apt-get update -qq
apt-get install -y -qq docker-compose-plugin < /dev/null 2>&1 | tail -2
docker compose version | head -1

echo ""
echo "[5/6] Creating $SWAP_SIZE_GB GB swap file..."
if [ ! -f /swapfile ]; then
  fallocate -l "${SWAP_SIZE_GB}G" /swapfile
  chmod 600 /swapfile
  mkswap -q /swapfile
  swapon /swapfile
  if ! grep -q "/swapfile" /etc/fstab; then
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
  fi
  echo "vm.swappiness=10" > /etc/sysctl.d/99-swappiness.conf
  sysctl -p /etc/sysctl.d/99-swappiness.conf > /dev/null
  echo "  swap: $(free -h | grep Swap | awk '{print $2}') created"
else
  echo "  swap already exists, skipping"
fi

echo ""
echo "[6/6] Enabling unattended-upgrades for security patches..."
echo "unattended-upgrades unattended-upgrades/enable_auto_updates boolean true" | \
  debconf-set-selections
dpkg-reconfigure -f noninteractive unattended-upgrades > /dev/null 2>&1
systemctl enable --now unattended-upgrades > /dev/null 2>&1
echo "  status: $(systemctl is-active unattended-upgrades)"

echo ""
echo "=========================================="
echo "PHASE 1 COMPLETE"
echo "=========================================="
echo "Hostname:     $(hostname)"
echo "Disk:         $(df -h / | tail -1 | awk '{print $3 " used / " $4 " free of " $2}')"
echo "Memory:       $(free -h | grep Mem | awk '{print $3 " used / " $7 " available"}')"
echo "Swap:         $(free -h | grep Swap | awk '{print $2}')"
echo "Docker:       $(docker --version)"
echo "Compose V2:   $(docker compose version)"
echo "fail2ban:     $(systemctl is-active fail2ban)"
echo "auto-updates: $(systemctl is-active unattended-upgrades)"
echo ""
echo "Next: run bootstrap_phase2.sh to harden security"
