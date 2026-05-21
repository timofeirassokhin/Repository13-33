# gluvex_catalog_mcp

MCP-сервер с read-only инструментами поверх каталога Gluvex + RAG-слоя.
Используется агентами **tender_analyzer** и **product_manager**.

## Бэкенды
- **PostgreSQL** `app-db` / БД `gluvex_documents` (каталог, конфигурации, runtime-метрики, document_chunks FTS)
- **MemPalace** HTTP `http://mempalace-gluvex:8080` (семантический поиск, Qdrant + multilingual embeddings)

## Инструменты (7)
| Tool | Назначение |
|---|---|
| `gluvex_search_documents` | Семантический поиск (RU/EN) по брошюрам/тендерам (MemPalace) |
| `gluvex_search_chunks_fts` | Полнотекстовый (точный) поиск по чанкам (Postgres russian tsv) — part numbers, коды |
| `gluvex_find_sequencer` | **Конфигуратор**: подбор платформа+кит по выходу/режиму/применению/бренду/Q30/РУ |
| `gluvex_get_platform` | Детали платформы: base_specs, слоты, киты+метрики, OEM (резолвит RU-ребренды) |
| `gluvex_resolve_oem` | RU-ребренд ↔ оригинал (+ РУ Росздравнадзора) |
| `gluvex_search_products` | Поиск по каталогу (model/vendor_code/display_name) + кол-во datasheet'ов |
| `gluvex_get_datasheets` | MinIO-пути брошюр/datasheet'ов продукта |

## Запуск
**stdio (локально / для агент-раннера):**
```bash
PGPASSWORD=*** python -m gluvex_catalog_mcp.server
```
**HTTP (в стеке, для нескольких клиентов):**
```bash
MCP_TRANSPORT=http MCP_PORT=8090 python -m gluvex_catalog_mcp.server
```
Env: `PGHOST,PGUSER,PGPASSWORD,PGDATABASE,MEMPALACE_URL,TENANT_ID`.

## Docker (в стеке gluvex_app_internal)
```bash
docker build -t gluvex-catalog-mcp services/catalog-mcp
docker run --rm --network gluvex_app_internal -e PGPASSWORD=$APP_DB_PASSWORD -p 8090:8090 gluvex-catalog-mcp
```

## Заметки
- Все инструменты read-only.
- В ответах `find_sequencer`/`get_platform` поле `source_confidence`/`confidence` < 0.8 = значение интерполировано/не подтверждено (см. `scripts/ngs_specs/*.md`) — сверять перед тендером.
- Источник истины спеков NGS: `scripts/ngs_specs/{illumina,mgi,genemind_sesana,salus_biofusion}.md`; seed: `scripts/seed_ngs_full.sql`.
