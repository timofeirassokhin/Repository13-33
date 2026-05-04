# tr-com — стек timofeirassokhin.com

Параллельный стек на том же VPS, что и 13-33. Делит общую сеть `proxy` (Traefik + ACME),
делит MemPalace для базы знаний; всё остальное — отдельные инстансы.

## Сервисы

| Подпапка | Что | Hostname (Traefik) |
|---|---|---|
| `twenty/` | Twenty CRM (отдельный инстанс, prefix `twenty-tr-`) | `crm.timofeirassokhin.com` |
| `listmonk/` | Newsletter (Listmonk + Postgres), SMTP-релей через Unisender | `mail-admin.timofeirassokhin.com` (basic-auth + admin-IP allowlist) |
| `bot/` | Telegram-бот `@timofeirassokhin_bot` (Python, polling) | — (не публичный) |
| `glue/` | webhook-router: Robokassa, форма подписки → Twenty + Unisender + Calendar | `glue.timofeirassokhin.com` (только нужные пути) |

Сайт `timofeirassokhin.com` — отдельный сервис в `sites/timofeirassokhin.com/` (Astro static, как у 13-33).

## Деплой

1. `cd /opt/stack/Repository13-33`
2. `git pull origin main`
3. `cp infra/.env.example infra/.env` *(если ещё не сделано)* и заполни `infra/tr-com/.env.example` → `infra/tr-com/.env`
4. `bash infra/scripts/link-env.sh` — симлинки `.env` во все подпапки
5. По очереди:
   ```bash
   docker compose -f infra/tr-com/twenty/docker-compose.yml --env-file infra/.env --env-file infra/tr-com/.env up -d
   docker compose -f infra/tr-com/listmonk/docker-compose.yml --env-file infra/.env --env-file infra/tr-com/.env up -d
   docker compose -f infra/tr-com/glue/docker-compose.yml --env-file infra/.env --env-file infra/tr-com/.env up -d
   docker compose -f infra/tr-com/bot/docker-compose.yml --env-file infra/.env --env-file infra/tr-com/.env up -d
   docker compose -f sites/timofeirassokhin.com/docker-compose.yml --env-file infra/.env up -d
   ```

Сначала Twenty (это долго — миграции БД), потом всё остальное.

## Переменные окружения

См. `infra/tr-com/.env.example`. Общие переменные (`ACME_EMAIL`, `ADMIN_IP`, `TRAEFIK_BASIC_AUTH`)
наследуются из `infra/.env`.

## Сеть

- Все публичные сервисы → external network `proxy` (там же Traefik и MemPalace)
- Внутри tr-com БД и приватные связи → отдельная сеть `tr-com-internal`
- MemPalace доступен по `http://mempalace:8080` для бота, glue и любого другого сервиса tr-com

## MemPalace wings, выделенные под tr-com

- `tr-publications` — опубликованные посты с сайта
- `tr-drafts` — черновики
- `tr-trainings` — материалы тренингов
- `voice-tr` — корпус голоса автора (общий с 13-33)

Создание: см. `infra/mempalace/init_wings.py` (после деплоя добавлю команду).
