# Gluvex — Master-data архитектура и контуры системы

**Версия:** 1.0
**Дата:** 2026-05-10
**Статус:** утверждено заказчиком, **верхнеуровневый источник истины**
**Связанные документы:**
- [`storage-architecture.md`](storage-architecture.md) — слой хранения, идентификаторы, retrieval
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Tender Pipeline (Searcher / Analyzer / CRM Pusher)

> Этот документ **выше** storage-architecture.md и ARCHITECTURE.md по иерархии.
> Он определяет **кто хранит что и кто решает**. Storage и pipeline — производное.

---

## 1. Главный принцип

> **Не строить Twenty как «ещё одну 1С».**
> 1С — юридический и коммерческий **центр правды**.
> Twenty — рабочее место менеджеров.
> Postgres — техническая память и аудит автоматизации.
> MemPalace + Qdrant — умный поисковый индекс, **всегда пересобираемый**.
> Storage — архив документов и бэкапов.

Все новые интеграции проектируются через этот принцип, иначе система быстро становится набором несогласованных копий данных.

---

## 2. Пять контуров системы

```
┌────────────────────────────────────────────────────────────────────┐
│  1C CORE  —  единственный центр правды                              │
│  • клиенты / контрагенты                                             │
│  • продукты / каталог                                                │
│  • цены / прайсы / скидки                                            │
│  • КП / коммерческие предложения                                     │
│  • сделки / заказы / отгрузки / финансы                              │
│  • статус контрагента: благонадёжный / в стоп-листе / новый          │
└──────────────────────────┬─────────────────────────────────────────┘
                          │ 1c-bridge (выделенный сервис)
                          │ протокол: REST / OData / WS-обмен 1С
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TWENTY CRM  —  операционный интерфейс продаж                        │
│  • 3 раздельные воронки лидов: website / tender / manager            │
│  • задачи менеджерам, коммуникации, заметки                          │
│  • ручная квалификация                                                │
│  • рабочие копии Company/Person, помеченные status_1c (validated /    │
│    pending_1c_validation / conflict / new_local)                     │
│                                                                       │
│  ❌ НЕ создаёт мастер-карточки клиентов сам                          │
│  ❌ НЕ хранит финальные коммерческие данные                          │
│  ❌ НЕ источник истины для прайсов и КП                              │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │ Twenty REST/GraphQL API
                                       │ (вход для tender pipeline,
                                       │  выход для дашбордов)
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TENDER MACHINE  —  автоматический контур                            │
│  • Searcher: Tenderland API → новые тендеры                          │
│  • Analyzer: парсинг ТЗ → характеристики → матчинг                    │
│  • CRM Pusher: создаёт tender_lead в Twenty + trace в Postgres        │
│                                                                       │
│  ❌ НЕ принимает финальные коммерческие решения                      │
│  ❌ НЕ заменяет 1С                                                    │
│  ✅ Может только пометить status='unqualified' / 'review' и ждать    │
│     ручного решения менеджера                                         │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE / AI LAYER  —  индекс, не истина                          │
│  • MemPalace — агентная память, drawer/wing, рабочий контекст         │
│  • Qdrant — векторный индекс по chunks                                │
│  • LiteLLM — модели + трассировка                                     │
│  • Whisper — транскрипция звонков                                     │
│                                                                       │
│  ✅ Всегда пересобирается из 1С + Postgres + Storage                  │
│  ❌ НЕ источник истины — рестарт с пустым Qdrant не теряет данных     │
└──────────────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AUDIT / BACKUP / MONITORING                                          │
│  • Postgres `audit_events` (append-only)                              │
│  • Backup Postgres + MinIO + конфиги                                  │
│  • Метрики, алерты, дашборды                                          │
│  • Vault для секретов (.env через secrets manager, не plain text)    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Master-system table

Для каждой сущности — где истина. **Конфликт побеждает master-система.**

| Сущность | Master | Реплика в | Кто решает конфликт |
|---|---|---|---|
| **Клиент / контрагент** | 1С | Twenty (read-mostly) | 1С |
| **Контакт (физлицо у клиента)** | 1С | Twenty (рабочая копия с CRM-полями: задачи, заметки) | 1С — для ФИО/email/телефон. Twenty — для CRM-полей |
| **Продукт / номенклатура** | 1С | Postgres (`products` таблица) + Qdrant (для семантического матчинга) | 1С |
| **Прайс / цена** | 1С | Postgres (`prices` таблица) + MinIO (`prices/`) + Qdrant | 1С |
| **Скидочное правило** | 1С | Postgres (для агентов КП) | 1С |
| **КП (коммерческое предложение)** | 1С | MinIO (`kp-generated/`) + Postgres (`kp_drafts` для AI-генерации до approve) | 1С |
| **Сделка / заказ** | 1С | — | 1С (Twenty не дублирует) |
| **Лид (website / tender / manager)** | **Twenty** | Postgres (`entity_links` для трассировки) | Twenty |
| **Тендер (raw)** | **Tender Machine / Postgres** | MinIO (zip + распакованные файлы) | Tender Machine |
| **Документ тендера (ТЗ, контракт)** | MinIO (file) + Postgres (`document_registry`) | Qdrant chunks | Postgres registry |
| **AI-анализ тендера** | Postgres (`tender_analyses`) | — | Tender Machine |
| **AI-объяснение / explanation** | Postgres (`llm_runs`) | — | append-only, не меняется |
| **История аудита** | Postgres (`audit_events`) | — | append-only, **НИКОГДА не меняется** |
| **Запись звонка / транскрипт** | MinIO (`calls/`) + Postgres (`document_registry`) | Qdrant chunks | Postgres registry |
| **Email-thread** | Postgres + MinIO (для вложений) | Qdrant chunks | Postgres |
| **Статус контрагента (благонадёжный/стоп-лист)** | 1С | Twenty (отображение) | 1С |

**Правило:** если поле есть в master-системе — реплика **read-only** для всех остальных. Запись только через master.

Исключение: **рабочие CRM-поля** (задачи, заметки, комментарии менеджера, временные статусы обработки) — пишутся в Twenty и не уходят в 1С (если только не явная синхронизация).

---

## 4. Direction of trust — поток данных

```
1С ───── 1c-bridge ─────► Postgres (kept in sync, idempotent)
                              │
                              ├─► Twenty (replica для UI менеджеров)
                              │   • read-only для master-полей
                              │   • read-write для CRM-полей
                              │
                              └─► Qdrant + MemPalace (индексация)

Tenderland ──► Tender Machine ──► Postgres ──► Twenty (как tender_lead)
                                       │
                                       └─► entity_links: tender ↔ lead ↔ company

Manager UI (Twenty) ──► Twenty CRM ──► Postgres (entity_links)
                                            │
                                            └─► 1c-bridge (когда лид перешёл в КП)
                                                    │
                                                    └─► 1С создаёт КП → Postgres получает 1c_id
```

Ключевое: **никогда** не идём от Twenty / Tender Machine / MemPalace **обратно** в 1С через прямую запись в БД 1С. Только через `1c-bridge` API с явным контрактом и идемпотентностью.

---

## 5. Twenty CRM — три раздельные воронки лидов

Лиды разных источников **не смешиваются**. У каждой воронки — свои обязательные поля и стадии.

### 5.1. `website_leads`
Источник: форма на сайте, виджет, чат.

| Поле | Тип | Обязательное |
|---|---|---|
| `source` | enum (`website`) | ✅ |
| `landing_page` | url | ✅ |
| `utm_source` / `utm_medium` / `utm_campaign` | text | ⚠️ если есть |
| `email` / `phone` | text | минимум один |
| `inquiry_text` | text | ✅ |
| `referrer` | url | ⚠️ |

Стадии: `new → contacted → qualified → converted_to_opportunity / closed_lost`.

### 5.2. `tender_leads`
Источник: Tender Machine (CRM Pusher).

| Поле | Тип | Обязательное |
|---|---|---|
| `source` | enum (`tenderland_pipeline`) | ✅ |
| `tender_id` | text (TL*) | ✅ unique |
| `reg_number` | text | ✅ |
| `customer_inn` | text | ✅ |
| `customer_company_id` (FK Twenty Company) | UUID | ✅ |
| `begin_price` | numeric | ⚠️ |
| `deadline` (end_date) | timestamptz | ✅ |
| `region` | text | ⚠️ |
| `etp_link` | url | ⚠️ |
| `matched_product_code` | text | ⚠️ (есть только если matcher работал) |
| `matched_score` | numeric(5,2) | ⚠️ |
| `decision_reason` | text | ✅ |
| `analysis_status` | enum: `pending` / `extracting` / `done` / `error` | ✅ |
| `documents_url` | url (на наш UI с docs) | ✅ |
| `tender_machine_postgres_id` | UUID (link to Postgres) | ✅ |

Стадии: `unqualified → review → accepted (→ creates Opportunity) / rejected / archived`.

### 5.3. `manager_leads`
Источник: менеджер вручную ввёл (звонок, выставка, рекомендация).

| Поле | Тип | Обязательное |
|---|---|---|
| `source` | enum (`manual`) | ✅ |
| `created_by_manager_id` | UUID | ✅ |
| `channel` | enum (`call`, `expo`, `referral`, `other`) | ✅ |
| `notes` | text | ✅ |

Стадии: `new → qualified → converted_to_opportunity / closed_lost`.

### 5.4. Поведение при создании Company через лид

**Twenty не создаёт мастер-карточки клиентов сама.** Если приходит лид с ИНН клиента, которого нет в Twenty:

```
1. lookup в Postgres `entity_links` по ИНН → есть ли уже маппинг ИНН→Twenty Company?
   • если есть → используем существующую Company

2. если нет → 1c-bridge.lookup_by_inn(inn)
   • если 1С знает → 1c-bridge возвращает one_c_id + master данные
                  → создаём Twenty Company с status_1c='validated' + one_c_id
                  → entity_links: ИНН ↔ one_c_id ↔ twenty_company_id

3. если 1С не знает → создаём Twenty Company со status_1c='pending_1c_validation'
                   → entity_links без one_c_id (пока null)
                   → менеджер увидит badge "ожидает валидации в 1С"
                   → периодический job каждые N часов проверяет 1С на появление
                     этого ИНН и обновляет статус
```

Любой лид, дошедший до стадии **КП / сделка**, должен иметь Company со `status_1c='validated'` и заполненным `one_c_id`. Это **жёсткий gate** — невозможно создать КП на pending-карточке.

---

## 6. `1c-bridge` — выделенный сервис

### 6.1. Назначение

Единственная точка обмена с 1С. Ни Twenty, ни Tender Machine **не дёргают** API 1С напрямую. Все идут через `1c-bridge`.

### 6.2. MVP-функционал

```
GET  /1c/companies?modified_since=<ts>          → список изменённых клиентов
GET  /1c/companies/{inn}                         → один клиент по ИНН
GET  /1c/products?modified_since=<ts>            → список изменённых продуктов
GET  /1c/prices?valid_on=<date>                  → актуальный прайс
GET  /1c/deals/{deal_id}                         → статус сделки
GET  /1c/kp/{kp_id}                              → статус и содержимое КП

POST /1c/kp                                      → создать КП (с idempotency_key)
POST /1c/deals                                   → создать сделку (с idempotency_key)
POST /1c/companies                               → создать клиента
                                                   (только если pre-validated в Twenty)
```

### 6.3. Идемпотентность

Каждый POST принимает `Idempotency-Key` header (UUID, генерируется клиентом). Bridge хранит `(idempotency_key, response)` пары в Postgres `sync_runs` 24 часа. При повторном вызове с тем же ключом — возвращает кэшированный ответ, не дублирует операцию в 1С.

### 6.4. Конфликты данных

При sync клиента из 1С → Twenty:
- master-поля (ИНН, ОГРН, КПП, юридическое название) **перезаписываются** значениями из 1С;
- CRM-поля (заметки, задачи, комментарии менеджера) **не трогаются**;
- если в Twenty были изменения master-полей вручную — пишется `audit_event` с `action='conflict'`, оригинал затирается, менеджер получает task «проверьте — изменение потёрто 1С-синхронизацией».

### 6.5. Ошибки и retry

Для long-running операций 1С (создание КП занимает минуты):
- bridge возвращает `202 Accepted` + `task_id`;
- клиент опрашивает `GET /1c/tasks/{task_id}` или ждёт webhook;
- bridge пишет в `sync_runs.status` все переходы.

---

## 7. Cross-system identifiers

Для **каждой кросс-системной сущности** хранятся все её идентификаторы:

```sql
CREATE TABLE entity_links (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_id     UUID NOT NULL UNIQUE,        -- наш собственный stable ID
  entity_type     TEXT NOT NULL,               -- company | person | product | tender | lead | kp | deal
  one_c_id        TEXT,                        -- ID в 1С
  twenty_company_id   UUID,                    -- ID в Twenty (если применимо)
  twenty_person_id    UUID,
  twenty_lead_id      UUID,
  twenty_opportunity_id UUID,
  tenderland_id   TEXT,                        -- TL*
  inn             TEXT,                        -- ключ дедупа для company
  metadata        JSONB DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_links_one_c       ON entity_links(one_c_id) WHERE one_c_id IS NOT NULL;
CREATE INDEX idx_links_twenty_co   ON entity_links(twenty_company_id) WHERE twenty_company_id IS NOT NULL;
CREATE INDEX idx_links_twenty_lead ON entity_links(twenty_lead_id) WHERE twenty_lead_id IS NOT NULL;
CREATE INDEX idx_links_inn         ON entity_links(inn) WHERE inn IS NOT NULL;
CREATE INDEX idx_links_tl          ON entity_links(tenderland_id) WHERE tenderland_id IS NOT NULL;
CREATE INDEX idx_links_type        ON entity_links(entity_type);
```

`internal_id` — наш собственный stable UUID. Все события `audit_events`, `llm_runs`, `status_history`, `human_reviews` ссылаются именно на `internal_id`, **никогда** на ID отдельных систем. Это даёт нам устойчивость к миграциям (Twenty переезжает → Twenty IDs меняются → audit history не ломается).

---

## 8. Расширение Postgres-схемы

К документам из [`storage-architecture.md`](storage-architecture.md) (раздел 8) добавляем:

### 8.1. `audit_events` — append-only журнал всего

```sql
CREATE TABLE audit_events (
  id              BIGSERIAL PRIMARY KEY,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,                        -- ссылка на entity_links.internal_id
  entity_type     TEXT NOT NULL,
  actor_id        UUID,                        -- user.id или agent.id; NULL = system
  actor_type      TEXT NOT NULL,               -- user | agent | system | scheduled | external
  action          TEXT NOT NULL,               -- created | updated | status_changed | accessed | sync_in | sync_out | ai_decision | human_decision | conflict
  payload_diff    JSONB,                       -- {field: {from, to}}
  context         JSONB,                       -- {session_id, request_id, ...}
  ip_address      INET,
  user_agent      TEXT
);

CREATE INDEX idx_audit_internal_ts ON audit_events(internal_id, ts DESC);
CREATE INDEX idx_audit_actor_ts    ON audit_events(actor_id, ts DESC);
CREATE INDEX idx_audit_action      ON audit_events(action, ts DESC);

-- запрет UPDATE/DELETE на уровне БД
REVOKE UPDATE, DELETE ON audit_events FROM PUBLIC;
```

### 8.2. `llm_runs` — трассировка AI-решений

```sql
CREATE TABLE llm_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,                        -- к какой entity относится решение
  agent_id        TEXT NOT NULL,               -- tender_analyzer | kp_agent | ...
  task            TEXT NOT NULL,               -- classify_files | extract_specs | match_products | generate_kp_draft | ...

  model           TEXT NOT NULL,               -- claude-sonnet-4.5 | bge-m3 | ...
  provider        TEXT NOT NULL,               -- openrouter | anthropic | local
  prompt_version  TEXT NOT NULL,               -- v3.2 (трекаем версии промптов)

  input_refs      JSONB NOT NULL,              -- ссылки на input documents/chunks/data
  input_summary   TEXT,                        -- человекочитаемое описание

  output          JSONB NOT NULL,              -- результат
  explanation     TEXT,                        -- человекочитаемое объяснение
  confidence      NUMERIC(5,2),                -- 0..100

  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        NUMERIC(10, 6),
  latency_ms      INTEGER,

  fallback_chain  JSONB,                       -- [{model, error}, ...] если был fallback
  error           TEXT,                        -- если итоговая ошибка
  status          TEXT NOT NULL                -- success | error | partial
);

CREATE INDEX idx_llm_internal      ON llm_runs(internal_id);
CREATE INDEX idx_llm_agent_ts      ON llm_runs(agent_id, ts DESC);
CREATE INDEX idx_llm_task_ts       ON llm_runs(task, ts DESC);
```

**Жёсткое правило:** каждое AI-решение которое влияет на бизнес-исход (matched product, decision pass/review/fail, скоринг лида, генерация черновика КП) — **должно** иметь запись в `llm_runs` с **explanation** и **input_refs**. Без этого решение не публикуется.

### 8.3. `document_registry` — единый реестр файлов

`documents` из storage-architecture.md **переименовывается в** `document_registry` для соответствия терминологии заказчика. Содержимое то же, плюс одно поле:

```sql
ALTER TABLE document_registry ADD COLUMN internal_id UUID;
-- ссылка на entity_links.internal_id (тендер / клиент / лид)
CREATE INDEX idx_doc_registry_internal ON document_registry(internal_id);
```

Это позволит запросить «все документы по тендеру TL2530033598» через `entity_links → internal_id → document_registry`.

### 8.4. `sync_runs` и `sync_errors`

```sql
CREATE TABLE sync_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts_started      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ts_finished     TIMESTAMPTZ,
  service         TEXT NOT NULL,               -- 1c-bridge | tenderland-search | twenty-sync
  direction       TEXT NOT NULL,               -- in | out | bidirectional
  operation       TEXT NOT NULL,               -- import_companies | export_kp | search_tenders | ...
  idempotency_key TEXT UNIQUE,
  request_payload JSONB,
  response_payload JSONB,
  records_in      INTEGER,
  records_out     INTEGER,
  status          TEXT NOT NULL,               -- success | partial | failed | running
  error_summary   TEXT
);

CREATE INDEX idx_sync_service_ts  ON sync_runs(service, ts_started DESC);
CREATE INDEX idx_sync_status      ON sync_runs(status) WHERE status != 'success';

CREATE TABLE sync_errors (
  id              BIGSERIAL PRIMARY KEY,
  sync_run_id     UUID NOT NULL REFERENCES sync_runs(id),
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,                        -- если ошибка на конкретной сущности
  error_code      TEXT,
  error_message   TEXT NOT NULL,
  payload         JSONB,
  retry_count     INTEGER DEFAULT 0,
  resolved_at     TIMESTAMPTZ,
  resolved_by     UUID                         -- кто пометил resolved
);
```

### 8.5. `status_history` — история смены статусов

```sql
CREATE TABLE status_history (
  id              BIGSERIAL PRIMARY KEY,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID NOT NULL,
  entity_type     TEXT NOT NULL,               -- tender | lead | kp | deal
  field           TEXT NOT NULL,               -- status | analysis_status | ...
  status_from     TEXT,
  status_to       TEXT NOT NULL,
  changed_by      UUID,                        -- user или agent
  changed_by_type TEXT NOT NULL,               -- user | agent | system | external
  reason          TEXT,
  llm_run_id      UUID REFERENCES llm_runs(id) -- если статус сменил AI
);

CREATE INDEX idx_status_internal_ts ON status_history(internal_id, ts DESC);
```

### 8.6. `human_reviews` — ручные решения менеджера

```sql
CREATE TABLE human_reviews (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID NOT NULL,
  entity_type     TEXT NOT NULL,
  reviewer_id     UUID NOT NULL,               -- user.id
  decision        TEXT NOT NULL,               -- accept | reject | needs_clarification | escalate
  ai_decision     TEXT,                        -- что предложил AI (для расхождения metric)
  ai_run_id       UUID REFERENCES llm_runs(id),
  comment         TEXT,
  takes_ai_advice BOOLEAN                      -- accept = AI совет; reject ≠ AI совет
);

CREATE INDEX idx_reviews_internal     ON human_reviews(internal_id);
CREATE INDEX idx_reviews_reviewer_ts  ON human_reviews(reviewer_id, ts DESC);
```

**Метрика качества AI:** `% случаев где human takes_ai_advice = true`. Если падает ниже 70% — промпты или модель надо тюнить.

---

## 9. Trace для каждого тендерного лида

Полная цепочка прослеживается одним JOIN:

```
audit_events / llm_runs / sync_runs
       ▲
       │
       └── internal_id ────► entity_links ───► twenty_lead_id
                                          ───► one_c_id
                                          ───► tenderland_id
```

Конкретно для тендерного лида trace выглядит так:

```
search_run (Searcher запустился по теме) 
  → audit_events: action=search_started
  → tender (raw, найден в Tenderland)
       → audit_events: action=tender_discovered
       → document_registry: zip скачан
       → audit_events: action=docs_downloaded
       → tender_analyses (Analyzer Module 1)
            → llm_runs: classify_files (Haiku)
            → llm_runs: extract_specs (Sonnet) — explanation + confidence
            → audit_events: action=analysis_complete
       → tender_analyses (Analyzer Module 2)
            → llm_runs: match_products (Sonnet) — explanation + matched_score
            → audit_events: action=match_complete
       → crm_push
            → sync_runs: service=twenty-sync, op=create_lead
            → audit_events: action=lead_created_in_crm
            → entity_links: tenderland_id ↔ twenty_lead_id ↔ internal_id
       → human_review (менеджер в Twenty)
            → human_reviews: decision=accept, takes_ai_advice=true
            → audit_events: action=human_decided
            → status_history: status_from=unqualified, status_to=accepted
       → 1c-bridge (создание КП)
            → sync_runs: service=1c-bridge, op=create_kp
            → entity_links: + one_c_kp_id
            → audit_events: action=kp_created_in_1c
```

В UI (Twenty / админка Tender Machine) для каждого лида — кнопка «Trace» которая показывает эту цепочку как timeline.

---

## 10. AI-решения: explanation и проверяемость

Жёсткие требования для каждого AI-решения с бизнес-влиянием:

1. **Хранится `input_refs`** — какие именно документы / chunks / поля были на входе (ссылки в `document_registry`, не копии текста).
2. **Хранится `prompt_version`** — какой промпт использовался (для воспроизводимости при апгрейде).
3. **Хранится `model` + `provider`** — какой моделью.
4. **Хранится `explanation`** на естественном языке: «Я выбрал Memmert UN 55 потому что в ТЗ требуется температурный диапазон 30-300°C, объём 50-60л — наш UN 55 покрывает 30-300°C / 53л. По параметру X не проходим».
5. **Хранится `confidence`** (0-100) — численная самооценка.
6. **Хранится `fallback_chain`** если был fallback (Sonnet упал → Haiku → final result).

В UI **рядом с каждым AI-результатом** — иконка «(i)» которая раскрывает explanation + ссылки на источники. Менеджер видит «почему AI так решил» в один клик.

В отчётах **отдельные** колонки:
- AI decision (что предложил AI);
- Human decision (что решил менеджер);
- Final commercial outcome (что в 1С — выиграли / проиграли / отказ).

---

## 11. Backup & storage абстракция

Не привязываемся к конкретному провайдеру до выбора. В коде:

```python
# infra/lib/storage.py
class DocumentStorage(Protocol):
    def put(self, key: str, content: bytes, metadata: dict) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def list(self, prefix: str) -> list[str]: ...

class BackupStorage(Protocol):
    def backup(self, source_path: str, target_key: str) -> BackupHandle: ...
    def restore(self, target_key: str, dest_path: str) -> None: ...
    def list_backups(self, prefix: str) -> list[BackupHandle]: ...

class ArchiveStorage(Protocol):
    """Cold storage, write-once-read-rarely."""
    def archive(self, source_key: str, retention_days: int) -> ArchiveHandle: ...
```

Имплементации выбираются по env var:
- `STORAGE_DRIVER=minio` (production)
- `STORAGE_DRIVER=fs` (тесты)
- `STORAGE_DRIVER=s3-yandex` / `s3-aws` / `gdrive` (на выбор когда заказчик решит)

**Минимальная backup-стратегия с первого дня:**
- ежедневный `pg_dump` всех БД (gluvex_documents, twenty, mempalace, camunda) → `/opt/gluvex/backups/`
- ежедневный `mc mirror` MinIO → отдельный физический volume
- бэкап `/opt/gluvex/secrets/.env` в **vault** (не plaintext в репо!) — выберем bitwarden self-hosted / 1password / hashicorp vault
- бэкап конфигов (`stack/`, `infra/`) — уже в git
- **тест восстановления** раз в месяц — отдельный isolated VPS, восстановить, проверить smoke-тесты

---

## 12. MVP-порядок этапов (10 фаз)

| Этап | Что | Зависит от | Время |
|---|---|---|---|
| **1** | Базовая инфра: VPS + Postgres + Redis + Twenty + Caddy + Tender Machine skeleton | — | ✅ **сделано** (Phase 3) |
| **2** | `audit_events`, `document_registry`, `entity_links`, `sync_runs`, `status_history`, `human_reviews`, `llm_runs` schema **до** реализации сложного Analyzer | Этап 1 | 1 день |
| **3** | Импорт справочников из 1С через `1c-bridge`: клиенты, продукты, цены | Этап 2 + готовность 1С | 3-5 дней |
| **4** | 3 раздельные воронки лидов в Twenty: website/tender/manager + кастомные поля под каждую | Этап 2, 3 | 1 день (по структуре от заказчика) |
| **5** | Tenderland Searcher + импорт тендеров (по ARCHITECTURE раздел 6) | Этап 2 + TENDERLAND_API_KEY | 3 дня |
| **6** | CRM Pusher: создание `tender_lead` в Twenty + полный trace через `entity_links` | Этап 4, 5 | 2 дня |
| **7** | Analyzer Module 1 (extract only): парсинг ТЗ → `extracted_specs` без матчинга | Этап 5, 6 | 5 дней |
| **8** | Matcher: каталог 1С → matched products + decision pass/review/fail. **Все** AI-решения через `llm_runs` | Этап 3, 7 | 1 неделя |
| **9** | Создание КП/сделок в 1С через `1c-bridge`: при `accepted` лиде — auto-create draft КП | Этап 8 | 1 неделя |
| **10** | Дашборды (метрики качества AI: % takes_ai_advice), SLA-алерты, ролевые модели, тонкая настройка | Этап 9 + накопленные данные | по потребности |

---

## 13. Открытые вопросы

| # | Вопрос | Кому |
|---|---|---|
| Q1 | Структура полей в 1С: Контрагенты / Контакты / Номенклатура / Прайсы / КП / Сделки + типы | заказчик |
| Q2 | API 1С: REST? OData? собственный middleware? Web-сервис 1С? | заказчик |
| Q3 | Authentication для 1С API: токен / basic auth / mTLS? | заказчик |
| Q4 | Расписание sync 1С → Postgres: real-time webhook / polling каждый час / ночной batch? | заказчик + админ 1С |
| Q5 | OPENROUTER_API_KEY для LiteLLM (в `/opt/gluvex/secrets/.env`) | заказчик |
| Q6 | Vault для секретов — bitwarden / 1password / hashicorp vault / иное? | заказчик |
| Q7 | Backup off-site provider — Yandex / Backblaze B2 / S3 / Google Workspace? | заказчик (через 6 мес) |
| Q8 | Mock 1С на этапе 3 — есть ли тестовая БД 1С для разработки `1c-bridge`? | заказчик / админ 1С |

---

## 14. Главное правило для агента

При любом архитектурном решении проверяй:

1. **Не дублирую ли я мастер-данные?** Если да — кто master? Только один.
2. **Не пишу ли я в 1С напрямую?** Только через `1c-bridge`.
3. **Будет ли trace?** Если действие AI или человека влияет на бизнес-результат — пишем `audit_events`. Если AI — ещё `llm_runs`.
4. **Идемпотентно ли?** Повторный запуск не должен ломать состояние.
5. **Можно ли восстановить из master?** Knowledge layer (Qdrant + MemPalace) пересобирается из 1С + Postgres + MinIO. Не используем как источник истины.
6. **Status flow явен?** Если меняется статус — `status_history` запись.
7. **default-deny на retrieval?** Агент видит только разрешённые источники для своей роли.

Если хоть один пункт нарушается — переархитектурим, не идём дальше.

---

_Документ верхнего уровня. Любые правки `storage-architecture.md` или `ARCHITECTURE.md` сначала проверяются на соответствие этому документу._
