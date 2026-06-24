# gluvex_documents — миграции БД

Содержит DDL для всех таблиц мастер-данных и retrieval-слоя.

## Структура

```
migrations/
├── 001_initial_schema.sql    # все 11 таблиц + 4 ENUM-типа + seed для agent_policies
├── 002_*.sql                 # будущие миграции (по мере эволюции)
└── apply.sh                  # применяет миграции к app-db
```

## Применение

На сервере:
```bash
cd /opt/gluvex/repos/Repository13-33/tenderland_bot/infra/gluvex_tender_machine/stack/migrations
./apply.sh
```

Применяет все `*.sql` по порядку. Идемпотентно — повторный запуск безвредный.

## Таблицы (с master-data-architecture.md / storage-architecture.md)

| Таблица | Зачем |
|---|---|
| `document_registry` | реестр всех файлов системы (метаданные; файлы в MinIO) |
| `document_chunks` | чанки текста + FTS (`tsvector`) для hybrid retrieval (vectors в Qdrant) |
| `entity_links` | cross-system ID mapping (1С / Twenty / Tenderland / internal) |
| `audit_events` | append-only журнал всех изменений и событий |
| `llm_runs` | трассировка AI-решений (input/output/explanation/cost) |
| `retrieval_log` | каждый retrieval-event агента (append-only) |
| `agent_policies` | retrieval whitelist per agent (default-deny) |
| `sync_runs` | прогоны синхронизации с внешними системами |
| `sync_errors` | детальные ошибки sync с retry-state |
| `status_history` | история смены статусов (для любой entity) |
| `human_reviews` | ручные решения менеджеров + метрика takes_ai_advice |

## ENUM-типы

- `document_status` — draft / pending_review / actual / archive / forbidden / expired
- `document_type_t` — brochure / price / sop / tz / offer / kp_template / kp_generated / ...
- `access_level_t` — public / internal / confidential / restricted
- `source_type_t` — 1c_supplier / 1c_export / 1c_bridge / tenderland / manual_upload / ...

## Append-only защита

`audit_events` и `retrieval_log` получают `REVOKE UPDATE, DELETE` для роли `gluvex_app`.
Только postgres (master) может изменять — на случай SQL-injection в приложении.

## Seed

`001_initial_schema.sql` сразу заливает 4 стартовые `agent_policies`:
- `tender_analyzer`, `product_manager`, `kp_agent`, `email_agent`

Каждая со своим whitelist'ом `document_type × status`. См. master-data-architecture.md раздел 6.

## В будущем

Когда понадобится миграция меняющая существующие столбцы — переходим на **alembic**:
- модели в `services/gluvex-db/src/gluvex_db/models.py` (SQLAlchemy)
- alembic-autogenerate → миграции
- этот SQL-based подход останется как baseline (`001_initial_schema.sql`)
