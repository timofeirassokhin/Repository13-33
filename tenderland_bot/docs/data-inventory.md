# Gluvex — инвентаризация базы данных (сводка по слоям)

**Снимок:** 2026-05-22. Сервер `45.66.117.251` (gluvex.com), стек `gluvex_app_internal`.
Документ описывает фактическое наполнение базы по 4 слоям и как они связаны.
(Архитектурный замысел — в [`data-layers-architecture.md`](data-layers-architecture.md) и [`catalog-architecture.md`](catalog-architecture.md).)

---

## Поток данных

```
СЫРЬЁ                ИЗВЛЕЧЕНО / СТРУКТУРА                ПОИСК
MinIO (файлы)  ──►  Postgres (каталог + текст/FTS)  ──►  Qdrant (вектора)
                              │                                 ▲
                              └── object_key / document_id ──────┘
                                                            MemPalace (HTTP API)
                          всё доступно агентам через MCP `catalog-mcp` (10 tools)
```

Файл в MinIO → его текст извлечён в `document_registry` (метаданные) + `document_chunks` (текст + FTS) → каждый чанк векторизован в Qdrant (доступ через MemPalace). Карточка продукта: `product.base_specs` (структура) + `datasheet_paths` → MinIO + чанки → семантика.

**Сводно:** 3 960 файлов (6.7 ГиБ) → 72 724 продукта (39 379 со структурой) + 3 490 документов → 67 721 чанк → 67 726 векторов. **65 брендов**, приборы и расходка.

---

## Слой 1 — MinIO (объектное хранилище, сырьё)

**Итого: 6.7 ГиБ, 3 960 объектов.** UI/эндпоинт: `files.gluvex.com`. 13 бакетов.

### `product-brochures/` — ~3 896 файлов (PDF + Markdown), 24 вендор-префикса
| Бренд | Файлов | Бренд | Файлов | Бренд | Файлов |
|---|---|---|---|---|---|
| shimadzu | 1249 | helicon | 652 | illumina | 515 |
| memmert | 489 | sartorius | 222 | sotax | 182 |
| sciex | 128 | agilent | 106 | thermofisher | 68 |
| metrohm | 62 | bruker | 48 | bandelin | 48 |
| camag | 31 | huber | 30 | heidolph | 15 |
| amoydx | 10 | vibra | 9 | schmidt_haensch | 8 |
| mgi_tech | 8 | sesana | 5 | salus_bio | 5 |
| parseq | 4 | liebherr | 1 | burning_rock | 1 |

Путь: `product-brochures/<brand_slug>/<file>.pdf|.md`.

Размер: **product-brochures 6.7 ГиБ / 3 896 объектов**.

### `tenders/` — 6.0 МиБ / 63 файла
ТЗ / описания объекта закупки / предложения участника. Путь: `tenders/src/<менеджер>/<год>/<file>` (docx/doc/xlsx/rtf/pdf).

### Служебные бакеты (заготовлены, пока пустые)
`archive`, `prices`, `kp-templates`, `kp-generated`, `sop`, `raw-documents`, `methodologies`, `client-files`, `audit-exports`, `postgres-backups`, `qdrant-snapshots`.

---

## Слой 2 — Postgres `gluvex_documents` (app-db, структурный слой)

| Таблица | Объектов | Назначение |
|---|---|---|
| **product** | **72 724** | каталог продукции; **65 брендов, 41 категория** |
| → с `base_specs` (JSONB) | **39 379** | структурные характеристики |
| → с `datasheet_paths` | 13 464 | ссылки на PDF в MinIO |
| **document_registry** | **3 490** | реестр документов (версионируемый) |
| **document_chunks** | **67 721** | чанки текста + русский FTS (tsvector) |
| product_configuration | 86 | NGS: reagent-киты / ячейки |
| sequencer_runtime_metric | 86 | NGS: производительность по режимам |
| product_slot | 25 | NGS: слоты flow cell |
| product_compatibility | 86 | NGS: совместимость (installable_in) |
| brochure_documents (legacy) | 119 | старая FTS-таблица (SOTAX/Memmert/CAMAG) |

### `document_registry` по типам
`brochure` — 3 430 · `tz` (техзадания) — 51 · `offer` (предложения/заявки) — 9.

### `product.base_specs` — что внутри
JSONB со структурными полями, извлечёнными LLM из брошюр/названий. Единицы в именах ключей:
- **Приборы:** `wavelength_range_nm` `[min,max]`, `mass_range_mz`, `pressure_max_bar`, `flow_rate_ml_min`, `temp_range_c`, число каналов/детекторов, разрешение, пределы обнаружения.
- **Расходка:** `membrane_material`, `pore_size_um`, `diameter_mm`, `sterile`, `volume_ml`, `pack_size`, `filter_type`, `septum_material`, `column_phase`, `carbon_filter_type`.
- **Всегда:** `catalog_numbers[]`, `applications[]`, `summary_ru`.

Покрытие base_specs (топ-категории): mass_spectrometer 231/243 · hplc_system 144/275 · uv_vis 41/142 · инкубаторы 30/30 · расходка (Hawach/DWK/TopAir/Gluvex/HTA) ~100%. Без структуры намеренно оставлен `spare_part` (~33k криптовых запчастей — ищутся через FTS/семантику по названию).

### `product` по всем 41 категориям (всего / со структурой base_specs)

| Категория | Всего | base_specs | Категория | Всего | base_specs |
|---|---|---|---|---|---|
| spare_part | 33195 | 1 | laminar_hood | 52 | 52 |
| other | 26022 | 25931 | realtime_pcr_kit | 46 | 46 |
| ngs_library_prep_kit | 3333 | 3307 | pcr_kit | 38 | 37 |
| hplc_column | 2080 | 2079 | ftir_spectrometer | 34 | 33 |
| gc_column | 1539 | 1539 | incubator | 30 | 30 |
| consumable | 1220 | 1214 | dna_extraction_kit | 18 | 17 |
| syringe_filter | 896 | 896 | hplc_autosampler | 17 | 17 |
| accessory | 896 | 895 | biological_safety_cabinet | 17 | 17 |
| service | 552 | 552 | gc_module | 16 | 16 |
| spe_cartridge | 458 | 453 | water_purifier | 12 | 12 |
| sequencer_reagent_kit | 301 | 301 | titrator | 10 | 10 |
| hplc_system | 275 | 274 | hplc_detector | 5 | 5 |
| mass_spectrometer | 243 | 243 | centrifuge | 4 | 4 |
| climate_chamber | 151 | 151 | ngs_amplicon_panel | 4 | 4 |
| gc_system | 147 | 147 | aas_system | 3 | 3 |
| sequencer_platform | 145 | 142 | sequencer_flowcell | 1 | 0 |
| ngs_target_capture_panel | 143 | 140 | | | |
| uv_vis_spectrometer | 142 | 141 | | | |
| software | 140 | 137 | | | |
| shaker_vortex | 119 | 115 | | | |
| icp_ms | 118 | 117 | | | |
| vial | 92 | 91 | | | |
| balance | 79 | 79 | | | |
| icp_oes | 74 | 74 | | | |
| drying_oven | 57 | 57 | | | |

`spare_part` намеренно без структурных base_specs.

### NGS-каталог (структурный пилот)
35 платформ (Illumina/MGI/GeneMind/Salus + 7 RU-OEM Геноскан/Helicon/БиоФьюжн через `oem_of_id`), 86 китов + 86 runtime-метрик + слоты + совместимость, с РУ Росздравнадзора.

---

## Слой 3 — Qdrant (векторный поиск)

- **Коллекция:** `memories` — **67 726 точек** (67 721 проиндексировано).
- **Вектор:** 384-d, distance Cosine. Модель эмбеддинга `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (мультиязычная RU+EN).
- **1 точка = 1 чанк** из `document_chunks` (1:1). Payload: `wing`, `room`(бренд), `source_file`, текст.
- Эндпоинт `qdrant:6333` (внутри стека).

---

## Слой 4 — MemPalace (HTTP API над Qdrant для агентов)

- Эндпоинт `mempalace-gluvex:8080`, backend Qdrant, **67 726 drawers**.
- API: `/search` (семантика, фильтр по wing), `/drawer` (add), `/wings`, `/health`, `/kg/*` (knowledge graph).
- **Wings (рубрики):**
  - `gluvex-products` — ~67.7k (брошюры всех брендов)
  - `gluvex-tenders` — 68 (ТЗ/закупки/предложения)
  - заготовлены пустые: `gluvex-kp`, `gluvex-clients`, `gluvex-knowledge`

---

## Доступ для агентов — MCP `catalog-mcp`

HTTP-сервис `catalog-mcp:8090/mcp` (в docker-compose). 10 read-only инструментов:
`gluvex_search_documents` (семантика), `gluvex_search_chunks_fts` (FTS), `gluvex_search_products`,
`gluvex_query_products_by_spec` (фильтр по base_specs), `gluvex_get_product` (карточка),
`gluvex_get_datasheets`, `gluvex_find_sequencer`, `gluvex_resolve_oem`,
`gluvex_catalog_overview`, `gluvex_list_spec_fields`.

Telegram-бот `@gluvexlibrary_bot` (`library-bot`) — поиск + карточки по запросу.

---

## Пайплайны наполнения/обновления (`infra/.../stack/scripts/`)

| Скрипт | Что делает |
|---|---|
| `ingest_rag.py` | MinIO брошюры (pdf+md, PyMuPDF) → document_registry + document_chunks |
| `ingest_docs.py` | тендерные доки (docx/doc/xlsx/rtf/pdf) → RAG + wing gluvex-tenders |
| `embed_corpus.py` | bulk-эмбеддинг всех чанков → Qdrant |
| `extract_specs.py` | LLM (LiteLLM) извлечение base_specs (режимы datasheet / names) |
| `seed_ngs_full.sql` | NGS-каталог: платформы/киты/метрики/OEM |
| `ngs_specs/*.md` | researched спец-матрицы Illumina/MGI/GeneMind/Salus + RU OEM |

**Расширение:** новые группы товаров → добавить продукты → `ingest_rag` + `extract_specs` + `embed_corpus`; MCP отдаёт автоматически (схема `base_specs` JSONB + `query_products_by_spec` работают по любым полям).

---

## Известные нюансы
- Бренд-дубли в каталоге: `memmert`/`Memmert`, `HTA Italia`/`HTA_2025` (нормализовать).
- `spare_part` (~33k) — без структурных base_specs (по дизайну).
- LiteLLM маршрут `cheap` имеет дефолт max_tokens=64000 → при низком балансе OpenRouter 402; в запросах ставить `max_tokens` явно.
