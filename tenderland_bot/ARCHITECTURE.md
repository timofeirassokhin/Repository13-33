# Tender Pipeline — архитектура

**Версия:** 1.0 (после решения перейти на полный API + двухагентную систему)
**Дата:** 2026-05-05
**Статус:** проектирование, утверждается у заказчика перед реализацией

> Этот документ — единственный источник истины по системе. Любой код пишется в соответствии с ним; любое изменение архитектуры начинается с правки этого документа.

---

## 1. Цель системы

Автоматизировать обработку тендеров на аналитическое и молекулярно-диагностическое оборудование от обнаружения до создания неквалифицированного лида в CRM, чтобы менеджер тратил время только на принятие решения, а не на ручной поиск, скачивание документации и сопоставление характеристик.

Система должна:

1. Каждое утро рабочего дня сама находить новые релевантные тендеры по 13 поисковым темам (8 аналитика + 5 молекулярка).
2. Скачивать всю документацию по каждому новому тендеру.
3. Понимать что именно требует заказчик — какой класс приборов, какие параметры, какая стартовая цена.
4. Сравнивать требования с нашим каталогом и принимать решение «проходим / не проходим / спорно».
5. По прошедшим и спорным — создавать в Twenty CRM компанию (если её ещё нет) и неквалифицированный лид с полным контекстом.
6. Менеджер в CRM решает «беру в работу / отказ».
7. По принятым в работу — отдельный агент в будущем сгенерирует файл заявки с нашими ТТХ и приложит к лиду.

Система должна быть **переносима на новый VPS** одной командой `docker compose up -d` + восстановление томов и `.env`.

---

## 2. Высокоуровневая схема

```
┌─────────────────────────────────────────────────────────────────────┐
│                       TENDER PIPELINE                                │
│                                                                       │
│  ┌──────────────┐                                                    │
│  │ keywords_*.md│ ◄── источник истины по ключам, в git              │
│  └──────┬───────┘                                                    │
│         │                                                             │
│         ▼                                                             │
│  ┌──────────────────────────────────────────────────────┐            │
│  │  AGENT 1: SEARCHER                                    │            │
│  │  • парсит keywords_*.md в JSON-фильтры               │            │
│  │  • дёргает Tenderland Search/Find по каждой теме     │            │
│  │  • дедуп по tender_id в Postgres                     │            │
│  │  • скачивает zip-архивы для новых                    │            │
│  │  • пишет в БД: tenders + search_runs                 │            │
│  │  • ставит задачи analyze_tender(id)                  │            │
│  └─────────────────────────┬────────────────────────────┘            │
│                            │                                          │
│                            ▼                                          │
│                   ┌────────────────┐                                  │
│                   │ Queue (Redis)  │                                  │
│                   └────────┬───────┘                                  │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────┐            │
│  │  AGENT 2: ANALYZER                                    │            │
│  │                                                       │            │
│  │  Module 1 (Classifier + Extractor):                  │            │
│  │  • распаковывает zip                                 │            │
│  │  • классифицирует файлы (ТЗ / договор / цена)        │            │
│  │  • парсит ТЗ → JSON {характеристика, значение, ед.}  │            │
│  │                                                       │            │
│  │  Module 2 (Matcher + Decision):                      │            │
│  │  • сравнивает с каталогом продукции                  │            │
│  │  • выбирает best match + score + объяснение          │            │
│  │  • правила решения: pass / review / fail             │            │
│  │                                                       │            │
│  │  • пишет: tender_analyses                            │            │
│  │  • ставит задачи push_to_crm(id)                     │            │
│  └─────────────────────────┬────────────────────────────┘            │
│                            │                                          │
│                            ▼                                          │
│  ┌──────────────────────────────────────────────────────┐            │
│  │  AGENT 3: CRM PUSHER                                  │            │
│  │  • ищет Company по ИНН в Twenty                      │            │
│  │  • если нет — создаёт                                 │            │
│  │  • создаёт Lead (статус: unqualified)                │            │
│  │  • привязывает к Company                             │            │
│  │  • пишет: crm_pushes                                  │            │
│  └─────────────────────────┬────────────────────────────┘            │
│                            │                                          │
│                            ▼                                          │
│                   ┌────────────────┐                                  │
│                   │  Twenty CRM    │ ◄── менеджер видит лиды           │
│                   └────────────────┘                                  │
│                                                                       │
│  ┌──────────────────────────────────────────────────────┐            │
│  │  FUTURE — AGENT 4: PROPOSAL GENERATOR                 │            │
│  │  По принятым в работу лидам → файл-заявка → в лид    │            │
│  └──────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

**Хранилища:**

- **Postgres** — состояние, дедуп, метаданные, результаты анализа.
- **Redis** — очередь задач для воркеров.
- **Локальная файловая система** (`/var/lib/tenders/`) — zip-архивы, распакованная документация, отчёты Excel/Markdown.
- **Twenty CRM** (внешняя система) — итоговые лиды.
- **`config/keywords_*.md` и `config/products/*.json`** в git — источники истины по ключам и каталогу.
- **`.env`** (gitignored) — секреты: `TENDERLAND_API_KEY`, `TWENTY_API_KEY`, `LITELLM_BASE_URL`, `POSTGRES_DSN`, `REDIS_URL`.

---

## 3. Технологический стек

| Слой                 | Выбор                                          | Обоснование                                                          |
|----------------------|-------------------------------------------------|----------------------------------------------------------------------|
| Язык                 | Python 3.12                                     | Уже есть `tenderland_bot`, экосистема для парсинга PDF/DOCX лучшая   |
| Asynchronous runtime | `asyncio` + `httpx`                             | API клиенты, конкурентные загрузки                                  |
| ORM / БД             | SQLAlchemy 2.x async + asyncpg → Postgres 16   | JSONB, индексы по ИНН, `tender_id`                                  |
| Очередь задач        | **ARQ** (Redis-based, async-native)             | Мелкая, понятная, дружит с asyncio. Альтернатива — Dramatiq         |
| Парсинг документов   | `pdfplumber`, `python-docx`, `openpyxl`, `pytesseract` (для сканов) | Стандарт                                                            |
| LLM                  | Anthropic SDK через **LiteLLM** (свой прокси)   | Уже есть в инфре content system 13-33. Модели: cheap=Haiku, creative=Sonnet, premium=Opus |
| HTTP API системы     | FastAPI + Uvicorn                               | Админка, мониторинг, ручные перезапуски конкретных тендеров         |
| CLI                  | `click` или `typer`                             | Уже используется в `tenderland_bot`                                 |
| Логирование          | `structlog` → JSON в файл + stdout              | Парсится Loki/любым агрегатором                                     |
| Контейнеризация      | Docker + docker-compose                         | Один файл — вся система                                             |
| Конфиги              | TOML для параметров + JSON для фильтров         | Парсится без зависимостей, человеко-читаемо                         |

---

## 4. Структура проекта

Текущий `tenderland_bot/` становится `searcher`-модулем внутри большего проекта. Имя верхнего уровня — **`gluvex_tender_machine`** (Python-пакет в snake_case, репозиторий и докер-образ — то же имя). На диске папка проекта тоже `gluvex_tender_machine/`.

```
gluvex_tender_machine/
├── ARCHITECTURE.md                  # ← этот документ
├── README.md                        # быстрый старт
├── pyproject.toml                   # зависимости
├── docker-compose.yml               # postgres + redis + api + worker
├── docker-compose.override.yml      # локальная разработка (gitignored)
├── .env.example                     # шаблон
├── .env                             # секреты (gitignored)
│
├── config/
│   ├── keywords_analytical.md       # источник истины: 8 поисков аналитики
│   ├── keywords_molecular.md        # источник истины: 5 поисков молекулярки
│   ├── searches/                    # сгенерённые из MD JSON-фильтры (gitignored — собираются)
│   │   ├── 01_LC_LCMS_GPC_Prep.json
│   │   ├── 02_GC_GCMS.json
│   │   └── ...
│   ├── products/                    # каталог нашей продукции
│   │   ├── analytical/
│   │   │   ├── memmert_un55.json
│   │   │   └── ...
│   │   └── molecular/
│   │       ├── illumina_miseq.json
│   │       └── ...
│   ├── decision_rules.toml          # пороги score, правила classification, EXCLUDE-логика
│   └── prompts/                     # системные промпты для LLM
│       ├── classifier.md
│       ├── extractor.md
│       └── matcher.md
│
├── src/
│   └── tender_pipeline/
│       ├── __init__.py
│       ├── __main__.py              # CLI entrypoint
│       ├── config.py                # pydantic-settings
│       ├── logger.py                # structlog setup
│       │
│       ├── searcher/                # AGENT 1 (бывший tenderland_bot)
│       │   ├── __init__.py
│       │   ├── md_parser.py         # keywords_*.md → JSON
│       │   ├── tenderland_client.py # обёртка над API (есть, расширим под Search/Find)
│       │   ├── runner.py            # запуск одного поиска
│       │   ├── orchestrator.py      # запуск всех поисков параллельно
│       │   ├── document_fetcher.py  # zip скачивание
│       │   └── exporter.py          # xlsx/md отчёт (есть)
│       │
│       ├── analyzer/                # AGENT 2
│       │   ├── __init__.py
│       │   ├── unpacker.py          # zip → /unpacked/<tender_id>/
│       │   ├── classifier.py        # Module 1 part 1: классификация файлов
│       │   ├── extractor.py         # Module 1 part 2: парсинг ТЗ
│       │   ├── matcher.py           # Module 2 part 1: сравнение с каталогом
│       │   ├── decision.py          # Module 2 part 2: pass/review/fail
│       │   └── runner.py            # связывает 4 шага
│       │
│       ├── crm/                     # AGENT 3
│       │   ├── __init__.py
│       │   ├── twenty_client.py
│       │   ├── company_resolver.py  # ИНН → Twenty Company ID (с дедупом)
│       │   └── lead_creator.py
│       │
│       ├── catalog/                 # каталог продукции
│       │   ├── __init__.py
│       │   ├── models.py            # pydantic-схема прибора
│       │   ├── loader.py            # JSON → Postgres
│       │   └── search.py            # быстрый поиск кандидатов (по brand/category/keywords)
│       │
│       ├── llm/                     # обёртка LLM
│       │   ├── __init__.py
│       │   ├── client.py            # httpx клиент к LiteLLM
│       │   ├── prompts.py           # загрузка из config/prompts/
│       │   └── cost_tracker.py      # учёт токенов и стоимости
│       │
│       ├── queue/                   # ARQ задачи
│       │   ├── __init__.py
│       │   ├── settings.py
│       │   └── tasks.py             # @arq_task analyze_tender, push_to_crm
│       │
│       ├── db/                      # схема, миграции, репозитории
│       │   ├── __init__.py
│       │   ├── models.py            # SQLAlchemy
│       │   ├── repositories.py      # async data access
│       │   └── migrations/          # alembic
│       │
│       ├── api/                     # FastAPI админка
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── routes/
│       │   │   ├── tenders.py
│       │   │   ├── searches.py
│       │   │   ├── analyses.py
│       │   │   └── crm.py
│       │   └── templates/           # минимальный HTML дашборд (опц.)
│       │
│       └── utils/
│           ├── retry.py             # backoff/retry для API
│           └── slugify.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/                    # сэмплы Tenderland JSON, тестовые ТЗ
│
└── scripts/
    ├── bootstrap.sh                 # первичная настройка
    ├── migrate.sh                   # alembic upgrade head
    └── seed_catalog.py              # заливка products/*.json в БД
```

Текущая папка `D:\-=ClaudeCode=-\tenderland_bot\` после стабилизации Этапа 1 переезжает в `D:\-=ClaudeCode=-\gluvex_tender_machine\` (через `git mv`, история сохраняется). До этого момента всё новое складываем в `tenderland_bot/` чтобы не плодить полу-готовых веток.

```text
```

---

## 5. Модель данных (Postgres)

### 5.1. `tenders` — все увиденные тендеры

```sql
CREATE TABLE tenders (
  tender_id        TEXT PRIMARY KEY,        -- TL2530033598
  reg_number       TEXT NOT NULL,
  name             TEXT NOT NULL,
  begin_price      NUMERIC(20, 2),
  customer_name    TEXT,
  customer_full_name TEXT,
  customer_inn     TEXT,
  customer_ogrn    TEXT,
  customer_kpp     TEXT,
  customer_contacts TEXT,
  publish_date     TIMESTAMPTZ NOT NULL,
  end_date         TIMESTAMPTZ,
  region           TEXT,
  type_name        TEXT,                    -- 44-ФЗ / 223-ФЗ / коммерческий / СНГ
  categories       TEXT[],
  etp_link         TEXT,
  files_url        TEXT,                    -- ссылка Tenderland на zip
  local_zip_path   TEXT,                    -- /var/lib/tenders/<topic>/<DDMMYY>/file.zip
  unpacked_dir     TEXT,                    -- /var/lib/tenders/unpacked/<tender_id>/

  -- Происхождение
  search_topic     TEXT NOT NULL,           -- 01_LC_LCMS_GPC_Prep | MDX_01_Sequencers | ...
  search_domain    TEXT NOT NULL,           -- analytical | molecular_diagnostics
  search_run_id    INTEGER REFERENCES search_runs(id),

  -- Сырой ответ Tenderland (для отладки и редких полей)
  raw_json         JSONB,

  -- Жизненный цикл
  status           TEXT NOT NULL DEFAULT 'new',
                   -- new | files_downloaded | analyzing | analyzed | crm_pushed | rejected | error
  first_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenders_status ON tenders(status);
CREATE INDEX idx_tenders_inn ON tenders(customer_inn);
CREATE INDEX idx_tenders_topic ON tenders(search_topic);
CREATE INDEX idx_tenders_first_seen ON tenders(first_seen_at DESC);
```

### 5.2. `search_runs` — каждый запуск Searcher по теме

```sql
CREATE TABLE search_runs (
  id               SERIAL PRIMARY KEY,
  topic            TEXT NOT NULL,
  domain           TEXT NOT NULL,
  started_at       TIMESTAMPTZ NOT NULL,
  finished_at      TIMESTAMPTZ,
  total_found      INTEGER,
  new_count        INTEGER,
  duplicate_count  INTEGER,
  errors           JSONB,
  api_units_used   INTEGER                  -- если есть лимиты
);
```

### 5.3. `tender_analyses` — результаты Analyzer

```sql
CREATE TABLE tender_analyses (
  id                  SERIAL PRIMARY KEY,
  tender_id           TEXT NOT NULL REFERENCES tenders(tender_id) ON DELETE CASCADE,

  -- Module 1
  classified_files    JSONB,                -- {"tz":[...], "price":[...], "contract":[...], "unknown":[...]}
  extracted_specs     JSONB,                -- [{"name":"температурный диапазон","value_min":30,"value_max":300,"unit":"°C","required":true}, ...]

  -- Module 2
  matched_products    JSONB,                -- [{"product_id":"memmert-un55","score":87,"reasoning":"...","fails_on":[]}, ...]
  best_match_id       TEXT,
  best_match_score    NUMERIC(5, 2),
  decision            TEXT,                 -- pass | review | fail
  decision_reason     TEXT,

  -- Учёт
  llm_costs           JSONB,                -- {"haiku":{"in":1234,"out":567,"usd":0.012}, ...}
  analyzed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  status              TEXT NOT NULL,        -- pending | extracting | matching | done | error
  error_message       TEXT
);

CREATE UNIQUE INDEX idx_analyses_tender ON tender_analyses(tender_id);
```

### 5.4. `crm_pushes` — отправки в Twenty

```sql
CREATE TABLE crm_pushes (
  id                  SERIAL PRIMARY KEY,
  tender_id           TEXT NOT NULL REFERENCES tenders(tender_id),
  twenty_company_id   TEXT,
  twenty_lead_id      TEXT,
  is_new_company      BOOLEAN,
  pushed_at           TIMESTAMPTZ DEFAULT now(),
  status              TEXT NOT NULL,        -- pending | success | failed
  error_message       TEXT
);
```

### 5.5. `companies_seen` — кэш компаний по ИНН

```sql
CREATE TABLE companies_seen (
  inn                  TEXT PRIMARY KEY,
  ogrn                 TEXT,
  twenty_company_id    TEXT NOT NULL,
  full_name            TEXT,
  short_name           TEXT,
  first_seen_at        TIMESTAMPTZ DEFAULT now(),
  last_tender_id       TEXT,
  total_tenders_count  INTEGER DEFAULT 0
);
```

### 5.6. `products` — каталог нашей продукции

```sql
CREATE TABLE products (
  id                SERIAL PRIMARY KEY,
  product_code      TEXT UNIQUE NOT NULL,
  brand             TEXT NOT NULL,
  model             TEXT NOT NULL,
  category          TEXT NOT NULL,          -- hplc | gc | icp_oes | aas | sequencer_ngs | ...
  domain            TEXT NOT NULL,          -- analytical | molecular_diagnostics
  specs             JSONB NOT NULL,
  consumables_for   INTEGER[],              -- ID родительских приборов
  datasheet_paths   TEXT[],
  is_active         BOOLEAN DEFAULT true,
  imported_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_domain ON products(domain);
```

---

## 6. Агент 1 — SEARCHER

### 6.1. Контракт

**Вход:**
- `config/keywords_*.md` файлы
- API-ключ Tenderland (`Search/Find` модуль активен)
- БД (для дедупа)

**Выход:**
- Записи `tenders` со `status='files_downloaded'` или `status='new'`
- Запись `search_runs`
- ZIP-архивы в `/var/lib/tenders/<topic>/<DDMMYY>/`
- Поставленные задачи `analyze_tender(tender_id)` в очереди
- Excel/Markdown отчёт в `/var/lib/tenders/<topic>/<topic>_<DDMMYY>.{xlsx,md}` (для ручного просмотра)

### 6.2. Парсер MD → JSON

В `keywords_*.md` есть готовые INCLUDE/EXCLUDE строки. Парсер `md_parser.py`:

1. Находит секции вида `### 5.1. \`<topic>\` — <description>`
2. Извлекает следующий за секцией fenced code block с `text` — это INCLUDE-строка
3. Аналогично EXCLUDE-секции
4. Формирует JSON для `Search/Find`:

```json
{
  "topic": "01_LC_LCMS_GPC_Prep",
  "domain": "analytical",
  "fields": [
    "tender_regNumber", "tender_name", "tender_beginPrice",
    "tender_lotCustomerShortName", "tender_lotCustomerInn", "tender_lotCustomerOgrn",
    "tender_publishDate", "tender_endDate", "tender_region",
    "tender_typeName", "tender_lotCategories",
    "tender_files", "tender_etpLink", "tender_fileCount"
  ],
  "filters": {
    "and": [
      {"id": 136, "name": "tender_keywords_include", "type": "text", "include": "<строка из MD>"},
      {"id": 137, "name": "tender_keywords_exclude", "type": "text", "include": "<EXCLUDE строка>"},
      {"id": 110, "name": "tender_publishDate", "type": "range", "from": "<today-7>", "to": null},
      {"id": 111, "name": "tender_endDate", "type": "range", "from": "<today>", "to": null}
    ]
  },
  "interval": [0, 1],
  "pageSize": 100,
  "skip": 0,
  "orderBy": "tender_sysPublishDate.desc"
}
```

ID фильтров `110` для `tender_publishDate` и `111` для `tender_endDate` — **(Q2: проверить через `GetFilterList`)**, но 136/137 для keywords уже подтверждены.

Сгенерённые JSON-ы кэшируются в `config/searches/<topic>.json` (gitignored, но воспроизводимы).

### 6.3. Алгоритм одного запуска (один topic)

```python
async def run_search(topic: str) -> SearchResult:
    1. Загрузить JSON фильтр для topic.
    2. Подставить актуальные даты.
    3. POST /Api/v1/Search/Find → получить sessionId, totalCount, items.
    4. Если pageSize=100, items=100 — пройти по страницам через skip += 100, max 100 страниц.
    5. Для каждого tender в items:
       a. Проверить tender_id в processed_tenders → если есть, skip.
       b. Парсить fields → создать запись tenders со status='new'.
       c. Скачать zip через GetEntityFileList + File/Get (или GetAll одним архивом):
          - GetAll одним архивом проще, но единицы лимита считаются по числу файлов внутри.
          - GetEntityFileList + по файлу даёт контроль (можно качать только PDF/DOCX/XLSX, скипать html/xml).
          - **Решение:** GetAll одним архивом для простоты на старте, оптимизация позже.
       d. Сохранить в /var/lib/tenders/<topic>/<DDMMYY>/<filename>.zip
       e. Обновить tender со status='files_downloaded' и local_zip_path.
       f. Поставить задачу analyze_tender(tender_id) в очередь.
    6. Записать search_runs с метриками.
    7. Сгенерировать Excel/MD отчёт за день (текущая логика exporter.py).
```

### 6.4. Параллельность

Все 13 поисков (8 + 5) запускаются параллельно через `asyncio.gather`. Tenderland API спокойно держит ~10 одновременных запросов. **(Q3: проверить с менеджером)**

### 6.5. Расписание

- Searcher запускается через ARQ cron-задачу: `0 7 * * 1-5` (07:00 МСК, рабочие дни).
- Анализатор стартует параллельно по мере появления задач — не ждём окончания всех поисков.
- К 09:00 ожидается готовность лидов в CRM.

---

## 7. Агент 2 — ANALYZER

Двухмодульный, как ты описал.

### 7.1. Module 1 — Classifier + Extractor

**Шаг 1.1. Распаковка zip**

`/var/lib/tenders/unpacked/<tender_id>/` — все файлы из архива. Если внутри вложенные архивы (`.rar`, `.7z`, ещё zip) — рекурсивно распаковать.

**Шаг 1.2. Классификация файлов**

Каждый файл классифицируется по типу:

| Тип            | Что это                                              | Эвристика                                                       |
|----------------|------------------------------------------------------|-----------------------------------------------------------------|
| `tz`           | Техническое задание / описание объекта закупки      | Имя содержит «Описание», «Техническое задание», «ТЗ», размер ≥ 10 КБ, формат DOCX/PDF/XLSX |
| `notification` | Извещение                                            | Имя содержит «Извещение», «Печатная форма извещения»           |
| `price_calc`   | Расчёт НМЦК                                          | Имя содержит «Расчёт», «НМЦК», «обоснование цены»              |
| `contract`     | Проект контракта                                     | Имя содержит «Контракт», «Договор»                              |
| `application`  | Форма заявки                                         | Имя содержит «Заявка», «Форма»                                  |
| `unknown`      | Не определено эвристикой                             | Если несколько `unknown` — отдаём LLM (Haiku) для классификации по содержимому |

LLM-классификатор (только для `unknown`): отправляем первые 1500 символов файла + его имя → возвращает категорию из списка. Промпт в `config/prompts/classifier.md`.

**Шаг 1.3. Извлечение характеристик из ТЗ**

Для каждого файла категории `tz`:

1. Извлечь сырой текст:
   - DOCX → `python-docx`, проходим по таблицам и параграфам
   - XLSX → `openpyxl`, читаем все листы, склеиваем как «<имя_листа>: <ячейки>»
   - PDF с текстовым слоем → `pdfplumber`
   - PDF-скан (если pdfplumber вернул < 200 символов на страницу) → `pytesseract` с языком `rus+eng`
2. Прогнать через LLM (Sonnet/`creative`):
   - Промпт в `config/prompts/extractor.md`
   - Задача: вернуть структурированный JSON `[{"name": "...", "value": "...", "unit": "...", "value_min": null, "value_max": null, "required": true}]`
   - Поддерживать диапазоны (`30...300 °C`), точные значения (`53 л`), условные (`не менее 0.5 °C`)
3. Записать `tender_analyses.extracted_specs`.

### 7.2. Module 2 — Matcher + Decision

**Шаг 2.1. Подбор кандидатов**

По типу/категории объекта закупки и упомянутым брендам/моделям отбираем кандидатов из `products`. Эвристика + быстрый текстовый матчинг по `model`/`brand`. Получаем 1–10 кандидатов.

**Шаг 2.2. Сравнение характеристик**

Для каждого кандидата:

1. Сопоставление атрибутов: для каждой требуемой характеристики ищем соответствие в `product.specs`.
2. Скоринг:
   - Точное попадание в значение или диапазон → +полный балл за пункт.
   - Покрытие требуемого диапазона нашим → +полный балл.
   - Частичное покрытие → +доля.
   - Не покрываем → 0 баллов и попадаем в `fails_on`.
3. Вес каждого пункта зависит от `required` (обязательный=2.0, желательный=1.0).
4. LLM (Sonnet/`creative`) валидирует и обогащает: добавляет `reasoning` человеческим текстом.

**Шаг 2.3. Решение**

Правила в `config/decision_rules.toml`:

```toml
[score_thresholds]
pass_min = 70           # ≥70 → автоматически pass
review_min = 40         # 40-69 → review
# < 40 → fail

[hard_blockers]
# Если есть хоть один — сразу fail независимо от score
list = [
  "specific_brand_required_not_ours",  # ТЗ требует конкретный бренд, которого нет в нашем портфеле
]

[manual_review_triggers]
# Не fail, но обязательно ручная проверка
list = [
  "spec_extraction_low_confidence",    # LLM не уверен в извлечённых характеристиках
  "unknown_category",                  # категория прибора не определена
]

# Фильтрация по цене НЕ применяется — параметры важнее цены.
# Начальная цена обязательно выводится в отчёте и в карточке лида (поле begin_price).
```

**Решено:** порогов по цене нет — параметры важнее. Цена всегда отображается в выдаче поиска (поле `begin_price`), отчётах и карточке лида в Twenty.

### 7.3. Контракт между модулями

Строгий — модули общаются только через БД. Module 1 пишет `extracted_specs`, Module 2 читает. Это позволяет:
- Перезапустить Module 2 не перепарсивая документацию.
- Заменить любой модуль независимо.
- Тестировать модули по отдельности.

---

## 8. Агент 3 — CRM PUSHER

### 8.1. Резолвинг компании

```python
async def resolve_company(inn: str, ogrn: str, name: str) -> CompanyResolution:
    1. Поискать в companies_seen по inn → если есть, вернуть twenty_company_id.
    2. Запросить Twenty API: GET /companies?filter[inn]=<inn>
    3. Если найдено — записать в companies_seen, вернуть.
    4. Если не найдено — POST /companies с полями inn, ogrn, name, full_name.
    5. Записать новый twenty_company_id в companies_seen.
    6. Вернуть.
```

### 8.2. Создание лида

```python
async def create_lead(tender_id: str, company_id: str, analysis: TenderAnalysis) -> str:
    Поля Lead:
    - name: f"Тендер {tender.reg_number} — {tender.name[:80]}"
    - company_id: <resolved>
    - status: "unqualified"
    - source: "tenderland_pipeline"
    - tender_url: ссылка в кабинете Tenderland
    - reg_number: tender.reg_number
    - begin_price: tender.begin_price
    - end_date: tender.end_date  (deadline для подачи!)
    - region: tender.region
    - matched_product_code: analysis.best_match_id
    - matched_score: analysis.best_match_score
    - decision_reason: analysis.decision_reason
    - search_topic: tender.search_topic
    - notes: <markdown с краткой выжимкой extracted_specs и обоснованием>
    - attachments: [местная ссылка на zip-архив, опционально загружаем в Twenty]
```

### 8.3. Twenty API детали

**Решено:** Twenty уже работает на текущем VPS на `crm.13-33.pro` (часть инфры content system 13-33). Поднят и GraphQL, и REST endpoint — используем оба по ситуации (REST проще для CRUD, GraphQL точнее для выборок). После переезда новый VPS получает **полную реплику** этого Twenty-инстанса (тот же стек: Ubuntu / Docker / Twenty / GraphQL / REST / Postgres / MemPalace / LiteLLM).

**Что нужно сделать в Twenty перед запуском CRM Pusher:**

1. Получить API-токен от админа Twenty (`crm.13-33.pro` → Settings → API).
2. Добавить кастомные поля на стандартные сущности:
   - `Company`: `inn` (text, unique), `ogrn` (text), `kpp` (text)
   - `Lead`: `tender_url`, `tender_id` (TL*), `reg_number`, `begin_price` (numeric), `end_date` (date), `region`, `search_topic`, `matched_product_code`, `matched_score` (numeric), `decision_reason` (long text)
3. Добавить статусы Lead: `unqualified` (по умолчанию для всех новых из системы), `accepted`, `rejected`, `in_proposal`.
4. Записать URL и токен в `.env`: `TWENTY_API_URL`, `TWENTY_API_KEY`.

После переезда на новый VPS:
- Полная реплика Twenty с тем же набором custom fields → миграция через `pg_dump` Twenty-Postgres.
- Новый домен (корпоративный с Gmail) подключается к Twenty: smtp/notifications через Gmail.
- В `.env` обновляется только `TWENTY_API_URL`, всё остальное переносится как есть.

---

## 9. Каталог продукции

**Это блокирующая зависимость для Analyzer Module 2.** Без каталога матчинг невозможен — Analyzer работает в режиме «extract only» и пишет только `extracted_specs`, без `matched_products` и `decision`.

### 9.1. Схема одного прибора

```json
{
  "product_code": "memmert-un55",
  "brand": "Memmert",
  "model": "UN 55",
  "category": "drying_oven",
  "domain": "analytical",
  "synonyms": ["сушильный шкаф", "drying oven", "термошкаф"],
  "specs": [
    {"name": "температурный диапазон", "value_min": 30, "value_max": 300, "unit": "°C"},
    {"name": "объём камеры", "value": 53, "unit": "л"},
    {"name": "точность поддержания температуры", "value": 0.5, "unit": "°C", "comparator": "≤"}
  ],
  "consumables_for": [],
  "datasheet_paths": ["catalog/memmert/un55-datasheet.pdf"],
  "price_range_rub": [180000, 220000],
  "alternative_products": []
}
```

### 9.2. Как наполняем

**(Q6: как будем собирать каталог? Параллельная задача — отдельный чат / агент?)**

Источники:
- PDF-каталоги производителей.
- Существующая прайс-таблица Глювекса (Excel? 1С?).
- Сайты производителей.

Подход — полу-ручной с LLM-ассистом:
1. Менеджер скидывает PDF/Excel.
2. Скрипт прогоняет через LLM (Opus/`premium` для точности) → черновик JSON.
3. Менеджер ревьюит и правит.
4. Скрипт `seed_catalog.py` загружает в `products`.

**Это отдельная ветка работы.** Без каталога Analyzer Module 2 запускается, но всегда возвращает `decision='review'` — то есть всё попадает менеджеру вручную. Это не блокирует Этап 1-3, но без Этапа «Каталог» система остаётся «ассистированной», а не «автоматической».

---

## 10. Деплой и переносимость

### 10.1. docker-compose.yml (структура)

```yaml
services:
  postgres:
    image: postgres:16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: tender_pipeline
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  api:
    build: .
    command: uvicorn tender_pipeline.api.app:app --host 0.0.0.0 --port 8000
    env_file: .env
    volumes:
      - tenders_data:/var/lib/tenders
    depends_on: [postgres, redis]

  worker:
    build: .
    command: arq tender_pipeline.queue.settings.WorkerSettings
    env_file: .env
    volumes:
      - tenders_data:/var/lib/tenders
    depends_on: [postgres, redis]
    deploy:
      replicas: 2

  scheduler:
    build: .
    command: python -m tender_pipeline scheduler
    env_file: .env
    depends_on: [postgres, redis]

volumes:
  postgres_data:
  redis_data:
  tenders_data:
```

### 10.2. Перенос на новый VPS

**Решено:** новый VPS — полная реплика стека (Ubuntu / Docker / Twenty / GraphQL / REST / Postgres / MemPalace / LiteLLM с теми же моделями). Отдельный домен с корпоративной почтой на Gmail — рассылка и нотификации менеджеров живут там.

Порядок переезда:

1. На новом VPS: установка Ubuntu + Docker + docker-compose.
2. `git clone` всех репозиториев (gluvex_tender_machine, content system 13-33, Twenty).
3. Перенос томов через `rsync` + `pg_dump` старого Postgres каждого сервиса:
   - Twenty Postgres (Companies, Leads со всеми custom-fields, история действий) → восстановить.
   - Gluvex_Tender_Machine Postgres (`tenders`, `tender_analyses`, `crm_pushes`, `companies_seen`, `products`, `search_runs`) → восстановить.
   - MemPalace Postgres + Chroma → восстановить.
4. Перенос файловых томов: `/var/lib/tenders/` (zip-архивы и распакованные ТЗ), MemPalace volume, WebDAV inbox.
5. Скопировать все `.env` (вне git, по защищённому каналу): `TENDERLAND_API_KEY`, `TWENTY_API_KEY`, `LITELLM_BASE_URL`, `OPENROUTER_API_KEY`, `POSTGRES_DSN`, `REDIS_URL`.
6. Поменять домены на новые корпоративные: Twenty → новый, MemPalace → новый.
7. Подключение Gmail SMTP к Twenty для нотификаций менеджерам.
8. `docker compose up -d` → `alembic upgrade head` → smoke-тесты по каждому сервису.

**LiteLLM:** переиспользуем тот же конфиг что в content system 13-33 — модели `cheap`=Haiku, `creative`=Sonnet, `premium`=Opus, маршрутизация через OpenRouter (обходит RU-блок). Никаких отдельных API-ключей для Gluvex_Tender_Machine не заводим — работаем через локальный LiteLLM endpoint.

**Email-рассылки менеджерам:** включаются ПОСЛЕ переезда. До этого момента уведомления = только Twenty UI (менеджер сам открывает CRM). После переезда + Gmail — Twenty шлёт уведомления о новых лидах через Gmail SMTP.

### 10.3. Что закоммичено в git, что нет

| Закоммичено                                    | Не закоммичено (gitignored)                       |
|------------------------------------------------|---------------------------------------------------|
| Весь код в `src/`                              | `.env`                                            |
| `config/keywords_*.md` (источник истины ключей)| `config/searches/*.json` (генерируются из MD)     |
| `config/products/*.json` (каталог продукции)   | `/var/lib/tenders/` (zip-архивы, отчёты)          |
| `config/decision_rules.toml`                   | Логи                                              |
| `config/prompts/*.md`                          | Postgres dumps                                    |
| `docker-compose.yml`                           | Виртуальное окружение                             |
| `pyproject.toml`                               |                                                   |

---

## 11. Этапы реализации

| № | Этап                                | Что делается                                                                                          | Блокер для следующего |
|---|--------------------------------------|--------------------------------------------------------------------------------------------------------|------------------------|
| 1 | Скелет + Postgres + миграции         | Структура папок, alembic, схема БД, базовый FastAPI + ARQ + docker-compose                            | да                     |
| 2 | Searcher через Search/Find          | После активации модуля. Парсер MD→JSON, обёртка API, дедуп, скачивание архивов, отчёты              | да для Analyzer        |
| 3 | Analyzer Module 1 (без Module 2)    | Распаковка, классификация, извлечение характеристик. На выходе только `extracted_specs`              | нет (можно дальше без него — review) |
| 4 | CRM Pusher (без матчинга)           | Twenty integration, создание Company/Lead. Все лиды идут как `manual_review` потому что нет каталога | нет (полезно как ассистент) |
| 5 | Каталог продукции — отдельная ветка | Сбор каталога приборов и расходников, нормализация, `seed_catalog.py`, ревью менеджером              | да для Module 2        |
| 6 | Analyzer Module 2 (matcher+decision)| Подбор кандидатов, сравнение, скоринг, правила решений                                                | да для авторешений в CRM |
| 7 | Тонкая настройка                    | Калибровка порогов, EXCLUDE, исправление промптов по реальным результатам                            | -                      |
| 8 | Будущее — Proposal Generator         | Генерация файла-заявки по принятому лиду                                                              | -                      |

**Минимальная точка ценности (MVP):** этапы 1+2+3+4 — менеджер получает в Twenty все новые тендеры с распарсенными характеристиками и ссылками на zip. Уже сильно лучше чем сейчас. Добавление этапов 5+6 превращает «ассистент» в «автомат с фильтрацией».

---

## 12. Статус вопросов

### Закрытые (решено)

| #  | Вопрос                                                                | Решение                                                                                  |
|----|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Q1 | Имя проекта верхнего уровня                                          | **`gluvex_tender_machine`**                                                              |
| Q4 | Пороги score, фильтры цены                                           | Порогов по цене нет — параметры важнее. Цена обязательно в выдаче и в карточке лида.    |
| Q5 | Twenty CRM: версия, GraphQL/REST, custom-fields                      | Twenty на `crm.13-33.pro`, поднят GraphQL+REST. Custom-fields добавляются перед Этапом 4 (см. 8.3). |
| Q7 | Twenty на новом VPS — миграция?                                      | Полная реплика через pg_dump → restore (см. 10.2). Старая история компаний/лидов сохраняется. |
| Q8 | LiteLLM — переиспользуем существующий?                               | Да, тот же endpoint что и в content system 13-33. Модели cheap/creative/premium через OpenRouter. |
| Q9 | Где живёт Twenty                                                     | На том же VPS 186.246.1.61 что и весь content system 13-33. После переезда → реплика на новом. |

### Открытые

| #  | Вопрос                                                                                                | Кому             |
|----|-------------------------------------------------------------------------------------------------------|-------------------|
| Q2 | Точные id фильтров `tender_publishDate` и `tender_endDate` через GetFilterList                       | Я сделаю сам когда возьмусь за Searcher Этап 2 |
| Q3 | Сколько одновременных запросов держит Tenderland API                                                  | Тебе при разговоре с менеджером Tenderland при активации Search/Find |
| Q6 | Каталог продукции — источники, кто собирает                                                           | Отдельная ветка работы (другой чат) |
| Q10| Резервное копирование — куда делаем dumps                                                             | После переезда — на новый VPS, политика копирования с content system 13-33 |
| Q11| **НОВЫЕ** автопоиски по расходникам хроматографии (колонки, картриджи SPE, виалы, септы, феррулы) и общелабораторному оборудованию (Memmert, Binder, Sartorius, Buchi, Metrohm + др.) | Тебе — отдельные чаты, как для аналитики и молекулярки. Я подхватываю готовые keywords_*.md автоматически — парсер MD не требует никаких изменений. |

---

## 13. Что я могу делать прямо сейчас, не дожидаясь активации Search/Find

1. **Этап 1 целиком** — скелет проекта, Postgres-схема, миграции, ARQ, docker-compose, FastAPI заготовка. Не требует API Поиск.
2. **Парсер MD → JSON** — отрабатывается на статичных данных. Готов к моменту активации.
3. **Analyzer Module 1** — работает с уже скачанными zip из `/var/lib/tenders/`. Тестируется на 5 архивах Memmert, которые уже скачаны.
4. **Промпты** для классификатора и экстрактора — пишутся, тестируются на реальных файлах.
5. **CRM-интеграция (Этап 4)** — клиент к Twenty REST/GraphQL пишется и тестируется на текущем `crm.13-33.pro` сразу. Кастомные поля на Company/Lead добавляем заранее.

После активации модуля Search/Find — Этап 2 запускается и за 1-2 дня доводится до конца.

---

## 14. Что нельзя делать пока

- **Этап 5 (каталог)** — нужны источники от тебя, отдельная ветка.
- **Этап 6 (matcher)** — без каталога невозможен.
- **Этапы 7-8 — будущие автопоиски** (хром-расходники, общелабораторное Memmert/Binder/Sartorius/Buchi/Metrohm). Нужны keywords_*.md от тебя. Код не требует изменений — парсер MD универсальный.
- **Email-рассылки** — после переезда на новый VPS с корпоративным Gmail.

---

## 15. Зафиксировано на текущий момент (snapshot готовности)

### 15.1. Готово полностью

| Компонент                                  | Где лежит                                                    | Статус         |
|--------------------------------------------|--------------------------------------------------------------|-----------------|
| Tenderland API клиент (Export/Create + Get)| `tenderland_bot/src/tenderland_bot/`                         | работает        |
| Скачивание zip-архивов                     | `tenderland_bot/src/tenderland_bot/document_fetcher.py` (или эквивалент) | работает |
| Excel/Markdown отчёты по тендерам          | `tenderland_bot/src/tenderland_bot/exporter.py`              | работает        |
| Структура папок `Z:\tenders\<topic>\<DDMMYY>\` | согласована                                              | работает        |
| Справочник фильтров и полей API            | `tenderland_bot/docs/filters.json`, `fields.json`            | актуально       |
| Конфиг ключевых слов: 8 поисков аналитики  | `tenderland_bot/config/keywords_config.md`                   | финальный       |
| Конфиг ключевых слов: 5 поисков молекулярки| `tenderland_bot/config/keywords_config_molecular_diagnostics.md` | финальный   |
| Handoff-документ для агента-анализатора    | `tenderland_bot/HANDOFF_TO_ANALYZER.md`                      | финальный       |
| Архитектура полной системы                 | `tenderland_bot/ARCHITECTURE.md`                             | этот документ   |

### 15.2. Карта автопоисков

| Домен                  | Тема                          | Статус       | Где описан                                          |
|------------------------|-------------------------------|--------------|----------------------------------------------------|
| analytical             | 01_LC_LCMS_GPC_Prep           | ✅ финальный | keywords_config.md                                  |
| analytical             | 02_GC_GCMS                    | ✅ финальный | keywords_config.md                                  |
| analytical             | 03_ICP_OES                    | ✅ финальный | keywords_config.md                                  |
| analytical             | 04_AAS                        | ✅ финальный | keywords_config.md                                  |
| analytical             | 05_ICP_MS                     | ✅ финальный | keywords_config.md                                  |
| analytical             | 06_IC                         | ✅ финальный | keywords_config.md                                  |
| analytical             | 07_UV_Vis                     | ✅ финальный | keywords_config.md                                  |
| analytical             | 08_FTIR                       | ✅ финальный | keywords_config.md                                  |
| analytical             | 09_Service *(опц.)*           | ✅ финальный | keywords_config.md, опциональный                    |
| analytical             | 10_Consumables *(опц.)*       | ✅ финальный | keywords_config.md, опциональный                    |
| molecular_diagnostics  | MDX_01_Sequencers             | ✅ финальный | keywords_config_molecular_diagnostics.md           |
| molecular_diagnostics  | MDX_02_Reagents_Libraries     | ✅ финальный | keywords_config_molecular_diagnostics.md           |
| molecular_diagnostics  | MDX_03_Oncology_Panels        | ✅ финальный | keywords_config_molecular_diagnostics.md           |
| molecular_diagnostics  | MDX_04_NIPT_PGT_HLA           | ✅ финальный | keywords_config_molecular_diagnostics.md           |
| molecular_diagnostics  | MDX_05_Service *(опц.)*       | ✅ финальный | keywords_config_molecular_diagnostics.md           |
| chromatography         | CHR_01_Consumables            | 🟡 PLANNED   | будет в `keywords_config_chromatography_consumables.md` |
| general_lab            | GLE_01_Memmert_Binder_Sartorius_Buchi_Metrohm_etc | 🟡 PLANNED | будет в `keywords_config_general_lab_equipment.md` |

> Когда появятся новые `keywords_*.md` — парсер MD автоматически их подхватит, никаких изменений в коде не нужно.

### 15.3. Готовые архитектурные решения

- **Имя проекта:** `gluvex_tender_machine`
- **Стек:** Python 3.12, FastAPI, ARQ (Redis), SQLAlchemy 2.x async, Postgres 16, Docker Compose
- **LLM:** через LiteLLM endpoint существующей content system 13-33, модели cheap=Haiku, creative=Sonnet, premium=Opus
- **CRM:** Twenty на `crm.13-33.pro` (REST + GraphQL), полная реплика на новом VPS после переезда
- **Хранилище файлов:** `/var/lib/tenders/<topic>/<DDMMYY>/*.zip` + `/var/lib/tenders/unpacked/<tender_id>/*`
- **Дедуп:** Postgres таблица `tenders` по `tender_id` (формат TL*), компании по `inn` в `companies_seen`
- **Расписание:** ARQ cron `0 7 * * 1-5` (07:00 МСК, рабочие дни), к 09:00 лиды в CRM
- **Цена:** обязательное поле в выдаче (`begin_price`), не используется как фильтр
- **Скоринг:** pass ≥ 70, review 40–69, fail < 40 (можно калибровать в `decision_rules.toml` без правки кода)
- **Email-рассылки:** не сейчас, после переезда на новый VPS с корпоративным Gmail

### 15.4. Что сейчас в работе или ждёт активации

| Задача                                                    | Готовность | Блокер                                              |
|-----------------------------------------------------------|------------|-----------------------------------------------------|
| Этап 1 — скелет gluvex_tender_machine, миграции, инфра   | 0%         | нет                                                 |
| Этап 2 — Searcher через Search/Find                       | 0%         | активация модуля API Поиск (завтра)                 |
| Этап 3 — Analyzer Module 1                                | 0%         | нет, можно начинать на Memmert-архивах              |
| Этап 4 — CRM Pusher                                       | 0%         | нужны custom-fields на Twenty (ставим заранее)      |
| Этап 5 — Каталог продукции                                | 0%         | отдельная ветка работы                              |
| Этап 6 — Analyzer Module 2 (matcher)                      | 0%         | каталог                                             |
| Будущие автопоиски: хром-расходники, общелабораторное     | 0%         | новые keywords_*.md от тебя                          |

---

_Документ обновляется по мере уточнения. Каждое серьёзное изменение архитектуры — через коммит с обновлением этого файла. Все ответы на Q-вопросы фиксируются в разделе 12 без удаления вопроса — сохраняем историю решений._

---

## 16. Стратегия точечных поисков (fine-grained searches)

**Эмпирически установлено** (probe 2026-05-06): `Export/Create + Export/Get` возвращает поля без подсветки матчингов. Подсветка `<span class='tl-highliter'>` появляется **только в выдаче `Search/Find`** (модуль API Поиск). Это меняет стратегию ключей после активации модуля.

### 16.1. Принцип

Вместо 13 широких поисков с гигантскими INCLUDE-строками — **десятки точечных поисков** с явной AND-логикой между фильтрами. Один поиск нацелен на конкретный класс прибора + конкретного вендора + конкретные модельные диапазоны (или конкретные приборные признаки).

**Иерархия имён:** `<domain>_<class>_<vendor>_<model_or_feature>`

Примеры:

| Точечный поиск                | Что ловит                                                          |
|-------------------------------|---------------------------------------------------------------------|
| `analytical_hplc_agilent_1260`| Тендеры конкретно на Agilent 1260 серии (1260 Infinity, 1260 II)   |
| `analytical_hplc_agilent_1290`| Конкретно 1290 серии                                                |
| `analytical_hplc_with_dad`    | ВЭЖХ-системы любого вендора + явное упоминание DAD/PDA-детектора   |
| `analytical_lcms_tq_agilent_6470` | Конкретно тройной квадруполь Agilent 6470                       |
| `analytical_lcms_tq_shimadzu_8060`| Конкретно LCMS-8060 серии                                       |
| `analytical_lcms_qtof_sciex_zenotof` | ZenoTOF 7600                                                  |
| `mdx_ngs_illumina_novaseq_x`  | Конкретно NovaSeq X / X Plus                                        |
| `mdx_ngs_mgi_dnbseq_t7`       | Конкретно DNBSEQ-T7                                                 |
| `mdx_consumables_flowcell_illumina` | Flow cells конкретно к Illumina                                |

### 16.2. Технически — как это выглядит в JSON для `/Search/Find`

Каждый точечный поиск = **отдельный POST-запрос** с фильтрами в массиве `and`. Внутри одного фильтра пробел = OR, `++` = AND-стемминг, `=` = точное совпадение. Между фильтрами в массиве `and` действует AND.

```json
{
  "topic": "analytical_lcms_tq_agilent_6470",
  "domain": "analytical",
  "fields": [
    "tender_regNumber", "tender_name", "tender_beginPrice",
    "tender_lotCustomerShortName", "tender_lotCustomerInn", "tender_lotCustomerOgrn",
    "tender_publishDate", "tender_endDate", "tender_region",
    "tender_typeName", "tender_lotCategories",
    "tender_files", "tender_etpLink", "tender_fileCount",
    "tender_notification"
  ],
  "filters": {
    "and": [
      {"id": 136, "name": "tender_keywords_include", "type": "text",
       "include": "Agilent++6470 6470++Triple++Quad =LCMS-6470"},
      {"id": 137, "name": "tender_keywords_exclude", "type": "text",
       "include": "<common_exclude> 6460 6480 6490 6495 6530 6545"},
      {"id": 110, "name": "tender_publishDate", "type": "range",
       "from": "<today-7>", "to": null},
      {"id": 111, "name": "tender_endDate", "type": "range",
       "from": "<today>", "to": null}
    ]
  },
  "interval": [0, 1],
  "pageSize": 100,
  "skip": 0,
  "orderBy": "tender_sysPublishDate.desc"
}
```

**EXCLUDE для точечного поиска** = общий EXCLUDE + специфические анти-ложные срабатывания (отсекаем близкие модели, чтобы 6460-я не попала в результаты 6470-й).

### 16.3. Структура keywords-конфигов с точечными поисками

```
config/searches/
├── _shared/
│   ├── common_exclude.txt           # общий EXCLUDE для всех (мусор + ПЦР для молекулярки)
│   ├── analytical_exclude.txt       # доп EXCLUDE для аналитики
│   └── molecular_exclude.txt        # доп EXCLUDE для молекулярки (ПЦР отсечка)
├── analytical/
│   ├── hplc/
│   │   ├── agilent_1260.json
│   │   ├── agilent_1290.json
│   │   ├── shimadzu_nexera.json
│   │   ├── waters_acquity.json
│   │   ├── thermo_vanquish.json
│   │   ├── thermo_ultimate.json
│   │   ├── with_dad.json            # любой ВЭЖХ + DAD/PDA
│   │   └── preparative.json         # препаративная ВЭЖХ
│   ├── lcms_tq/
│   │   ├── agilent_6470.json
│   │   ├── agilent_6495.json
│   │   ├── shimadzu_8060.json
│   │   ├── sciex_5500.json
│   │   ├── sciex_6500.json
│   │   └── waters_xevo_tq.json
│   ├── lcms_qtof/
│   ├── lcms_orbitrap/
│   ├── gc/
│   ├── gcms/
│   ├── icp_oes/
│   ├── icp_ms/
│   ├── aas/
│   ├── ic/
│   ├── uv_vis/
│   └── ftir/
├── molecular/
│   ├── ngs_short_read/
│   │   ├── illumina_miseq.json
│   │   ├── illumina_nextseq.json
│   │   ├── illumina_novaseq.json
│   │   ├── illumina_iseq.json
│   │   ├── mgi_dnbseq_g50.json
│   │   ├── mgi_dnbseq_g400.json
│   │   ├── mgi_dnbseq_t7.json
│   │   ├── mgi_dnbseq_t10_t20.json
│   │   ├── helicon_g400.json
│   │   ├── salus.json
│   │   └── genemind_genolab.json
│   ├── ngs_long_read/
│   │   ├── ont_minion.json
│   │   ├── ont_promethion.json
│   │   └── pacbio.json
│   ├── capillary/
│   │   ├── abi_3500.json
│   │   └── seqstudio.json
│   ├── consumables/
│   │   ├── flowcell_illumina.json
│   │   ├── flowcell_mgi.json
│   │   ├── flowcell_ont.json
│   │   ├── library_prep_illumina.json
│   │   └── extraction_kits.json
│   ├── oncology_panels/
│   │   ├── brca.json
│   │   ├── egfr_kras_braf_lung.json
│   │   ├── colorectal.json
│   │   ├── cgp_panels.json
│   │   ├── amoydx.json
│   │   ├── parseq.json
│   │   └── foundationone.json
│   └── nipt_pgt_hla/
│       ├── nipt.json
│       ├── pgt_a.json
│       ├── pgt_m.json
│       └── hla_typing.json
└── chromatography_consumables/
    ├── columns_lc.json
    ├── columns_gc.json
    ├── spe_cartridges.json
    ├── vials_septa.json
    └── ferrules_liners.json
```

### 16.4. Что меняется в Searcher

- На каждый запуск — обход всех JSON-ов в `config/searches/<domain>/<class>/`
- Параллельность: ~50-100 параллельных POST-запросов через `asyncio.gather` (Tenderland держит несколько одновременных, точное число — Q3)
- Лимит 1000 запросов/день при 100 точечных поисках = 100 запросов на прогон, можно делать утром + вечером, влезаем
- В БД `tenders.matched_searches TEXT[]` — массив имён точечных поисков, поймавших этот тендер (один тендер может попасть в несколько)
- В БД `tenders.match_snippets JSONB` — сниппеты с подсветкой по полям `tender_name` / `tender_notification` / `tender_files`, сгруппированные по точечному поиску

### 16.5. Что меняется в Analyzer

**Module 1 (Classifier + Extractor) сильно упрощается:**

- **Атрибуция категории/вендора/модели уже сделана поиском** — не нужен LLM-классификатор «что это вообще». Имя точечного поиска (`analytical_lcms_tq_agilent_6470`) парсится в `{domain: analytical, class: lcms_tq, vendor: agilent, model: 6470}`.
- **Сниппеты с подсветкой = первый источник характеристик** — там уже есть контекст совпадения. LLM может сразу обогатить сниппеты в характеристики без чтения целых файлов.
- **Парсинг полных файлов остаётся**, но цель уже не «определить класс прибора», а «добыть конкретные числовые параметры» (температурный диапазон, объём, точность, скорость потока, давление и т.д.). Это делается LLM на тексте только релевантных файлов (тех, в которых Tenderland нашёл совпадения).

**Module 2 (Matcher + Decision) становится прямолинейнее:**

- Кандидаты из каталога уже сильно сужены атрибутами поиска (если поиск `analytical_lcms_tq_agilent_6470` — не нужно сравнивать с продуктами категории `gc` или `aas`)
- Часто известна **конкретная модель конкурента** → сравнение «наш аналог vs Agilent 6470» это конкретная задача, а не «угадай что нужно»
- Решение `pass / review / fail` принимается по покрытию числовых параметров, а не по «попали в категорию или нет»

### 16.6. Изменение модели данных

```sql
ALTER TABLE tenders ADD COLUMN matched_searches TEXT[];
ALTER TABLE tenders ADD COLUMN match_snippets JSONB;
-- match_snippets структура:
-- [
--   {
--     "search_topic": "analytical_lcms_tq_agilent_6470",
--     "in_field": "tender_files",
--     "snippets": ["...требуется хроматограф <hl>Agilent</hl> <hl>6470</hl> Triple Quad..."]
--   },
--   {
--     "search_topic": "analytical_hplc_with_dad",
--     "in_field": "tender_notification",
--     "snippets": ["...с <hl>диодно-матричным</hl> <hl>детектором</hl>..."]
--   }
-- ]

CREATE TABLE search_definitions (
  topic            TEXT PRIMARY KEY,
  domain           TEXT NOT NULL,
  class            TEXT NOT NULL,
  vendor           TEXT,
  model_or_feature TEXT,
  filter_json      JSONB NOT NULL,           -- готовое тело для Search/Find
  is_active        BOOLEAN DEFAULT true,
  last_run_at      TIMESTAMPTZ,
  last_match_count INTEGER
);
```

### 16.7. Открытые вопросы для проверки после активации Search/Find

| #   | Вопрос                                                                                                  |
|-----|---------------------------------------------------------------------------------------------------------|
| Q12 | Поддерживает ли Tenderland вложенные `or` внутри `and` в `filters`? Если да — точечные поиски можно компактнее. |
| Q13 | Какие именно поля приходят с подсветкой: `tender_name`, `tender_notification`, `tender_files` — все или только часть? |
| Q14 | Как Tenderland разрешает множественные совпадения в одном тендере — все сниппеты или только первый?    |
| Q15 | Реальный rate-limit Search/Find — сколько одновременных запросов и запросов в минуту                  |
| Q16 | Включает ли `tender_files` ПОЛНЫЙ распарсенный текст всех документов или только сниппеты?              |

Все 5 вопросов проверяются одним пробным запросом сразу после активации модуля.

### 16.8. Итог по карте автопоисков

Старые 13 широких автопоисков (15.2) **остаются на бумаге** как справочное руководство по ключевым словам — они полезны как «mental map» доменов. Но **не реализуются** в gluvex_tender_machine как 13 отдельных запросов. Вместо них — точечные поиски из раздела 16.3.

Будущие keywords_*.md (хром-расходники, общелаб Memmert/Binder/Sartorius/Buchi/Metrohm) приходят в проект уже **в новой структуре** — иерархия точечных JSON-ов в `config/searches/<domain>/<class>/`. При появлении файлов от тебя я их разворачиваю в эту иерархию автоматически.

---

_End of document._

---

## 17. Стратегическое решение: отдельный VPS + свой MemPalace для тендерной воронки

**Дата фиксации:** 2026-05-06

### 17.1. Принцип

Gluvex_Tender_Machine — это **отдельный продакшн-стек**, не подмодуль content system 13-33. Им нужен:

- **Свой VPS** (новый, отдельный от 186.246.1.61, где живёт content system 13-33)
- **Свой MemPalace** — отдельный инстанс для тендерных данных, не смешанный с личным/творческим content system 13-33
- **Свой Twenty CRM** — отдельная база компаний и лидов (бизнес Gluvex изолирован от 13-33)
- **Свой Postgres** для метаданных тендеров и истории выгрузок
- **Общий LiteLLM** — можно переиспользовать роутер моделей (cheap/creative/premium через OpenRouter)

### 17.2. Зачем отдельный MemPalace

Как только перейдём на ежедневный сбор данных, нужно индексировать:

- **Архив описаний тендеров** — тексты ТЗ, извещений, файлы документации
- **Профиль заказчиков** — кто что покупает исторически, какие бренды предпочитает
- **Прайс-листы и каталоги Gluvex** — для семантического поиска «что у нас есть похожее»
- **Победители прошлых тендеров** — кто кому что поставил и за сколько (бенчмаркинг)
- **Заявки и предложения** Gluvex — как мы участвовали раньше, что выигрывали

Это специфичный корпус, **не должен смешиваться** с content system 13-33 (там личное / творческое / контентное). Отдельный MemPalace даёт:

- Чистоту поиска (никаких пересечений с книгами / транскриптами / контентом)
- Изоляцию ACL (тендерные данные могут быть коммерчески чувствительные)
- Отдельный жизненный цикл (можно мигрировать / резервировать независимо)

### 17.3. Wing-структура нового MemPalace для тендеров

Предложение по структуре:

| Wing                 | Что хранится                                               |
|----------------------|------------------------------------------------------------|
| `tenders_active`     | Активные текущие тендеры (свежий поток, обновляется ежедневно) |
| `tenders_archive`    | Закрытые тендеры с результатами                            |
| `customers_profile`  | Накопленные профили заказчиков (ИНН → закупочная история)  |
| `gluvex_catalog`     | Каталог продукции Gluvex с характеристиками                |
| `gluvex_proposals`   | Прошлые заявки/коммерческие предложения Gluvex             |
| `competitor_intel`   | Информация о конкурентах (кто выигрывал что у кого)         |
| `tz_documents`       | Распакованные тексты ТЗ для семантического поиска          |

### 17.4. Тактический фокус сейчас (до переезда)

Пока нет нового VPS — **не лезем в CLI / Analyzer / классификатор**. Это большая алгоритмическая работа (как сказал заказчик), требующая:
- Стабильной инфраструктуры на новом VPS
- Каталога продукции Gluvex в структурированном виде (отдельная задача)
- Базы для накопления данных
- Активного API Поиска для безлимитной работы с фильтрами

**Чем занимаемся сейчас (фаза 1 — на UI Tenderland):**

1. ✅ Отлажена методология (Test 4b: 5203 за 2 года, ~75% релевантность для приборов аналитики)
2. ✅ Применена к расходникам хроматографии (Test 5: 11 483 за 2025, требует мелких подкруток EXCLUDE)
3. ⏳ Аналогично применить к: молекулярка приборы+панели, молекулярка расходники, общелаб (Memmert/Binder/Sartorius/Metrohm/Buchi/Sotax/S+H)
4. ⏳ Накапливать **архивные выгрузки в xlsx** — это будет сырьё для импорта в MemPalace на новом VPS
5. ⏳ Документировать каждый автопоиск, его параметры и результаты в `tenderland_bot/docs/`

**Чем занимаемся при переезде на новый VPS (фаза 2):**

1. Развернуть стек: Ubuntu + Docker + Postgres + Redis + Twenty + MemPalace + LiteLLM
2. Импортировать накопленные xlsx-выгрузки в `tenders_archive` wing MemPalace (~50 000 тендеров за 2 года по всем 5 темам)
3. Развернуть `gluvex_tender_machine` Этап 1 (скелет + БД + scheduler)
4. Активировать Search/Find и перенести фильтры из UI в JSON-конфиги
5. Запустить ежедневный сбор активных тендеров

**Чем занимаемся после переезда (фаза 3 — алгоритмическая работа):**

1. Собирать каталог продукции Gluvex (отдельная ветка работы)
2. Загружать каталог в `gluvex_catalog` wing MemPalace
3. Реализовать Analyzer Module 1 — извлечение характеристик из ТЗ через LLM
4. Реализовать Analyzer Module 2 — матчер «их требования vs наш каталог» через семантический поиск в MemPalace
5. Подключить CRM Pusher → лиды в Twenty
6. Email-дайджесты менеджерам через Gmail SMTP

### 17.5. Что фиксируется к моменту переезда

К моменту когда новый VPS готов, у нас должно быть в `tenderland_bot/`:

- 5 production-автопоисков в Tenderland UI (приборы аналитики ✅, расходники хроматограф 🟡, молекулярка приборы 🟡, молекулярка расходники 🟡, общелаб 🟡)
- Полные INCLUDE/EXCLUDE строки в `docs/autosearch_configs_phase2.md` и `docs/autosearch_ui_patches.md`
- Архив xlsx-выгрузок за исторический период (минимум 2 года) для импорта
- ARCHITECTURE.md (этот документ) с актуальной архитектурой
- HANDOFF_TO_ANALYZER.md для будущего разработчика анализатора
- Анализаторский скрипт (`scripts/analyze_lcms_export.py`) для оценки качества выборок

Этот «пакет фазы 1» переезжает целиком в `gluvex_tender_machine/` на новом VPS.

### 17.6. Каталог Gluvex — параллельная задача-блокер

Без структурированного каталога продукции невозможен матчер. Это **отдельная задача-параллель**, которую надо начать собирать уже сейчас (хоть в Excel, хоть в JSON), чтобы к моменту переезда было что загружать в `gluvex_catalog` wing.

Источники:
- PDF-каталоги дистрибьюторов и производителей (которые Gluvex поставляет)
- Прайс-лист Gluvex (Excel/1С)
- Сайт https://gluvexlab.com/catalog/
- Спецификации к проданным позициям

Минимальная схема одного товара (для каталога):
```json
{
  "product_code": "...",
  "category": "hplc_column | gc_column | spe_cartridge | vial | filter | ...",
  "brand": "Phenomenex | Restek | ...",
  "model": "Luna C18 100x4.6mm 5um",
  "specs": {
    "phase": "C18",
    "particle_size_um": 5,
    "column_length_mm": 100,
    "column_id_mm": 4.6,
    "compatible_with": ["Agilent 1260", "Shimadzu Nexera"]
  },
  "price_rub": 28000,
  "datasheet_url": "..."
}
```

### 17.7. Что НЕ делаем до переезда

- ❌ Не пишем CLI-классификатор сегментов (вернёмся при наличии БД и MemPalace)
- ❌ Не пишем Analyzer (Module 1/2) — без каталога он бесполезен
- ❌ Не настраиваем CRM Pusher — нужна реальная Twenty инстанция нового VPS
- ❌ Не делаем Email-рассылку — будет через Gmail SMTP (Google Workspace, уже оплачен) после переезда

Это всё фаза 3, после полного развёртывания стека на новом VPS.

### 17.8. Стек, выбор моделей, расчёт расходов VPS

Все решения по железу, AI-моделям и стоимости вынесены в отдельный документ:

📄 **[docs/SERVER_INFRASTRUCTURE.md](docs/SERVER_INFRASTRUCTURE.md)** — полная спецификация:

- Финальный стек ПО (Postgres / Redis / Twenty / MemPalace / Tender Pipeline / LiteLLM / Whisper)
- **2 модели в работе** (без чехарды): локально Qwen 2.5 32B Q4, внешне Anthropic Sonnet через OpenRouter
- Whisper: faster-whisper локально + Groq fallback
- 3 сценария VPS Selectel (без GPU старт / с GPU 16 GB целевой / с GPU 24 GB перспективный)
- Стоимость операций по сценариям (~$340-400/мес старт, ~$540-720/мес целевой)
- План решения GPU/без GPU после 4-8 недель тестов с реальными метриками
- Чек-лист миграции в 5 этапов
- Чек-лист тестирования (Whisper качество, LLM качество, нагрузка VPS)

---

_End of document._
