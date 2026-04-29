# Infra: Self-hosted stack для 13-33.pro

Разворачивание стека под управлением Traefik с автоматическим Let's Encrypt.

## Общая архитектура

```
Internet ──443/80──> Traefik ──proxy network──> [Twenty | n8n | OpenWebUI | OpenClaw | LiteLLM | Qdrant | Bot | Astro]
                       │
                       └── ACME (Let's Encrypt) → /letsencrypt/acme.json
```

Все сервисы:
- слушают только во внутренней docker-сети `proxy`,
- наружу доступны только через Traefik по поддоменам,
- получают TLS-сертификаты автоматически.

UFW наружу открывает только `22, 80, 443`.

## Поддомены

| Hostname | Сервис |
|---|---|
| `13-33.pro`, `www.13-33.pro` | Astro (статический сайт) |
| `crm.13-33.pro` | Twenty CRM |
| `n8n.13-33.pro` | n8n |
| `chat.13-33.pro` | OpenWebUI |
| `claw.13-33.pro` | OpenClaw |
| `traefik.13-33.pro` | Traefik dashboard (basic auth + IP allow) |
| `bot.13-33.pro` | OAuth callback Telegram-бота |

## Структура каталогов

```
infra/
├── .env.example       # общие переменные (DOMAIN, ACME_EMAIL, ADMIN_IP, …)
├── traefik/           # reverse proxy
├── twenty/            # CRM
├── n8n/               # автоматизации
├── openwebui/         # чат с LLM
├── openclaw/          # AI-агенты gateway
├── litellm/           # LLM-прокси
├── qdrant/            # векторная БД
├── bot/               # PA Telegram Bot
├── sites/             # статические сайты
└── scripts/           # вспомогательные скрипты (cleanup, ufw, backup)
```

## Phase 1 — bootstrap (сейчас)

Цель: поднять Traefik, получить сертификаты, доказать что HTTPS работает.

См. `docs/phase1.md` (или инструкцию в чате).

## Phase 2 — основные сервисы

Twenty + n8n + OpenWebUI + OpenClaw + LiteLLM + Qdrant.

## Phase 3 — собственное

Telegram-бот (`src/`) и сайт на Astro.
