# Gluvex — состояние системы и operational reference

**Версия:** 1.0
**Дата:** 2026-05-11
**Сервер:** `45.66.117.251` (Selectel, 16 vCPU / 64 GB RAM / 512 GB NVMe, Ubuntu 24.04)
**Статус:** Phase 3.5 завершена, инфраструктура полностью готова

> Этот документ — **operational reference**. Описывает что где живёт, как достучаться, как чинить.
> **Архитектурные принципы** — в [`master-data-architecture.md`](master-data-architecture.md).
> **Tender pipeline** — в [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

---

## 1. Карта публичных URL

| Сервис | URL | Что это | Кто использует |
|---|---|---|---|
| Twenty CRM | https://crm.gluvex.com | основной интерфейс продаж | команда менеджеров |
| LiteLLM | https://litellm.gluvex.com | router моделей (с master key) | все агенты (через LiteLLM endpoint) |
| Camunda Tasklist + Cockpit | https://bpm.gluvex.com | BPMN workflow, аппрувы | менеджеры (для approval tasks), админ |
| MinIO Console | https://files.gluvex.com | UI управления файлами в buckets | админ, ML/DevOps |
| Bot webhook | https://bot.gluvex.com | Telegram-бот (пока 503 placeholder) | менеджеры |

Все 5 поддоменов имеют:
- HTTPS Let's Encrypt сертификаты (auto-renewal через Caddy)
- HSTS (`max-age=31536000`)
- noindex для поисковиков (`X-Robots-Tag` + `robots.txt: Disallow: /`)

## 2. Внутренние сервисы (без публичного URL)

| Сервис | Internal endpoint | Назначение | Кто ходит |
|---|---|---|---|
| Postgres app-db | `app-db:5432` | мастер-данные / mempalace / camunda | gluvex_app role + сервисы |
| Postgres twenty-db | `twenty-db:5432` | данные Twenty | только Twenty |
| Redis twenty-redis | `twenty-redis:6379` | очереди BullMQ Twenty | только Twenty |
| Qdrant | `qdrant:6333` (HTTP), `:6334` (gRPC) | векторный индекс | mempalace-gluvex, будущий retrieval-api |
| MinIO API | `minio:9000` (S3 protocol) | программная работа с buckets | сервисы (ingestion, backups) |
| MemPalace Gluvex | `mempalace-gluvex:8080` | агентная память | агенты через MCP / REST |

## 3. Полная инвентаризация контейнеров

| Container | Image | Сеть | Healthcheck |
|---|---|---|---|
| `caddy` | `caddy:2-alpine` | `proxy` | внешний — `manage.sh health` |
| `twenty-server` | `twentycrm/twenty:v1.23.9` | `proxy`, `twenty_internal` | `curl /healthz` |
| `twenty-worker` | `twentycrm/twenty:v1.23.9` | `twenty_internal` | — |
| `twenty-db` | `postgres:16` | `twenty_internal` | `pg_isready` |
| `twenty-redis` | `redis:7-alpine` | `twenty_internal` | `redis-cli ping` |
| `litellm` | `ghcr.io/berriai/litellm:main-latest` | `proxy` | `/health/liveliness` |
| `app-db` | `postgres:16` | `app_internal` | `pg_isready` |
| `minio` | `minio/minio:latest` | `proxy`, `app_internal` | `mc ready local` |
| `qdrant` | `qdrant/qdrant:latest` | `app_internal` | TCP probe `:6333` |
| `camunda` | `camunda/camunda-bpm-platform:run-7.21.0` | `proxy`, `app_internal` | `wget /camunda/app/welcome/` |
| `mempalace-gluvex` | `gluvex/mempalace-gluvex:local` | `app_internal` | `/health` |

**Сети:**
- `gluvex_proxy` — публичные сервисы за Caddy
- `gluvex_twenty_internal` — изоляция Twenty stack
- `gluvex_app_internal` — основной слой Gluvex (app-db, mempalace, qdrant, minio)

## 4. Базы данных Postgres

### 4.1. `app-db:5432` (наш мастер)

| База | Owner | Назначение |
|---|---|---|
| `gluvex_documents` | `gluvex_app` | master-data слой (см. ниже) |
| `mempalace` | `mempalace` | пусто — задел под MemPalace (сейчас MemPalace использует SQLite в volume) |
| `camunda` | `camunda` | BPMN engine state (Camunda управляет схемой сама) |

### 4.2. `gluvex_documents` — 11 таблиц мастер-данных

| Таблица | Назначение | Кто пишет |
|---|---|---|
| `document_registry` | реестр всех файлов (метаданные; контент в MinIO) | ingestion API, 1c-bridge, manual upload |
| `document_chunks` | чанки текста + FTS `tsvector` (vectors в Qdrant) | ingestion pipeline |
| `entity_links` | cross-system ID mapping (1С / Twenty / Tenderland) | 1c-bridge, tender-pipeline |
| `audit_events` | **append-only** журнал всех событий | все сервисы (через INSERT) |
| `llm_runs` | трассировка AI-решений | все агенты |
| `retrieval_log` | **append-only** лог retrieval-events | retrieval API |
| `agent_policies` | retrieval whitelist per agent | админ, миграции |
| `sync_runs` | прогоны синхронизации | 1c-bridge, tenderland-search |
| `sync_errors` | детальные ошибки sync | 1c-bridge |
| `status_history` | смена статусов любых сущностей | все сервисы |
| `human_reviews` | ручные решения менеджеров | Twenty webhook → handler |

**Защита:** `audit_events` и `retrieval_log` имеют `REVOKE UPDATE, DELETE` для `gluvex_app` — append-only на уровне БД.

**ENUM-типы:** `document_status` (`draft|pending_review|actual|archive|forbidden|expired`), `document_type_t` (19 значений), `access_level_t`, `source_type_t`.

**Seeded:** 4 `agent_policies` — `tender_analyzer`, `product_manager`, `kp_agent`, `email_agent`.

### 4.3. `twenty-db:5432` — данные Twenty

Управляется Twenty CRM. Workspace: `Gluvex CRM` (id `c450b453-9745-4b25-a95f-7351eecc413d`, subdomain `gluvex`). 1 юзер: `t.rassokhin@gluvex.com`.

Кастомные поля Company: `inn` (unique), `ogrn`, `kpp` (созданы через `seed_twenty_metadata.py`).

## 5. MinIO — buckets

**API:** `http://minio:9000` (internal)
**Console:** https://files.gluvex.com (external, root login)
**Master credentials:** в `/opt/gluvex/secrets/.env` (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`)

| Bucket | Назначение | Versioning |
|---|---|---|
| `raw-documents` | staging до классификации (TTL 30 дней) | — |
| `product-brochures` | брошюры производителей | — |
| `prices` | прайсы (с `valid_from/until` в metadata) | ✅ |
| `kp-templates` | шаблоны КП | ✅ |
| `kp-generated` | сгенерированные КП клиентам | — |
| `tenders` | zip-архивы из Tenderland + распакованные ТЗ | — |
| `sop` | внутренние SOP, регламенты | ✅ |
| `methodologies` | клиентские методики | ✅ |
| `client-files` | файлы по клиентам (партиции по ИНН) | — |
| `archive` | архивные версии | — |
| `qdrant-snapshots` | бэкапы Qdrant | — |
| `postgres-backups` | дампы Postgres (доп. копия к локальным) | — |
| `audit-exports` | выгрузки audit log | — |

Шифрование SSE-S3 — включается отдельным шагом (TODO).

## 6. Qdrant collections

**Endpoint:** `http://qdrant:6333` (internal)
**Аутентификация:** не настроена (доступ только из docker network)

| Collection | Размерность | Кто пишет | Назначение |
|---|---|---|---|
| `memories` | 384 (mpnet-base) | mempalace-gluvex | агентная память (drawers) |

В будущем добавятся:
- `document_chunks_<embedding_model>` — vectors для retrieval API
- `tender_specs` — извлечённые характеристики ТЗ

## 7. MemPalace Gluvex

**Endpoint:** `http://mempalace-gluvex:8080` (internal)
**Backend:** Qdrant (`memories` collection) + SQLite (KG в `/data/palace/knowledge_graph.sqlite3`)
**Embedding model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim, ru/en)

### 7.1. Wings (домены памяти)

| Wing | Для каких задач | Кто пишет/читает |
|---|---|---|
| `gluvex-products` | каталог приборов, синонимы, совместимость | product_manager, tender_analyzer |
| `gluvex-clients` | клиенты, история закупок, тон коммуникации | kp_agent, email_agent |
| `gluvex-tenders` | паттерны ТЗ, скрытые требования, кейсы | tender_analyzer |
| `gluvex-kp` | шаблоны КП, удачные формулировки, скидки | kp_agent |
| `gluvex-knowledge` | методики, SOP, регламенты | все агенты |

### 7.2. REST endpoints

| Метод | URL | Тело | Возвращает |
|---|---|---|---|
| `GET` | `/health` | — | `{status, total_drawers, backend}` |
| `GET` | `/wings` | — | `{wings: [{wing, drawer_count}], total}` |
| `POST` | `/drawer` | `{content, wing, room, title?, tags?, added_by?}` | `{id, wing, room}` |
| `GET` | `/drawer/{id}` | — | `{id, content, metadata}` |
| `DELETE` | `/drawer/{id}` | — | `{deleted}` |
| `POST` | `/search` | `{query, wing?, room?, n_results, max_distance}` | `{results: [...], count}` |
| `POST` | `/kg/add` | `{subject, predicate, object, valid_from?}` | `{triple_id}` |
| `POST` | `/kg/query` | `{entity, direction: outgoing\|incoming\|both, as_of?}` | `{facts: [...], count}` |
| `GET` | `/kg/stats` | — | `{entities, triples, current_facts, relationship_types}` |

### 7.3. Как агенту использовать

**Из контейнера в `gluvex_app_internal` сети:**
```bash
curl -sS -X POST http://mempalace-gluvex:8080/search \
  -H "Content-Type: application/json" \
  -d '{"query": "сушильный шкаф 30-300C", "wing": "gluvex-products", "n_results": 5}'
```

**Через MCP** (для Claude/Cursor) — после того как настроим MCP-server-mempalace на этом инстансе (TODO Phase 4).

## 8. Camunda 7 CE

**URL:** https://bpm.gluvex.com
**Дефолтный логин:** `demo / demo` — **сменить при первом входе!**
**REST API:** https://bpm.gluvex.com/engine-rest/

### 8.1. Базовые endpoints

| Назначение | URL |
|---|---|
| Welcome | https://bpm.gluvex.com/camunda/app/welcome/ |
| Tasklist (задачи менеджеров) | https://bpm.gluvex.com/camunda/app/tasklist/ |
| Cockpit (admin процессов) | https://bpm.gluvex.com/camunda/app/cockpit/ |
| Engine REST | https://bpm.gluvex.com/engine-rest/ |
| Deploy process (POST BPMN) | https://bpm.gluvex.com/engine-rest/deployment/create |

### 8.2. Готовые процессы

Пока нет — задел под:
- `document_approval` (draft → actual)
- `price_change` (с DMN-эскалацией по %)
- `tender_routing` (decision pass / review / fail)
- `kp_generation` (auto-draft → review → send)

## 9. LiteLLM router

**URL:** https://litellm.gluvex.com
**Master key:** в `/opt/gluvex/secrets/.env` (`LITELLM_MASTER_KEY`)
**OpenRouter key:** **пока пустой** — заполнить в `/opt/gluvex/secrets/.env`, перезапустить `manage.sh restart litellm`

### 9.1. Модельные алиасы

| Алиас | Реальная модель | Когда |
|---|---|---|
| `cheap` | `openrouter/anthropic/claude-haiku-4.5` | классификация файлов в zip, быстрый routing |
| `creative` | `openrouter/anthropic/claude-sonnet-4.5` | парсинг ТЗ, matching продуктов, генерация КП-draft |
| `premium` | `openrouter/anthropic/claude-opus-4.5` | спорные кейсы, длинный контекст |
| `claude-sonnet-4.5` / `claude-haiku-4.5` / `claude-opus-4.5` | прямые имена | прямой выбор модели |

### 9.2. Как агенту вызывать

```bash
curl -sS https://litellm.gluvex.com/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "creative", "messages": [{"role":"user","content":"Hi"}]}'
```

## 10. Twenty CRM

**URL:** https://crm.gluvex.com
**Workspace:** `Gluvex CRM`
**API token:** в `/opt/gluvex/secrets/.env` (`TWENTY_API_TOKEN`)

### 10.1. API endpoints

| Назначение | URL |
|---|---|
| Frontend | https://crm.gluvex.com/ |
| REST API | https://crm.gluvex.com/rest/ |
| GraphQL | https://crm.gluvex.com/graphql |
| Metadata GraphQL | https://crm.gluvex.com/metadata |
| Metadata REST | https://crm.gluvex.com/rest/metadata/ |

### 10.2. Сейчас есть кастомные поля

- `Company.inn` (TEXT, unique) — ключ дедупа по ИНН
- `Company.ogrn`, `Company.kpp`

**Ещё нет** (до структуры из 1С):
- Кастомный объект `tenderLead` или поля на Opportunity
- 3 раздельные воронки лидов (`website_leads`, `tender_leads`, `manager_leads`)
- Поля Person/Deal/Lead под 1С-структуру

## 11. Файловая система сервера

```
/opt/gluvex/
├── repos/
│   └── Repository13-33/           # git clone от deploy key
│       └── tenderland_bot/
│           ├── docs/              # архитектурные документы
│           │   ├── master-data-architecture.md
│           │   ├── storage-architecture.md
│           │   └── system-state.md       ← этот документ
│           ├── catalog/           # каталог продукции
│           └── infra/gluvex_tender_machine/
│               ├── bootstrap_phase1.sh
│               ├── bootstrap_phase2.sh
│               ├── scripts/
│               │   ├── backup-twenty.sh   # cron @ 03:00
│               │   ├── backup-tender-monitor.sh
│               │   └── seed_twenty_metadata.py
│               └── stack/         # ← главная папка деплоя
│                   ├── docker-compose.yml
│                   ├── Caddyfile
│                   ├── litellm-config.yaml
│                   ├── manage.sh         # ./manage.sh {up,down,status,logs,health,update}
│                   ├── .env -> /opt/gluvex/secrets/.env   (симлинк)
│                   ├── app-db-init.sql (с подставленными паролями, .gitignored)
│                   ├── migrations/
│                   │   ├── 001_initial_schema.sql
│                   │   └── apply.sh
│                   └── mempalace-gluvex/
│                       ├── Dockerfile
│                       ├── qdrant_backend.py
│                       ├── service.py
│                       └── init_wings.py
├── secrets/
│   └── .env                       # все секреты (chmod 600)
├── backups/
│   └── twenty/                    # nightly pg_dump gzip, ротация 14 дней
├── logs/
│   └── backup-twenty.log
└── tenders_data/                  # под /var/lib/tenders/ для tender-pipeline
```

## 12. Секреты — /opt/gluvex/secrets/.env

**Видимы только пользователю `gluvex`** (`chmod 600`). НЕ в git.

| Переменная | Что |
|---|---|
| `DOMAIN` | `gluvex.com` |
| `ACME_EMAIL` | `timofei.rassokhin@gmail.com` |
| `TWENTY_PG_PASSWORD` | Postgres для Twenty |
| `TWENTY_APP_SECRET` | APP_SECRET Twenty |
| `LITELLM_MASTER_KEY` | мастер-ключ LiteLLM API |
| `LITELLM_SALT_KEY` | salt для encryption virtual keys |
| `OPENROUTER_API_KEY` | **пустой** — заполнить |
| `APP_DB_PASSWORD` | postgres-master в app-db |
| `GLUVEX_APP_PG_PASSWORD` | прикладной юзер для gluvex_documents |
| `MEMPALACE_PG_PASSWORD` | юзер для БД mempalace |
| `CAMUNDA_PG_PASSWORD` | юзер для БД camunda |
| `MINIO_ROOT_USER` / `_PASSWORD` | MinIO root creds |
| `TWENTY_API_TOKEN` | API key из Twenty Settings |

## 13. Бэкапы

| Что | Куда | Когда | Где скрипт |
|---|---|---|---|
| Twenty Postgres | `/opt/gluvex/backups/twenty/*.sql.gz` | cron @ 03:00 МСК ежедневно | `infra/.../scripts/backup-twenty.sh` |
| app-db Postgres | — TODO | — | следующая итерация — расширим backup-twenty.sh |
| MinIO | — TODO (`mc mirror` на /opt/gluvex/backups/minio) | — | следующая итерация |
| Qdrant | — TODO (snapshot в qdrant-snapshots bucket) | — | следующая итерация |
| MemPalace SQLite KG | — TODO (включить в app-db backup) | — | — |

**Off-site backup** — пока на сервере. Через 6 месяцев перейдём на Yandex Object Storage / Backblaze B2 (Q7 из master-data-architecture.md).

## 14. Operational команды

### 14.1. Управление стеком

На сервере, в `stack/`:
```bash
./manage.sh status        # docker compose ps
./manage.sh up            # docker compose up -d
./manage.sh down          # docker compose down
./manage.sh restart litellm    # рестарт одного сервиса
./manage.sh logs camunda  # follow логи одного сервиса
./manage.sh logs          # все логи follow
./manage.sh update        # pull + up -d + image prune
./manage.sh health        # внешний health-check по 3 URL
./manage.sh shell minio   # bash в контейнер
```

### 14.2. Применение миграций к app-db

```bash
cd /opt/gluvex/repos/Repository13-33/tenderland_bot/infra/gluvex_tender_machine/stack/migrations
./apply.sh                # все миграции по порядку
./apply.sh 001_initial_schema.sql   # конкретная
```

### 14.3. Backup вручную

```bash
/opt/gluvex/repos/Repository13-33/tenderland_bot/infra/gluvex_tender_machine/scripts/backup-twenty.sh
ls /opt/gluvex/backups/twenty/
```

### 14.4. Восстановление из backup

```bash
docker compose stop twenty-server twenty-worker
zcat /opt/gluvex/backups/twenty/twenty_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i twenty-db psql -U postgres -d default
docker compose up -d twenty-server twenty-worker
```

### 14.5. Создание API key в Twenty

UI: https://crm.gluvex.com → Settings → Developers → API Keys → Create

Программно (зная JWT-схему Twenty) пока не поддерживается через REST.

## 15. Карта git-коммитов Phase 3-3.5

```
a91e842  MemPalace на Qdrant — отдельный инстанс под Gluvex (Phase 3.5 завершение)
816321f  Phase 3.5 миграции — gluvex_documents schema init (11 таблиц + 4 ENUM)
fc642e2  Phase 3.5 системный фундамент (app-db / minio / qdrant / camunda)
85f0da8  rename server hostname gluvex-tender-machine -> gluvex
bec7b09  master-data architecture (1С как master) + storage architecture
779bf88  Twenty pinned to v1.23.9 + password auth env vars
7ac142b  общая настройка — бэкап-cron, manage.sh, перенос New project/
2a064e2  Phase 3 stack — Caddy + Twenty CRM + LiteLLM
e0f0fe3  migration guide для разделения на два компа
2977497  handoff документ для следующей сессии
e5a3839  фаза 1 — отладка автопоисков Tenderland + план VPS
```

PR: https://github.com/timofeirassokhin/Repository13-33/pull/6

## 16. Что осталось до Phase 4

| Блокер | Зависит от |
|---|---|
| `OPENROUTER_API_KEY` в `.env` | заказчик |
| Структура полей в 1С (Q1) | заказчик |
| API контракт 1С (REST? OData?) — Q2 | заказчик |
| Camunda admin password (поменять demo/demo) | заказчик (5 минут в UI) |
| Off-site backup провайдер | через 6 мес |

## 17. Что планируется в Phase 4

1. **Каталог приборов Gluvex** — парсер с сайта Gluvex → JSON → `document_registry` + `gluvex-products` wing MemPalace
2. **База Illumina + MGI + AmoyDx** — каталоги поставщиков → MemPalace `gluvex-products`
3. **1c-bridge scaffold** (FastAPI + mock 1С) — готов принять реальный 1С API
4. **tender-pipeline scaffold** (Searcher → Analyzer → CRM Pusher, по `ARCHITECTURE.md`)
5. **3 раздельные воронки лидов в Twenty** — после получения структуры 1С
6. **Стартовые BPMN-процессы Camunda** — document_approval, price_change

---

_Документ обновляется при каждом серьёзном изменении инфраструктуры. Любое расхождение между этим документом и реальностью — bug._

## 18. Vendor crawls — текущее состояние (2026-05-12)

| Brand | Records | Datasheets | Crawler status |
|---|---|---|---|
| Sartorius | 160 | 160 PDF | ✅ done |
| Sciex | 116 | 115 PDF | ✅ done |
| BANDELIN | 51 | 47 md | ✅ done (через IPRoyal proxy) |
| Metrohm | 38 | 38 PDF | ✅ done |
| Huber | 31 | 30 md | ✅ done (через IPRoyal proxy) |
| Bruker | 24 | 24 PDF | ✅ done |
| Memmert | 20 | 20 md + 435 PDF | 🟡 PDF собраны, matching не работает |
| Heidolph | 7 | 7 md | 🟡 mало deeper pages |
| Shimadzu | 6 | 6 md | ✅ done |
| Thermo Fisher | 6 | 6 md | ✅ done |
| SOTAX | 4 | 4 md | 🟡 partial |
| CAMAG | 1 | 1 md | ❌ сайт нестабилен |

**Итого vendor data:** 464 записей, 458 с datasheet (98.7%)
**В MinIO:** ~700 файлов в product-brochures/ (PDF + markdown)

**IPRoyal residential proxy:** PROXY_URL в /opt/gluvex/secrets/.env
**Использовано трафика:** ~0.1 GB из 5 GB plan

