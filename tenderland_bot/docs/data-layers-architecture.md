# Gluvex — архитектура слоёв данных каталог → specs → тендеры

**Версия:** 1.0
**Дата:** 2026-05-14
**Иерархия документов:**
1. [`master-data-architecture.md`](master-data-architecture.md) — 1С как master, контуры
2. [`storage-architecture.md`](storage-architecture.md) — низкоуровневое хранилище (Postgres / MinIO / Qdrant)
3. [`catalog-architecture.md`](catalog-architecture.md) — схема `product` / `product_configuration` / `product_compatibility`
4. **(этот)** `data-layers-architecture.md` — стратегия наполнения 3 слоёв и связь с tender pipeline
5. [`system-state.md`](system-state.md) — operational state
6. [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — tender pipeline (Searcher + Analyzer + CRM Pusher)

> Этот документ описывает **стратегию построения знаний о приборах**: от сырых брошюр производителей до RAG-системы которая распознаёт что хочет заказчик в тендере и подбирает наш ассортимент.

---

## 0. TL;DR

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — RAW (брошюры/каталоги/datasheets)                                │
│  Источники: сайты производителей, дистрибьюторов, наши PDF                  │
│  Хранение: MinIO bucket `product-brochures`                                 │
│  Индекс: product.datasheet_paths, document_chunks (текст + FTS + vectors)   │
│  Обновление: monthly crawler (cron), новые версии складываются версиями     │
│  Состояние: 12 vendor crawlers готовы (analytical), 0 для NGS-генетики      │
└─────────────────────────────────────────────────────────────────────────────┘
                                  ↓ extraction
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 2 — STRUCTURED SPECS                                                 │
│  Что: вытащенные характеристики прибора по фиксированной схеме per category │
│  Хранение: product.base_specs (JSONB) + product_configuration.specs (JSONB) │
│  Дополнительно: sequencer_runtime_metric (для NGS платформ × FC × kit × RM) │
│  Источник: LLM extraction из брошюр + manual review менеджеров              │
│  Состояние: schema готова в catalog-architecture.md; pipeline НЕ построен   │
└─────────────────────────────────────────────────────────────────────────────┘
                                  ↓ matching
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 3 — TENDER MATCHING + RAG                                            │
│  Часть A: наши готовые ТЗ-шаблоны (загружаются как образцы)                 │
│  Часть B: входящие тендерные ТЗ (extracted из tender_pipeline analyzer)     │
│  Хранение: tender_tz_template (наши) + tender_analyses.extracted_specs      │
│  Матчер: extracted_specs → product catalogue → score + reasoning            │
│  Хранение: tender_match_result (per кандидат, with score)                   │
│  Состояние: каталог 39.8K продуктов есть, matcher и наши ТЗ — пока в плане  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Текущее состояние (по состоянию на 2026-05-14)

### 1.1. Что есть в `product` таблице

```
imported_from  | products | with_ds 
---------------+----------+---------
 gluvexlab     |  39,395  |     0
 agilent_sitemap|  3,552  |     0
 shimadzu      |    515   |   515
 sartorius     |    160   |   160
 sciex         |    116   |   115
 bandelin      |     51   |    47
 metrohm       |     38   |    38
 huber         |     31   |    30
 thermofisher  |     29   |    29
 bruker        |     24   |    24
 memmert       |     20   |    20
 heidolph      |      7   |     7
 sotax         |      4   |     4
 camag         |      1   |     1
ИТОГО           ~43,943    ~1,010 продуктов с datasheets
```

### 1.2. Что есть в MinIO `product-brochures`

- **~455 PDF** в `product-brochures/memmert/` (brochure-finder), **не linked** в `datasheet_paths`
- сотни в других brand-bucket'ах (sartorius / sciex / metrohm / bruker / shimadzu)
- **agilent_sitemap stubs** (3,552 stub-записи) без скачанных PDF
- **0 PDF для NGS-вендоров** (Illumina, MGI, Genemind, ONT, PacBio и др.)

### 1.3. Главные пробелы

| Категория | Пробел | Бизнес-impact |
|---|---|---|
| **Agilent** | 35,641 артикулов из gluvexlab + 3,552 stubs — **0 datasheets** | КРИТИЧНО. Самый большой бренд, сайт за Akamai (IPRoyal не пробивает) |
| **NGS / Генетика** | **0 вендоров** в БД (Illumina, MGI, Genemind, ONT, PacBio, Helicon, Salus, Pillar, Burning Rock, AmoyDx, Parseq, OncoAtlas, Nanodigm) | КРИТИЧНО. Растущий бизнес-вектор, в тендерах фигурируют ежедневно |
| **Layer 2 specs** | Pipeline вытаскивания specs из PDF не построен | matcher не сможет работать структурно |
| **Layer 3 наши ТЗ** | Образцы наших готовых ТЗ не загружены в систему | KP-агент не сможет генерировать заявки по template'у |

---

## 2. LAYER 1 — Брошюры и каталоги

### 2.1. Принципы

1. **Один файл — один PDF/MD/HTML** в MinIO, путь `product-brochures/<vendor_slug>/<basename>`
2. **`product.datasheet_paths`** — массив object-keys MinIO для всех файлов привязанных к продукту
3. **`document_registry`** — каждый файл получает запись с метаданными (vendor, model, source_url, content_hash, retrieved_at)
4. **`document_chunks`** — после загрузки PDF чанкуется → FTS (tsvector) + Qdrant vectors для RAG
5. **Дедуп по content_hash** — повторный crawl того же файла не пересохраняет

### 2.2. Strategy: Agilent (35K+ артикулов, без datasheets)

**Проблема:** прямой crawl `agilent.com` блокируется Akamai. IPRoyal residential тоже 403.

**3-уровневый план:**

#### Уровень 1 — Sitemap-only stubs (✅ сделано, 3552 stub-записей)
- `adapters/vendors/agilent_sitemap.py` берёт `agilent.com/products0.xml`
- Создаёт stub-records в `product` с `metadata: {stub_from_sitemap: true, needs_enrichment: true}`
- Извлекает только: vendor_code (артикул в URL), brand, category-hint
- **Без datasheets, без description, без specs**

#### Уровень 2 — Russian distributors (НЕ НАЧАТО, приоритет HANDOFF #1)

5 русских дистрибьюторов **открыты без proxy** (мы и так в RU маршруте):

| Дистрибьютор | URL | Что есть |
|---|---|---|
| **Lacopa** | lacopa.group | analytical + genomics + biotech, sitemap.xml |
| **Millab** | millab.ru + analitika.millab.ru | premium-каталог, фильтр по producer |
| **IMC Systems** | imc-systems.ru | хроматография |
| **Element-msc** | element-msc.ru | генеральный дистрибьютор Shimadzu в РФ |
| **Хеликон** | shop.helicon.ru | NGS — MGI / Сесана / Геноскан + расходники |

**Подход:** `GenericVendorAdapter` с правильными `entry_urls` + `category_keyword_map`. ~1 час на adapter, ~5 часов на все.

**Результат:** обогатить **Agilent stubs** реальными specs/datasheets через **их же артикулы** на стороне русских дистрибьюторов. Это даёт:
- русское описание прибора
- актуальную цену (РРЦ)
- комплектацию для РФ (с РУ если есть)

#### Уровень 3 — SelectScience (опц., приоритет HANDOFF #3)
- `selectscience.net` — открыт без proxy, имеет independent reviews
- Cross-validation specs из источника не-производителя
- Реальный user feedback

### 2.3. Strategy: NGS-вендоры (0 в БД)

Это **полный новый кластер**. План:

#### NGS платформы (instrument-уровень)

| Бренд | Сайт | Сложность |
|---|---|---|
| **Illumina** | illumina.com | TBD — проверить, доступно ли |
| **MGI Tech** | mgi-tech.com | открыт |
| **Genemind** | genemind.com | открыт |
| **Oxford Nanopore** | nanoporetech.com | открыт |
| **PacBio** | pacb.com | открыт |
| **Element Biosciences** | elementbiosciences.com | открыт |
| **Singular Genomics** | singulargenomics.com | открыт |
| **Ultima Genomics** | ultimagenomics.com | открыт |
| **Thermo Ion Torrent** | thermofisher.com → ion-torrent | через ThermoFisher adapter |
| **Salus / Биофьюжн** (RU) | salus-bio.ru | открыт |
| **Сесана** (RU) | sesana.ru | открыт |
| **Хеликон** (RU, OEM MGI) | shop.helicon.ru | открыт |

#### NGS реагенты и панели

| Бренд | Сайт | Категория |
|---|---|---|
| **IDT** | idtdna.com | xGen panels, oligos |
| **Twist Biosciences** | twistbioscience.com | Exome, Custom panels |
| **Roche KAPA** | sequencing.roche.com | HyperPrep, HyperCap |
| **AmoyDx** | amoydiagnostics.com | онкопанели NGS |
| **Burning Rock** | brbiotech.com | OncoScreen Plus, OverC MCD |
| **Pillar Biosciences** | pillar-biosciences.com | oncoReveal CDx |
| **Parseq** (RU) | parseq.pro | OncoScope, ReadyU-Panel |
| **OncoAtlas** (RU) | oncoatlas.com | NGS диагностика |
| **Nanodigm** (RU) | nanodigm.ru / -.com | CTC + NGS-prep |
| **Novogene** | novogene.com | WES/WGS reagents + услуги |
| **Vazyme** | vazyme.com | VAHTS / Hieff library prep |
| **TestGen** (RU) | testgen.ru | онкопанели |

**Реализация:** 2 спринта по ~5 дней.
- **Спринт 1**: adapter'ы для 7 NGS-instrument-вендоров (включая 3 RU)
- **Спринт 2**: adapter'ы для 12 reagent/panel-вендоров

Каждый adapter — GenericVendorAdapter с YAML-конфигом + override методов где нужен Playwright.

### 2.4. Monthly crawler для обновлений

**Назначение:** ежемесячно проверять обновления у производителей и подкачивать новые брошюры.

**Архитектура:**

```python
# infra/gluvex_tender_machine/stack/catalog-crawler/src/catalog_crawler/
#   monthly_refresh.py

@cron("0 3 1 * *")  # 1-го числа каждого месяца в 03:00 МСК
async def monthly_refresh():
    for vendor in get_active_vendors():
        # 1. List products of this vendor in DB
        existing = db.fetch_products(vendor_slug=vendor.slug)
        # 2. Crawl vendor (idempotent — same as initial)
        new_data = run_vendor_adapter(vendor.slug)
        # 3. Diff:
        #    - changed datasheets (content_hash diff) → re-download
        #    - new products → insert
        #    - missing products → mark status='discontinued'
        diff = compute_diff(existing, new_data)
        # 4. Insert audit_event(s)
        # 5. Send digest email "M new products, N updated datasheets, K discontinued"
        save_refresh_log(vendor.slug, diff)
```

**Триггер:** ARQ cron-задача в catalog-crawler контейнере. Запуск ночью чтобы не мешать обычной работе.

**Артефакты:**
- Новый bucket `product-brochures-archive/<vendor>/<retrieved_at>/` — версии файлов
- Telegram-нотификация менеджеру: "Memmert обновил 3 datasheet'а на ICOmed серию"

**Реализация:** 2-3 дня после того как все adapters готовы.

### 2.5. Текущий приоритет работ по Layer 1

| # | Задача | Усилия | Impact |
|---|---|---|---|
| 1 | Lacopa adapter (Agilent enrichment) | 1ч | КРИТИЧНО |
| 2 | Millab + analitika.millab.ru adapter | 1.5ч | КРИТИЧНО |
| 3 | IMC Systems adapter | 1ч | важно |
| 4 | Element-msc adapter (Shimadzu cross-check) | 1ч | важно |
| 5 | Хеликон adapter (MGI/Сесана NGS) | 2ч | КРИТИЧНО (NGS) |
| 6 | MGI Tech adapter | 2ч | КРИТИЧНО (NGS) |
| 7 | Genemind / Сесана adapter | 2ч | КРИТИЧНО (NGS) |
| 8 | Oxford Nanopore + PacBio adapters | 3ч | важно |
| 9 | NGS reagents (AmoyDx, Pillar, Burning Rock, Parseq, OncoAtlas, Nanodigm, Novogene, Vazyme) | 8ч | важно |
| 10 | Monthly refresh cron | 3ч | средне |
| 11 | SelectScience cross-check | 2ч | низкий |
| 12 | Memmert PDF matching (linking) | 0.5ч | tactical |
|   | **Итого** | **~28 часов** | |

---

## 3. LAYER 2 — Structured specs (выжатые из PDF)

### 3.1. Что именно вытаскивать

**Per-category schema** — фиксированный набор полей которые важны для тендерного матчинга.

Примеры:

#### `incubator` / `drying_oven` / `climate_chamber`
```json
{
  "category": "incubator",
  "specs": {
    "internal_volume_l": {"value": 53, "unit": "L"},
    "temperature_range_c": {"min": 20, "max": 80, "unit": "°C"},
    "temperature_accuracy_c": {"value": 0.1, "unit": "°C"},
    "temperature_uniformity_c": {"value": 0.4, "unit": "°C", "spatial": "any-point"},
    "convection_type": "natural | forced",
    "co2_control": {"enabled": false, "range_pct": null},
    "humidity_control": {"enabled": false},
    "atmosphere_control": false,
    "interior_material": "stainless_steel",
    "shelves_max": 6,
    "door_type": "single | double",
    "outer_dimensions_mm": {"w": 585, "d": 640, "h": 814},
    "weight_kg": 50,
    "power_w": 1400,
    "voltage_v": 230,
    "frequency_hz": 50,
    "compliance": ["DIN12880", "EN61010-1"]
  }
}
```

#### `hplc_system`
```json
{
  "category": "hplc_system",
  "specs": {
    "modular": true,
    "max_pressure_bar": 1300,
    "flow_rate_range_ml_min": {"min": 0.001, "max": 5.0},
    "default_components": ["pump", "autosampler", "column_oven"],
    "available_detectors": ["UV-VIS", "DAD", "FLD", "RID", "ELSD", "CAD", "MS"],
    "max_columns": 3,
    "injection_volume_ul": {"min": 0.1, "max": 1500},
    "control_software": "OpenLab CDS | ChemStation | MassHunter"
  }
}
```

#### `sequencer_platform`
```json
{
  "category": "sequencer_platform",
  "specs": {
    "technology": "SBS | DNB | nanopore | SMRT",
    "read_lengths_supported": ["2x150 PE", "2x300 PE"],
    "max_output_gb_per_run": 6000,
    "max_reads_million_per_run": 20000,
    "compatible_flowcells": ["S2", "S4", "SP"],
    "compatible_reagent_kits": ["v1.5 300", "v1.5 500"],
    "q30_pct_typical": 90,
    "footprint_mm": {"w": 850, "d": 800, "h": 1000},
    "weight_kg": 250,
    "applications": ["WGS", "WES", "RNA-seq", "targeted", "NIPT"]
  }
}
```

### 3.2. Pipeline вытаскивания specs

```
PDF in MinIO
    ↓
Text extraction (pdfplumber/Marker/Unstructured)
    ↓
Table detection (Camelot / Tabula / LLM-vision)
    ↓
LLM extraction (Claude Haiku/Sonnet) с per-category prompt
    ↓
Schema validation (pydantic per category)
    ↓
INSERT into product.base_specs (JSONB)
    ↓
Audit event: spec_extracted_from_pdf
```

**Хранение в БД:**

```sql
-- specs живут в существующей колонке product.base_specs (уже есть)
ALTER TABLE product ADD COLUMN IF NOT EXISTS specs_status TEXT
  DEFAULT 'empty';
-- 'empty' | 'auto_extracted' | 'manual_reviewed' | 'manual_edited'
-- 'auto_extracted' — есть, но не проверено менеджером
-- 'manual_reviewed' — менеджер просмотрел, всё ок
-- 'manual_edited' — менеджер вручную исправил → не перезаписывать crawler'ом

ALTER TABLE product ADD COLUMN IF NOT EXISTS specs_extracted_at TIMESTAMPTZ;
ALTER TABLE product ADD COLUMN IF NOT EXISTS specs_source_files TEXT[];  -- какие PDFы участвовали
ALTER TABLE product ADD COLUMN IF NOT EXISTS specs_extraction_model TEXT;  -- 'claude-haiku-20251022' и т.п.
ALTER TABLE product ADD COLUMN IF NOT EXISTS specs_extraction_confidence NUMERIC(3,2);
```

### 3.3. LLM-prompt template

```
Ты эксперт-консультант по лабораторному оборудованию. Извлеки технические
характеристики прибора {brand} {model} (категория: {category}) из текста брошюры.

ВЕРНИ строго JSON соответствующий схеме:
{schema_for_category}

ПРАВИЛА:
1. Если параметр не указан в брошюре — оставь null. Не выдумывай.
2. Числа с единицами — оставь единицу в поле _unit.
3. Диапазоны — {min, max}, точные значения — {value}.
4. Если есть допуск ±0.1 °C — это temperature_accuracy_c, НЕ uniformity.
5. Не путай «температурный диапазон от RT+5» (relative) с абсолютным.
6. Source citation: для каждого поля укажи `_source_quote` — 30-50 символов
   фрагмент брошюры где найден этот параметр.

ТЕКСТ БРОШЮРЫ:
{pdf_text_chunks}
```

### 3.4. Manual review workflow

Поскольку LLM может ошибаться:

1. После `auto_extracted` → отображать в **Twenty CRM** custom view "Specs Review"
2. Менеджер сравнивает с PDF (открывается рядом)
3. Утверждает / правит / отклоняет
4. После approval `specs_status='manual_reviewed'` — больше не перезаписывается

### 3.5. Sequencer-специфика — `sequencer_runtime_metric`

Для NGS платформ важно **декартово произведение** (platform × flowcell × reagent kit × read mode) → реальные метрики (output, reads, runtime, $/Gb).

Эта таблица уже спроектирована в `catalog-architecture.md` раздел 3.5. После extractor'а можно:
1. Парсить таблицу "Run modes" из брошюры NovaSeq
2. Каждая строка → row в `sequencer_runtime_metric`

### 3.6. Приоритет работ по Layer 2

| # | Задача | Усилия |
|---|---|---|
| 1 | Per-category schemas (pydantic models, ~15 категорий) | 2 дня |
| 2 | PDF text extraction pipeline | 1 день |
| 3 | LLM extraction service (vs LiteLLM) | 2 дня |
| 4 | Schema validation + write to DB | 1 день |
| 5 | Twenty CRM custom view "Specs Review" | 2 дня |
| 6 | First run на Memmert/Buchi/IKA (где есть 100% datasheets) | 1 день |
| 7 | Sequencer runtime metric extractor (после NGS adapters) | 2 дня |
|   | **Итого** | **~11 дней** |

---

## 4. LAYER 3 — Тендерные ТЗ + RAG

### 4.1. Часть A: наши готовые ТЗ-шаблоны

**Сценарий:** есть тендер на «термостат для культур клеток». Мы знаем что подходит **Memmert ICO150**, у нас есть **готовый раздел ТЗ** который мы вписываем в заявку. Эту библиотеку шаблонов нужно загрузить.

**Schema (новая таблица):**

```sql
CREATE TABLE tender_tz_template (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  -- Что это за шаблон
  template_name         TEXT NOT NULL,            -- 'Memmert ICO150 — стандартное ТЗ для НИИ'
  primary_product_id    UUID REFERENCES product(id),
  alternate_products    UUID[],                   -- альтернативные совместимые приборы
  category              product_category_t,

  -- Контент ТЗ
  tz_full_text          TEXT NOT NULL,            -- наш готовый раздел "Описание объекта закупки"
  tz_structured_specs   JSONB,                    -- те же specs что в Layer 2 — параметры из ТЗ
  variant_blocks        JSONB,                    -- для разных конфигураций ("базовая | с CO2 | расширенная")

  -- Метаданные
  source_file_path      TEXT,                     -- MinIO путь к исходному ТЗ
  used_in_tenders       INTEGER[],                -- список tender_id где этот шаблон использовался
  win_rate_pct          NUMERIC(5,2),             -- % выигранных тендеров с этим шаблоном

  imported_at           TIMESTAMPTZ,
  imported_from         TEXT,                     -- 'manual_upload' | 'historical_tender'
  reviewed_by           TEXT,                     -- менеджер кто валидировал
  is_active             BOOLEAN DEFAULT true,

  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tz_template_category    ON tender_tz_template(category);
CREATE INDEX idx_tz_template_product     ON tender_tz_template(primary_product_id);
CREATE INDEX idx_tz_template_specs_gin   ON tender_tz_template USING GIN (tz_structured_specs);
```

**Workflow загрузки:**

1. Загружаю DOCX наших готовых ТЗ в MinIO bucket `tender-templates/`
2. Скрипт `tender_template_importer.py`:
   - распаковывает DOCX → текст + таблицы
   - LLM извлекает structured specs (тот же extractor что в Layer 2)
   - привязывает к product_id (по brand+model в таблице или по similarity)
3. Менеджер ревьюит в Twenty CRM
4. После approval `is_active=true`

### 4.2. Часть B: входящие тендерные ТЗ (из tender_pipeline)

Это **то что делает analyzer/** (см. `tenderland_bot/src/tenderland_bot/analyzer/`).

Текущий статус (✅ сделано):
- `unpacker.py` — распаковка zip + nested zips + CP866
- `classifier.py` — классификация файлов tender package (TZ / contract / price_calc / ...)
- `extractor.py` — DOCX extraction со 3 стратегиями (КТРУ-таблица / kv / параграфы)
- `manifest.py` — JSON-манифест per tender

**Не сделано (см. `analyzer/runner.py`, `matcher.py`, `decision.py`):**

#### `value_parser.py` — нормализация значений
```python
# Вход: "≥ 80" / "≥ 5 и ≤ 60" / "±0,4" / "Наличие" / "≤ 1.5"
# Выход:
#   ">= 80"  → {"op": ">=", "value": 80}
#   "≥5 ≤60" → {"min": 5, "max": 60}
#   "±0,4"   → {"tolerance": 0.4}
#   "Наличие"→ {"presence": True}
```

#### `pdf_extractor.py` — для PDF-копий ТЗ
- pdfplumber для текстовых PDF
- pytesseract / Marker для сканов с OCR

#### `html_extractor.py` — для извещений (.html файлов из zip)
- ФЗ-44 печатные формы — структурированный HTML
- Из section "Описание объекта закупки" вытащить таблицу характеристик

#### `doc_extractor.py` — для старых .doc (Word 97-2003)
- LibreOffice headless: `libreoffice --headless --convert-to docx input.doc`
- После — обычный python-docx

### 4.3. `matcher.py` — extracted_specs ↔ product catalogue

```python
@dataclass
class MatchCandidate:
    product_id: UUID
    score: float                   # 0..100
    matched_specs: list[dict]      # совпавшие параметры
    failed_specs: list[dict]       # не прошли по конкретному параметру (КРИТИЧНО)
    missing_in_catalog: list[str]  # параметры тендера, нет данных в каталоге
    reasoning: str

def match_tender_to_catalog(
    extracted_specs: list[ExtractedSpec],
    okpd2_code: str | None,
    product_name_hint: str,
) -> list[MatchCandidate]:
    # 1. Сужение кандидатов:
    #    a. По ОКПД2 (если есть в ТЗ)
    #    b. По category (через ОКПД2 → product_category_t mapping)
    #    c. По brand-hint (через synonyms в product_name)
    # 2. Для каждого кандидата:
    #    - Парсим specs тендера в normalized form (через value_parser)
    #    - Сверяем с product.base_specs / product_configuration.specs
    #    - Считаем score (% совпавших обязательных параметров)
    # 3. Sort by score desc, top-5
```

**Стратегии матчинга по типу параметра:**

| Тип в ТЗ | Тип в catalog | Логика сравнения |
|---|---|---|
| `≥ 80 (количеств.)` | `value: 100` | OK если catalog >= 80 |
| `≥ 5 и ≤ 60` (диапазон) | `range: {min: 30, max: 200}` | OK если range tender ⊇ или ⊆? (зависит от типа) |
| `±0,4` (допуск) | `value: 0.3` | OK если catalog <= ±0.4 (строже) |
| `Наличие` (качеств.) | `presence: true` | OK если catalog has feature |
| `Тип характеристики` | `not required` | если "Значение не может изменяться" — STRICT MATCH |
| Числовое | NULL в catalog | partial (warn — missing data) |

### 4.4. `decision.py` — pass / review / fail

```python
DECISION_RULES = {
    'pass': {
        'min_score': 80,
        'no_critical_fails': True,
        'description': 'Берём в работу',
    },
    'review': {
        'min_score': 60,
        'allow_some_partial': True,
        'description': 'Менеджеру решить — есть нюансы',
    },
    'fail': {
        'description': 'Не подходит — описание объекта закупки требует параметров, которых у нашего ассортимента нет',
    },
}
```

### 4.5. `runner.py` — orchestrator

```python
def analyze_tender(tender_id: str, archive_path: Path):
    # 1. Unpack
    unpack = unpack_tender_archive(archive_path, output_root)
    # 2. Classify
    classified = classify_files(unpack.primary_files())
    # 3. Extract from each TZ-like file
    extracted_specs = []
    for f in classified.get(FileCategory.TZ, []):
        if f.path.suffix == '.docx':
            extracted_specs.extend(extract_from_docx(f.path).specs)
        elif f.path.suffix == '.pdf':
            extracted_specs.extend(extract_from_pdf(f.path).specs)
        elif f.path.suffix in ('.doc', '.rtf'):
            converted = libreoffice_to_docx(f.path)
            extracted_specs.extend(extract_from_docx(converted).specs)
    # 4. Match against catalog
    candidates = match_tender_to_catalog(
        extracted_specs,
        okpd2_code=manifest.ktru_okpd2_code,
        product_name_hint=manifest.product_name,
    )
    # 5. Decide
    decision = decide(candidates)
    # 6. Persist
    save_tender_analysis(tender_id, extracted_specs, candidates, decision)
    # 7. If pass/review — push to CRM agent (Agent 3)
    if decision in ('pass', 'review'):
        queue.put(push_to_crm(tender_id))
```

### 4.6. RAG для семантического матчинга

Для случаев когда extracted specs не дают чёткой картины (текстовое ТЗ без таблицы):

1. **Vectorize** наши `tender_tz_template.tz_full_text` → Qdrant collection `tender_templates_v1`
2. На входящий тендер → vectorize его `tz_full_text` → top-k similar templates → suggest those products
3. Combine with structured matcher results

**Qdrant collection schema:**
```python
{
    "collection_name": "tender_templates_v1",
    "vector_size": 1024,  # voyage-2 / nomic / mxbai-large
    "metadata": {
        "template_id": UUID,
        "primary_product_id": UUID,
        "category": str,
        "win_rate": float,
    }
}
```

### 4.7. Приоритет работ по Layer 3

| # | Задача | Усилия | Зависимость |
|---|---|---|---|
| 1 | `value_parser.py` — операторы | 1 день | — |
| 2 | `pdf_extractor.py` (pdfplumber) | 1 день | — |
| 3 | `html_extractor.py` (для извещений ФЗ-44) | 1 день | — |
| 4 | `doc_extractor.py` (LibreOffice convert) | 0.5 день | — |
| 5 | `matcher.py` — structural matching | 2 дня | Layer 2 specs готовы |
| 6 | `decision.py` + правила | 0.5 день | matcher |
| 7 | `runner.py` orchestrator | 1 день | всё выше |
| 8 | `tender_tz_template` schema + migration | 0.5 день | — |
| 9 | Importer наших ТЗ из DOCX | 1 день | schema |
| 10 | RAG: Qdrant + embeddings | 2 дня | templates загружены |
| 11 | Twenty CRM custom Lead view | 2 дня | — |
| 12 | KP-генератор по template'у | 3 дня | tender_tz_template |
|    | **Итого** | **~15 дней** | |

---

## 5. Связь со схемой агентов (Tender Pipeline)

```
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT 1 — SEARCHER                                                 │
│  Сейчас: ручное создание автопоисков в UI + Export/Create CLI       │
│  Будущее (когда Tenderland даст UpdateAutosearch API): автосинк MD  │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT 2 — ANALYZER  (LAYER 3 Part B)                               │
│  ✅ unpacker + classifier + extractor (DOCX-КТРУ) готовы            │
│  🟡 value_parser + pdf/html/doc extractors — todo                   │
│  🟡 matcher + decision + runner — todo                              │
│  🟡 RAG для семантики — todo                                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓ pass/review
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT 3 — CRM PUSHER                                               │
│  Создаёт Lead в Twenty + Company по ИНН (если новая)                │
│  Прикладывает: tender_analyses.json + matched_products + KP draft   │
└──────────────────────────┬──────────────────────────────────────────┘
                           ↓ если "Беру в работу"
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT 4 — KP GENERATOR  (LAYER 3 Part A — наши шаблоны)            │
│  Берёт tender_tz_template (наш ТЗ для конкретной модели)            │
│  + adapt'ит под конкретного заказчика                               │
│  + добавляет цены из 1С                                             │
│  → DOCX заявка                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Связь между слоями

```
LAYER 1 (raw)                       LAYER 2 (structured)              LAYER 3 (tender)
─────────────────                   ──────────────────                ────────────────
PDF "Memmert ICO150       extract   product.base_specs        match   tender_tz extracted
brochure.pdf"            ────────→  {volume: 150, CO2: 0-20%} ←─────  {volume: ≥80, CO2: ≥18%}
       ↓                                     ↓                                ↓
  document_chunks               sequencer_runtime_metric           tender_match_result
       ↓                                                                      ↓
   Qdrant vectors                                                  CRM Lead + KP draft
                                                                              ↑
                                                                              │
                                                          LAYER 3 Part A:
                                                       tender_tz_template
                                                        (наши готовые ТЗ)
                                                              ↑
                                                  загружаем DOCX образцы
```

Главный принцип: **продукт = id в каталоге, всё остальное (брошюра, specs, наш ТЗ-шаблон, тендерное матчинг) — крепится к этому id**.

---

## 7. Дорожная карта

### Фаза A — Заполнение каталога (2-3 недели работы, ~28ч факт)

Параллельные потоки:
- A1: Русские дистрибьюторы (Lacopa → Millab → IMC → Element-msc) — обогащают Agilent + Shimadzu
- A2: NGS instruments (Хеликон → MGI → Genemind → ONT → PacBio) — новый кластер
- A3: NGS reagents/panels (12 brands)
- A4: Memmert PDF matching + остальные tactical fixes

Результат: **~50-70K продуктов с datasheets, покрытие 95%+ нашего ассортимента**.

### Фаза B — Layer 2 extraction (2 недели, ~11д)

- Per-category schemas (15 категорий)
- LLM extraction pipeline
- First batch: Memmert + Sartorius + IKA (где 100% datasheets)
- Twenty review view

Результат: **~5,000 продуктов с structured specs, manager-reviewed**.

### Фаза C — Tender Pipeline analyzer (2-3 недели, ~15д)

- value_parser + остальные extractor'ы
- matcher + decision + runner
- наши ТЗ-шаблоны (schema + importer)
- RAG для семантики
- Twenty Lead view + KP-генератор

Результат: **полностью автоматический pipeline** тендер → анализ → решение → лид в CRM с KP-черновиком.

### Фаза D — Operations (постоянно)

- Monthly crawler для refresh
- Spec review queue в Twenty (manager work)
- KP feedback loop (улучшение шаблонов на основе win/loss)

---

## 8. Открытые вопросы

1. **Agilent enrichment через distributors** — если у Lacopa/Millab нет конкретной модели, нужен fallback (manual entry)
2. **NGS reagent-vendor blocking** — у нескольких сайт может требовать регистрацию (AmoyDx, Burning Rock — китайские, специфичный UX)
3. **LLM cost для extraction** — 50K продуктов × ~5K tokens = ~250M tokens. Через LiteLLM Haiku — ~$100. Терпимо
4. **Spec schema эволюция** — добавление новой категории требует prompt + pydantic update. Нужен migration plan
5. **OCR качество для сканов** — для PDF-сканов тендеров tesseract может ошибаться; рассмотреть Marker / Unstructured (платно) если станет проблемой

---

## 9. Ссылки

- [`master-data-architecture.md`](master-data-architecture.md) — high-level контуры
- [`catalog-architecture.md`](catalog-architecture.md) — product/configuration/compatibility schema
- [`storage-architecture.md`](storage-architecture.md) — Postgres + MinIO + Qdrant
- [`system-state.md`](system-state.md) — operational state
- [`HANDOFF_NEXT_SESSION.md`](HANDOFF_NEXT_SESSION.md) — предыдущая сессия по catalog crawler
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — tender pipeline 3-agent design
