# Gluvex Tender Machine — server bootstrap

Скрипты для воспроизводимой первичной настройки нового VPS под систему Gluvex Tender Machine. Применяются после получения Ubuntu 24.04 LTS сервера от провайдера (Selectel).

См. также:
- `../../docs/SERVER_INFRASTRUCTURE.md` — конфигурация сервера, выбор моделей, стоимость
- `../../ARCHITECTURE.md` — общая архитектура

## Предварительные требования

- Свежий Ubuntu Server 24.04 LTS
- Public IP, доступный по SSH (порт 22)
- Заведённый SSH-ключ для root (через панель провайдера или KVM-консоль)

## Этапы развёртывания

### Phase 1 — Baseline OS (≈5-10 минут)

```bash
# С локальной машины
scp bootstrap_phase1.sh root@<SERVER_IP>:/tmp/
ssh root@<SERVER_IP> 'bash /tmp/bootstrap_phase1.sh'
```

Что делает:
- Устанавливает hostname `gluvex-tender-machine`
- Обновляет все apt-пакеты
- Ставит базовые утилиты (curl, git, jq, ufw, fail2ban, htop, tmux, vim)
- Ставит Docker Compose V2 plugin (через apt из docker.com репозитория)
- Создаёт swap-файл 8 GB со swappiness=10
- Включает unattended-upgrades для автоматических security-патчей

### Phase 2 — Security hardening (≈2 минуты)

```bash
ssh root@<SERVER_IP> 'bash /tmp/bootstrap_phase2.sh'
```

Что делает:
- Создаёт non-root sudo-пользователя `gluvex` (группы `sudo`, `docker`, NOPASSWD sudo)
- Копирует authorized_keys из root в gluvex
- Настраивает UFW: deny incoming, allow outgoing, открывает 22/80/443
- Включает UFW
- Настраивает fail2ban jail для sshd (3 попытки → бан 1 час)

После Phase 2:
- Подключение через `ssh gluvex@<SERVER_IP>` работает
- Root SSH login пока **не отключён** — отключим вручную после стабильности (раздел 4 ниже)

### Phase 3 — Application stack (см. infra/gluvex_tender_machine/stack/)

После Phase 2 следующий шаг — деплой Docker-стека (Caddy + Postgres + Redis + Twenty + MemPalace + Tender Pipeline). Это в отдельном каталоге.

## Финальная защита (Phase 4 — ручная)

Когда подтвердишь что `ssh gluvex@<IP>` работает стабильно несколько дней:

```bash
ssh gluvex@<SERVER_IP>
sudo nano /etc/ssh/sshd_config
# Установить:
#   PermitRootLogin no
#   PasswordAuthentication no
sudo systemctl reload ssh
```

После этого root SSH отключён, доступ только под gluvex по ключу.

## Как откатиться

Если что-то пошло не так — все изменения обратимы:

- `apt remove ufw fail2ban` — снять файрволл и ban
- `swapoff /swapfile && rm /swapfile` + убрать строку из `/etc/fstab` — снять swap
- `userdel -r gluvex` + `rm /etc/sudoers.d/gluvex` — убрать пользователя
- `dpkg-reconfigure unattended-upgrades` — перенастроить автообновления

## Что после bootstrap

См. `../docs/SERVER_INFRASTRUCTURE.md` раздел 8 — полный чек-лист развёртывания, включая Этапы 3-5 (docker-compose стек, Twenty CRM, MemPalace, импорт данных, smoke-тесты).
