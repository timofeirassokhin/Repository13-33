# Gluvex — архитектура хранения, индексации и retrieval

**Версия:** 1.1
**Дата:** 2026-05-10
**Статус:** утверждено заказчиком
**Иерархия документов:**
1. ⭐ [`master-data-architecture.md`](master-data-architecture.md) — **верхнеуровневый** документ: 1С как master, 5 контуров, master-system table, аудит, sync. **Читать первым.**
2. **(этот)** `storage-architecture.md` — слой хранения, идентификаторов, retrieval policy
3. [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — Tender Pipeline (Searcher / Analyzer / CRM Pusher)

> Любое решение в этом документе **подчинено** `master-data-architecture.md`. Если есть конфликт — побеждает master-data-architecture.

> ⚠️ **Терминологическое уточнение (с v1.1):** таблица `documents` переименована в `document_registry` для соответствия терминологии заказчика. Содержимое не изменилось.

---

## 1. Цель документа

Один источник истины по тому, **где** и **как** Gluvex хранит:
- знания (документы, прайсы, брошюры, SOP, методички, ТЗ);
- состояние (CRM-сущности, тендеры, процессы);
- ссылки между ними;
- историю изменений и аппрувов.

И по тому, **кто из агентов** имеет право брать данные из каких источников.

Адресован:
- агентам/разработчикам — как чек-лист реализации;
- заказчику — для ревью архитектуры до того, как мы зафиксируем её в коде.

---

## 2. Принципы

1. **Разделение слоёв ответственности.** Каждое хранилище отвечает за один слой. Дублирование = риск рассинхрона.
2. **Source of truth — Postgres.** Если данные есть в трёх местах, истиной считается то, что в Postgres. Остальное — производное.
3. **Оригиналы в MinIO.** Postgres не хранит файлы (BLOB), только метаданные и ссылки. Vector store не хранит файлы — только chunks и embeddings.
4. **Идентифицируемость.** Каждый ответ агента отслеживается до конкретного документа, версии, чанка. «Агент сказал X на основе документа Y версии Z, чанк W».
5. **Версионирование с истечением.** Прайс не «удалён» — он `archive` или `expired`. Старые версии остаются для audit trail и ретроспективного анализа.
6. **Default-deny retrieval.** Агент видит **только то, что в его whitelist'е**. Не «всё кроме чёрного списка».
7. **Approvals на бизнес-критичных операциях.** Изменение прайса, шаблона КП, скидочного правила, статуса документа `actual ↔ archive` — через явный approval (Camunda task → менеджер).
8. **Audit log с первого дня.** Все изменения мастер-данных пишутся в `document_events` (append-only).
9. **Multi-tenant ready.** Даже сейчас одна компания — схема и идентификаторы поддерживают несколько `tenant_id` на будущее.
10. **Hybrid search.** Семантический + keyword (FTS) — объединяются через RRF. Чисто semantic фейлится на артикулах и моделях.

---

## 3. Слои стека

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           АГЕНТЫ И КЛИЕНТЫ                                    │
│   Tender Analyzer  •  Product Manager  •  KP Agent  •  Email Agent  •  UI    │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
   │  RETRIEVAL API  │  │ APPROVAL API │  │  CRM (Twenty)    │
   │  hybrid search  │  │  Camunda 7   │  │  Companies/Leads │
   │  + policy check │  │  BPMN tasks  │  │  Opportunities   │
   └────────┬────────┘  └──────┬───────┘  └────────┬─────────┘
            │                   │                   │
   ┌────────┴───────────────────┴───────────────────┴─────────────────┐
   │                       АГЕНТНЫЙ СЛОЙ                              │
   │   MemPalace — рабочий контекст, drawers, wings, агентная память  │
   └────────┬─────────────────────────────────────────────────────────┘
            │
   ┌────────┴───────────────┬─────────────────────┬─────────────────┐
   ▼                        ▼                     ▼                 ▼
┌────────────┐      ┌──────────────┐      ┌──────────────┐  ┌────────────┐
│ POSTGRES   │      │   QDRANT     │      │    MINIO     │  │  CAMUNDA   │
│ source of  │      │  vector      │      │  оригиналы   │  │  workflow  │
│ truth      │◄─────│  index       │      │  файлов      │  │  engine    │
│            │      │  (embeddings │      │              │  │            │
│ • documents│      │   + chunks)  │      │ raw-documents│  │ BPMN       │
│ • events   │      │              │      │ commercial   │  │ DMN        │
│ • Twenty   │      │              │      │ tenders      │  │ User Tasks │
│   schema   │      │              │      │ brochures    │  │            │
│ • Camunda  │      │              │      │ sop          │  │            │
│   schema   │      │              │      │ archive      │  │            │
└────────────┘      └──────────────┘      └──────────────┘  └────────────┘
                                                                  │
                          ┌───────────────────────────────────────┘
                          ▼
                  ┌────────────────────────┐
                  │  LITELLM + LOGS        │
                  │  модели + трассировка  │
                  │  стоимости и качества  │
                  └────────────────────────┘
```

| Слой | Что хранит | Размер | Бэкап |
|---|---|---|---|
| **Postgres 16** | мастер-данные: `documents`, `chunks`, `events`, `agent_policies`, Twenty schema, Camunda schema | ~10–50 GB через год | nightly pg_dump → `/opt/gluvex/backups/` (есть) |
| **MinIO** | оригиналы файлов всех типов, разнесены по buckets | ~100–500 GB через год | nightly `mc mirror` на отдельный диск, off-site через 6 мес. |
| **Qdrant** | embeddings + chunks_metadata, ссылки на `chunks.id` в Postgres | ~5–30 GB через год | nightly snapshot в MinIO bucket `qdrant-snapshots` |
| **MemPalace** | рабочий контекст агентов: drawers/wings/timeline, ссылки на `documents.id` | ~1–10 GB | nightly pg_dump (если PG-backed) или собственный snapshot |
| **Camunda 7 (Postgres)** | BPMN-определения, instances, tasks, history | ~1–5 GB | nightly pg_dump |
| **LiteLLM logs** | request/response, токены, стоимость, latency | ~5–20 GB | в Postgres → попадает в общий dump |
| **Twenty (Postgres)** | CRM-сущности | ~1–10 GB | уже бэкапим (cron @ 03:00) |

---

## 4. Идентификаторы и метаданные

### 4.1. Универсальная схема ID

Каждый объект знаний/документ имеет следующий набор:

```yaml
# обязательные
document_id:    UUID       # глобальный уникальный (UUIDv7 для сортируемости)
source_id:      string     # ID в источнике: 1С code, tender_id TL*, GoogleDrive fileId
source_type:    enum       # 1c_supplier | tenderland | manual_upload | gdrive | email_attachment
tenant_id:      UUID       # для multi-tenancy (на старте: один tenant Gluvex)
content_hash:   sha256     # хеш бинарника файла
content_type:   string     # MIME: application/pdf, application/vnd.openxmlformats…

# происхождение
created_at:     timestamp
updated_at:     timestamp
owner:          UUID       # ссылка на user.id (кто загрузил/создал)

# классификация
document_type:  enum       # brochure | price | sop | tz | offer | contract | methodology | brand_book | other
project_id:     UUID|null  # к какому проекту относится (опционально)
language:       enum       # ru | en | mixed | auto

# доступ и жизненный цикл
status:         enum       # draft | pending_review | actual | archive | forbidden | expired
access_level:   enum       # public | internal | confidential | restricted
valid_from:     date|null  # для прайсов: с какой даты действует
valid_until:    date|null  # до какой
supersedes_id:  UUID|null  # ссылка на предыдущую версию (chain версий)
is_pii:         boolean    # содержит ли персданные

# индексация
indexed_at:     timestamp|null  # когда последний раз прогнали через chunker+embedder
embedding_model: string         # какой моделью эмбеддили (bge-m3, e5-large, ...)
chunk_count:    integer
ocr_applied:    boolean         # применялся ли OCR при индексации
```

### 4.2. Chunk-level идентификаторы

```yaml
chunk_id:         UUID
document_id:      UUID FK
version_id:       UUID            # версия документа в момент эмбеддинга
chunk_index:      integer         # порядковый номер в документе
chunk_text:       text            # сам текст
chunk_hash:       sha256          # для dedup и инвалидации
embedding:        vector(1024)    # в Qdrant
embedding_model:  string
created_at:       timestamp
```

### 4.3. Привязка к ответам агента

Каждый retrieval-event (агент сделал поиск) пишется в `retrieval_log`:

```yaml
retrieval_id:     UUID
agent_id:         enum    # tender_analyzer | product_manager | kp_agent | email_agent
session_id:       UUID    # сессия агента (например, обработка одного тендера)
query:            text
hits:             [        # массив попаданий
  {chunk_id, document_id, version_id, score, retrieval_method}
]
allowed_sources:  [enum]  # какие document_type были разрешены этому агенту в этом запросе
created_at:       timestamp
```

При ответе агент **обязан цитировать** `document_id` + `version_id` + `chunk_id` из retrieval_log. Это даёт полную трассируемость "Я взял из брошюры X (версия Y, чанк Z)".

---

## 5. Версионирование знаний

### 5.1. Жизненный цикл документа

```
                              ┌─────────────────────────────────────┐
   upload                     ▼                                     │
   ──────► [draft] ───review──► [pending_review] ───approve──► [actual]
                                                                     │
                                                              expires │
                                                              (date)  │
                                                                     ▼
                                                              [expired]
                                                                     │
   manual archive (заменён  ◄──── replaces ────new version uploaded  │
   новой версией)                                                    │
                                                                     ▼
                                                              [archive]
                                                                     │
                                                              отозван производителем
                                                              / запрещён к использованию
                                                                     ▼
                                                              [forbidden]
```

### 5.2. Семантика статусов

| Status | Кто видит | Кто использует | Можно ли цитировать клиенту |
|---|---|---|---|
| `draft` | только автор | никто | ❌ |
| `pending_review` | автор + аппрувер | никто | ❌ |
| `actual` | все агенты | все по retrieval_policy | ✅ — единственный валидный для текущих КП |
| `archive` | агенты с пометкой `historical_ok` | только аналитика, ретроспектива | ⚠️ только если клиент явно ссылается на эту версию |
| `expired` | агенты с пометкой `historical_ok` | никто (автоматически архивируется по `valid_until`) | ❌ |
| `forbidden` | админ | **никто** — агент должен **активно избегать** | ❌ + триггер к замене |

### 5.3. Цепочка версий

`supersedes_id` создаёт цепочку: новая версия указывает на старую. Запрос «дай актуальную версию документа X» = найти `head` цепочки со `status='actual'`.

Для прайсов с `valid_from`/`valid_until` — несколько `actual` версий могут сосуществовать (Q3-прайс действует с 1 июля по 30 сентября, Q4-прайс — с 1 октября). Агент при retrieval указывает date context и выбирает подходящую.

---

## 6. Retrieval policy

### 6.1. Принцип default-deny

Каждый агент имеет `agent_policy` запись со списком **разрешённых** `document_type` × `status` пар. Всё остальное — недоступно.

```yaml
# тендерный аналитик — оценка ТЗ
agent_id: tender_analyzer
allow:
  - {document_type: tz,            status: [actual]}
  - {document_type: sop,           status: [actual]}
  - {document_type: methodology,   status: [actual]}
  - {document_type: brochure,      status: [actual]}        # для матчинга
  - {document_type: client_request, status: [actual, archive]}  # история запросов клиента
deny_explicit:  # переопределение даже если бы попало под allow
  - {access_level: restricted}
historical_ok: false  # archive/expired видны только если в allow явно

# продакт-менеджер — конфигуратор оборудования
agent_id: product_manager
allow:
  - {document_type: brochure,      status: [actual]}
  - {document_type: price,         status: [actual]}
  - {document_type: methodology,   status: [actual]}
  - {document_type: configurator,  status: [actual]}
  - {document_type: compatibility, status: [actual]}

# агент КП — генерация коммерческого предложения
agent_id: kp_agent
allow:
  - {document_type: kp_template,   status: [actual]}
  - {document_type: price,         status: [actual]}
  - {document_type: discount_rule, status: [actual]}
  - {document_type: brochure,      status: [actual]}
  - {document_type: brand_book,    status: [actual]}

# email-агент — переписка с клиентом
agent_id: email_agent
allow:
  - {document_type: email_thread,  status: [actual, archive]}  # вся история
  - {document_type: kp_template,   status: [actual]}
  - {document_type: crm_notes,     status: [actual]}
deny_explicit:
  - {is_pii: true, scope: cross_customer}  # email-агент не видит PII других клиентов
```

### 6.2. Реализация в `Retrieval API`

```python
def retrieve(agent_id, query, session_context):
    policy = load_policy(agent_id)
    allowed_filter = build_filter(policy)            # SQL/Qdrant filter
    
    # hybrid search: semantic + FTS, объединение через RRF
    semantic_hits = qdrant.search(query, filter=allowed_filter, top_k=20)
    keyword_hits  = postgres_fts.search(query, filter=allowed_filter, top_k=20)
    fused_hits    = reciprocal_rank_fusion(semantic_hits, keyword_hits, k=60)
    
    log_retrieval(agent_id, session_context, query, fused_hits, policy.allow)
    return fused_hits[:policy.max_results]
```

Каждый retrieval **логируется** в `retrieval_log` с указанием `policy.allow` — для аудита «не взял ли агент случайно archive вместо actual».

---

## 7. MinIO buckets

### 7.1. Структура

```
minio://gluvex/
├── raw-documents/          # raw uploads до классификации (короткоживущий staging)
├── product-brochures/      # брошюры производителей по приборам
├── prices/                 # прайс-листы (с valid_from/valid_until в metadata)
├── kp-templates/           # шаблоны коммерческих предложений
├── kp-generated/           # сгенерированные КП по клиентам (read-only архив)
├── tenders/                # тендерная документация (zip-архивы из Tenderland)
│   └── unpacked/           # распакованные ТЗ
├── sop/                    # внутренние SOP, регламенты, инструкции
├── methodologies/          # клиентские методики, прислонные методические указания
├── client-files/           # файлы конкретных клиентов
│   └── <inn>/              # партиционирование по ИНН
├── archive/                # архивные версии (вытесненные, expired)
├── qdrant-snapshots/       # snapshots Qdrant для backup
├── postgres-backups/       # nightly pg_dumps (опционально, помимо локальных)
└── audit-exports/          # выгрузки audit log по запросу регулятора/аудитора
```

### 7.2. Object key convention

```
<bucket>/<tenant_id>/<year>/<month>/<document_id>__<slug>.<ext>

Пример:
product-brochures/gluvex/2026/05/0193b8a4-...__memmert-un55-en.pdf
prices/gluvex/2026/Q3/0193b8b1-...__analytical-gluvex-q3-2026.xlsx
tenders/gluvex/2026/05/0193b8c2-...__TL2530033598-postavka-termostata.zip
```

### 7.3. Lifecycle и encryption

- **Server-Side Encryption SSE-S3** включена на всех buckets с первого дня (master key в MinIO config, бэкапим отдельно).
- **Versioning** включён на `prices`, `kp-templates`, `sop`, `methodologies` — там где история критична.
- **Object Lock (governance mode)** на `kp-generated` и `audit-exports` — нельзя удалить ранее года.
- **Lifecycle rule:** `raw-documents` чистится через 30 дней (это staging, не источник истины).
- **Бэкап MinIO:** `mc mirror` на отдельный физический диск ежедневно. Через 6 месяцев — off-site (Yandex Object Storage / Backblaze B2).

---

## 8. Postgres-схема `documents` (DDL skeleton)

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- для fuzzy match на title
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector (опционально, если будем хранить ANN-индекс рядом)

-- =====================================================================
CREATE TYPE document_status AS ENUM (
  'draft', 'pending_review', 'actual', 'archive', 'forbidden', 'expired'
);
CREATE TYPE document_type_t AS ENUM (
  'brochure', 'price', 'sop', 'tz', 'offer', 'kp_template', 'kp_generated',
  'contract', 'methodology', 'brand_book', 'email_thread', 'crm_notes',
  'configurator', 'compatibility', 'discount_rule', 'client_request', 'other'
);
CREATE TYPE access_level_t AS ENUM ('public', 'internal', 'confidential', 'restricted');
CREATE TYPE source_type_t AS ENUM (
  '1c_supplier', '1c_export', 'tenderland', 'manual_upload', 'gdrive',
  'email_attachment', 'webhook', 'agent_generated'
);

-- =====================================================================
-- основная таблица документов
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL,
  source_id       TEXT,
  source_type     source_type_t NOT NULL,

  bucket          TEXT NOT NULL,
  object_key      TEXT NOT NULL,
  filename        TEXT NOT NULL,
  content_type    TEXT NOT NULL,
  content_hash    BYTEA NOT NULL,         -- sha256 raw bytes
  size_bytes      BIGINT,

  document_type   document_type_t NOT NULL,
  language        TEXT,                   -- ru / en / mixed / auto
  project_id      UUID,
  is_pii          BOOLEAN NOT NULL DEFAULT false,

  status          document_status NOT NULL DEFAULT 'draft',
  access_level    access_level_t NOT NULL DEFAULT 'internal',
  valid_from      DATE,
  valid_until     DATE,
  supersedes_id   UUID REFERENCES documents(id),

  indexed_at      TIMESTAMPTZ,
  embedding_model TEXT,
  chunk_count     INTEGER,
  ocr_applied     BOOLEAN NOT NULL DEFAULT false,

  metadata        JSONB NOT NULL DEFAULT '{}',  -- произвольные доп. поля

  owner_id        UUID NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (tenant_id, content_hash)        -- автоматический dedup при upload
);

CREATE INDEX idx_documents_tenant_status   ON documents(tenant_id, status);
CREATE INDEX idx_documents_type            ON documents(tenant_id, document_type);
CREATE INDEX idx_documents_source          ON documents(source_type, source_id);
CREATE INDEX idx_documents_validity        ON documents(valid_from, valid_until)
    WHERE status = 'actual';
CREATE INDEX idx_documents_filename_trgm   ON documents USING GIN (filename gin_trgm_ops);

-- =====================================================================
-- чанки (для гибридного поиска)
CREATE TABLE document_chunks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_id      UUID NOT NULL,           -- хеш состава: content_hash + chunker_config + embedding_model
  chunk_index     INTEGER NOT NULL,
  chunk_text      TEXT NOT NULL,
  chunk_hash      BYTEA NOT NULL,
  embedding_model TEXT NOT NULL,
  -- ВАЖНО: сам vector живёт в Qdrant, а не здесь — таблица служит чтобы находить chunk по тексту/FTS
  tsv             tsvector GENERATED ALWAYS AS (to_tsvector('russian', chunk_text)) STORED,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chunks_document       ON document_chunks(document_id);
CREATE INDEX idx_chunks_version        ON document_chunks(version_id);
CREATE INDEX idx_chunks_fts            ON document_chunks USING GIN (tsv);

-- =====================================================================
-- audit log (append-only, не редактируется и не удаляется)
CREATE TABLE document_events (
  id              BIGSERIAL PRIMARY KEY,
  document_id     UUID NOT NULL,             -- без FK, чтобы пережить удаление документа
  tenant_id       UUID NOT NULL,
  actor_id        UUID,                      -- кто сделал; NULL = system
  actor_type      TEXT NOT NULL,             -- user | agent | system | scheduled
  action          TEXT NOT NULL,             -- created | updated | status_changed | accessed | deleted
  payload_diff    JSONB,                     -- diff: {field: {from, to}}
  retrieved_by    UUID,                      -- ссылка на retrieval_log если action=accessed
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  ip_address      INET,
  user_agent      TEXT
);

CREATE INDEX idx_events_doc_ts   ON document_events(document_id, ts DESC);
CREATE INDEX idx_events_actor_ts ON document_events(actor_id, ts DESC);

-- запрет UPDATE/DELETE на уровне БД
REVOKE UPDATE, DELETE ON document_events FROM PUBLIC;

-- =====================================================================
-- retrieval log (тоже append-only)
CREATE TABLE retrieval_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id        TEXT NOT NULL,
  session_id      UUID,
  query           TEXT NOT NULL,
  query_embedding_model TEXT,
  hits            JSONB NOT NULL,            -- [{chunk_id, document_id, version_id, score, retrieval_method}]
  allowed_filter  JSONB NOT NULL,            -- что было разрешено для этого retrieval
  result_count    INTEGER NOT NULL,
  duration_ms     INTEGER,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_retrieval_agent_ts ON retrieval_log(agent_id, ts DESC);
CREATE INDEX idx_retrieval_session  ON retrieval_log(session_id) WHERE session_id IS NOT NULL;

-- =====================================================================
-- agent policies
CREATE TABLE agent_policies (
  agent_id        TEXT PRIMARY KEY,
  allow_rules     JSONB NOT NULL,            -- [{document_type, status: []}]
  deny_explicit   JSONB,
  historical_ok   BOOLEAN DEFAULT false,
  max_results     INTEGER DEFAULT 10,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 9. Vector storage: границы Qdrant и MemPalace

Вопрос: зачем оба, а не один? Ответ — **разные роли**.

### Qdrant — низкоуровневое хранилище эмбеддингов

- Хранит: vectors + chunk metadata (минимум для filter'а: `tenant_id`, `document_type`, `status`, `valid_from`, `valid_until`, `access_level`, `language`, `is_pii`).
- Не знает про агентов, сессии, контекст.
- Каждый chunk имеет payload `{document_id, chunk_id, version_id}` — ссылки в Postgres.
- Один Qdrant collection per `(tenant_id, embedding_model)`.

### MemPalace — агентный слой памяти

- Хранит: drawer'ы (рабочие заметки), wing'и (домены знаний), timeline событий, агентные контексты длинных задач.
- Использует Qdrant **как backend** для semantic search внутри своих drawer'ов (через MemPalace-specific Qdrant collection, отдельную от documents collection).
- Знает агента, сессию, что происходит в long-running задаче.
- Решает вопросы «что я уже видел в этой сессии», «что было в прошлый раз», «связан ли этот тендер с тем клиентом».
- НЕ хранит оригиналы документов — только ссылки `documents.id` или собственные drawer-записи.

### Синхронизация и трассировка

```
upload → MinIO (object_key)
       → Postgres documents (id, content_hash, status='draft')
       → ingestion pipeline:
           parse → chunk → embed
           ↓
           Postgres document_chunks (id, version_id, chunk_text, tsv)
           Qdrant points  (vector, payload={document_id, chunk_id, version_id, ...})
           ↓
           Postgres documents.indexed_at = now(), chunk_count = N

retrieval (агент):
   Retrieval API → Qdrant + Postgres FTS → fused hits
                 → Postgres retrieval_log (allowed_filter + hits)
                 → результаты возвращаются агенту
                 → агент при ответе цитирует {document_id, chunk_id, version_id}
```

Каждый chunk в Qdrant **обязан иметь** `version_id` в payload. При обновлении документа (новая версия = новый content_hash) — старые точки в Qdrant `tagged as superseded` (не удаляются сразу, чтобы archive-агенты могли видеть). Через N дней (default 90) — выпиливаются.

---

## 10. Workflow и Approval — Camunda Platform 7 CE

### 10.1. Что Camunda даёт нам

- **BPMN 2.0** — процессы рисуются визуально в Camunda Modeler (десктопное приложение) или в bpmn.io editor. Менеджеры могут **читать процесс**.
- **User Tasks** — задачи на конкретного человека/группу. UI Tasklist приходит в комплекте.
- **DMN** — Decision Model Notation. Например, скоринг тендера или правила скидок — описываются таблицей решений, не кодом.
- **REST API** — старт процесса, завершение задачи, query — всё через HTTP. Агенты дёргают API.
- **Postgres backend** — всё состояние процессов в Postgres (отдельная база `camunda` в нашем общем инстансе).

### 10.2. Стартовые процессы (для CRM, расширяем потом)

```bpmn
─────────── document_approval ───────────
  upload draft
       ↓
  → User Task "Review by owner"
       ↓ approved              ↓ rejected
       ↓                       ↓
  status → actual         status → draft
  superseded → archive    notify uploader

─────────── price_change ───────────
  proposed price change (from agent or manager)
       ↓
  DMN: автоматическое решение
    if discount > 15%  → escalate to head of sales
    if discount > 30%  → escalate to CEO
    else               → manager approval
       ↓
  → User Task assigned by DMN result
       ↓
  on approve: documents.status='actual' для new price
              documents.status='archive' для old price

─────────── tender_routing (Phase 6 в ARCHITECTURE) ───────────
  tender analyzed → score X, decision Y
       ↓
  if decision == 'pass'    → auto: create CRM Lead
  if decision == 'review'  → User Task to analyst
  if decision == 'fail'    → archive

─────────── kp_generation ───────────
  CRM lead promoted to "in_proposal"
       ↓
  agent generates КП draft (kp_generated bucket)
       ↓
  → User Task "Review KP" → manager
       ↓ approved
       ↓
  send to client (email-agent), log to email_thread
```

### 10.3. Будущее расширение — ERP-on-agents

Camunda — это плацдарм. По мере роста добавим процессы:
- финансы: оплата счёта → согласование с финансовой → проводка в 1С;
- логистика: заказ у поставщика → отгрузка → таможня → склад;
- HR: найм → отчёт на испытательном → перевод в штат;
- …

Каждый процесс — отдельный BPMN-файл в `infra/camunda/processes/*.bpmn`. Деплоятся через REST API при старте контейнера. Изменения — через PR в git.

### 10.4. Роли и Tasklist UI

- `https://bpm.gluvex.com` — Camunda Operate + Tasklist (после публикации DNS).
- Группы: `sales-managers`, `sales-head`, `finance`, `analysts`, `ceo`.
- Юзеры синхронизируются из Twenty (через периодический job, чтобы не дублировать управление пользователями).

---

## 11. Audit log и Approval — итеративная реализация

### Сейчас (Phase 3.5):
- `document_events` таблица с триггерами на `documents` — пишутся все INSERT/UPDATE/DELETE автоматически.
- Подписчик на retrieval_log → копирует событие `accessed` в `document_events` для каждого хита.

### Phase 3.8 (через 2 недели):
- BPMN-процесс `document_approval` deploy в Camunda.
- При попытке поменять `documents.status` с `draft` на `actual` — Postgres trigger проверяет: есть ли активный approval task в Camunda → если нет, отклоняет.
- Менеджер в Camunda Tasklist видит «approve / reject» — после approve, Camunda дёргает PATCH /documents/{id} → status меняется → trigger сейчас разрешает потому что approval pass'нул.

### Phase 4+ (по мере роста):
- DMN-таблицы для скидок, скоринга, эскалаций.
- Roll-out на финансы, логистику.

---

## 12. Hybrid search — почему оба

Чисто semantic поиск **проигрывает** на трёх классах запросов в торговой нише:

| Класс запроса | Семантика | FTS | Итог |
|---|---|---|---|
| «сушильный шкаф 53 литра» | ✅ хорошо | ⚠️ может пропустить «термошкаф» | **семантика** |
| «Memmert UN 55» (модель) | ⚠️ путает с UN 110, UN 75 | ✅ exact match | **FTS** |
| «L-9000-AC-12V» (артикул) | ❌ embedding не различит | ✅ exact match | **FTS** |
| «приборы для определения тяжёлых металлов в воде» | ✅ хорошо | ⚠️ нужны точные слова | **семантика** |

Решение — **Reciprocal Rank Fusion (RRF)** с k=60 (стандартный гиперпараметр):

```python
def rrf(rankings, k=60):
    """rankings: list of [doc_id, ...] from each retrieval method."""
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)
    return sorted(scores.items(), key=lambda x: -x[1])
```

Дёшево, без ML, эффективно. Можно потом надстроить cross-encoder reranker (например, bge-reranker-large) когда наберётся датасет «правильных» retrieval'ов.

---

## 13. Ingestion pipeline

```
1. UPLOAD
   • Multipart upload → MinIO (bucket=raw-documents, key пока временный)
   • Compute sha256
   • Если такой hash уже есть в documents (UNIQUE constraint) → return existing.id, не дублируем

2. CLASSIFY (auto + manual)
   • MIME detect
   • Heuristic classification по filename + первым 1500 символам (Haiku через LiteLLM)
   • Manual override через UI: пользователь подтверждает/правит document_type, project_id, valid_from/until
   • Move object: raw-documents → правильный bucket (atomic copy + delete)

3. PARSE
   • PDF text-layer (pdfplumber)
   • PDF без text layer → OCR (Tesseract rus+eng → Yandex Vision как fallback на сложном)
   • DOCX → python-docx (включая таблицы)
   • XLSX → openpyxl (по листам, по cells)
   • HTML/MD → trafilatura (чистка boilerplate)
   • Output: text + structural metadata (headings, tables)

4. CHUNK
   • Semantic chunker (LangChain RecursiveCharacterTextSplitter с semantic boundaries)
   • Размер chunk: 512–1024 токенов с overlap 64
   • Для таблиц — отдельные chunks с заголовками: "<таблица: характеристика прибора X>\n<rows>"

5. EMBED
   • Default: bge-m3 (multilingual, хорош на русском + английском)
   • Через LiteLLM endpoint (если есть прокси для embedding) или прямо локально через transformers
   • Задача в ARQ queue, чтобы не блокировать upload-API

6. STORE
   • document_chunks insert (text + tsv + version_id)
   • Qdrant upsert (vector + payload)
   • documents.indexed_at = now()
   • document_events: event=indexed

7. NOTIFY
   • MemPalace получает webhook: новый документ {document_id, document_type}
   • MemPalace в нужном wing'е создаёт drawer-ссылку
   • Camunda — если document требует approval — стартует BPMN процесс document_approval
```

### Failure modes

| Шаг | Что если упало |
|---|---|
| Upload | client retry (S3 multipart resume) |
| Classify | документ остаётся `status=pending_review`, ждёт ручной классификации |
| Parse | document_events пишет error, документ помечается `status=draft` + `metadata.parse_error=...` |
| OCR | retry до 3 раз, потом fallback Yandex Vision |
| Embed | retry с экспоненциальным backoff, при 5+ failures — admin alert |
| Qdrant insert | если Qdrant down → ARQ retry с backoff, документ остаётся `indexed_at=null` |

---

## 14. Стек на сервере — что добавляем

К текущему стеку (`caddy + twenty + litellm + postgres + redis`) добавляем:

```yaml
# в docker-compose.yml gluvex stack:

services:
  # БД для нового слоя — отдельная от Twenty чтобы можно было независимо бэкапить/мигрировать
  app-db:
    image: postgres:16
    # databases: gluvex_documents, mempalace, camunda

  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]   # 9001 — admin console
    volumes: [minio_data:/data, minio_backup:/backup]
    environment:
      MINIO_ROOT_USER: ...
      MINIO_ROOT_PASSWORD: ...

  qdrant:
    image: qdrant/qdrant:latest
    volumes: [qdrant_data:/qdrant/storage]

  mempalace:
    # Reuse from infra/mempalace/ (13-33 stack)
    # adapt config: backend Qdrant вместо Chroma, новая БД mempalace
    image: ...

  camunda:
    image: camunda/camunda-bpm-platform:run-7.21.0    # community edition, run distribution
    environment:
      DB_DRIVER: org.postgresql.Driver
      DB_URL: jdbc:postgresql://app-db:5432/camunda
      DB_USERNAME: camunda
      DB_PASSWORD: ${CAMUNDA_PG_PASSWORD}

  ingestion-worker:
    image: gluvex/ingestion:latest
    # ARQ workers под parsing/chunking/embedding tasks
```

### DNS — что добавить

| Поддомен | Назначение | Видимость |
|---|---|---|
| `bpm.gluvex.com` | Camunda Tasklist + Operate UI | публично через Caddy |
| `files.gluvex.com` | MinIO Admin Console | публично через Caddy (с basic auth) |
| `qdrant.gluvex.com` | Qdrant API | НЕ публично, только внутри docker network |
| `mempalace.gluvex.com` | MemPalace UI/API | публично через Caddy |
| `tenders.gluvex.com` | tender pipeline UI | публично через Caddy |

---

## 15. Поэтапный план

| Phase | Что | Зависит от | Время |
|---|---|---|---|
| **3.5** | MinIO + Postgres `documents`/`document_events`/`retrieval_log` schema + upload API + sha256 dedup + базовый audit | — | 1–2 дня |
| **3.6** | Qdrant + ingestion pipeline (parse/chunk/embed/OCR) + ARQ workers | 3.5 | 2–3 дня |
| **3.7** | Retrieval API + `agent_policies` + RRF hybrid search | 3.6 | 1–2 дня |
| **3.8** | Camunda 7 CE + базовые BPMN: document_approval, price_change | 3.5 + Twenty | 2 дня |
| **3.9** | MemPalace на Qdrant backend + sync с documents | 3.6, 3.7 | 1–2 дня |
| **4** | Twenty schema под 1С (когда заказчик пришлёт структуру) | заказчик | 1 день |
| **5** | Tender Pipeline: Searcher + Analyzer Module 1 (см. ARCHITECTURE.md) | 3.6, 3.7 | 1 неделя |
| **6** | Tender Pipeline: каталог продукции импорт → Postgres + Qdrant | 3.6, 5 | 3 дня |
| **7** | Tender Pipeline: Analyzer Module 2 (matcher) + CRM Pusher | 4, 6 | 1 неделя |
| **8** | KP Agent + Email Agent (используя retrieval policy 3.7) | 3.7 | 2 недели |
| **9** | DMN-правила в Camunda для скидок и скоринга | 3.8 | 1 неделя |
| **позже** | ERP-роллаут: финансы, логистика, HR | по мере роста | — |

---

## 16. Открытые вопросы

| # | Вопрос | Кому |
|---|---|---|
| Q1 | Структура полей Twenty Company/Person/Lead/Deal **зеркальна 1С** — заказчик готовит | заказчик |
| Q2 | OPENROUTER_API_KEY для LiteLLM | заказчик |
| Q3 | Где брать embedding модель — локальный bge-m3 (Ollama/transformers) или через OpenRouter? | мы (после теста latency) |
| Q4 | OCR провайдер — только Tesseract или подключаем Yandex Vision API (платно, но точнее)? | заказчик (бюджет) |
| Q5 | Бэкап MinIO off-site — через 6 мес. Куда? Yandex Object Storage / Backblaze B2 / другое? | заказчик |
| Q6 | Camunda Tasklist UI на русском — есть ли локализация в community? Если нет, надо или ОК? | мы (проверим) |
| Q7 | Multi-workspace в MemPalace — будет ли разделение по агентам/командам или общий wing-set? | мы (после первой итерации) |

---

_Документ — источник истины по слою хранения и процессов. Любое серьёзное изменение архитектуры — через коммит с правкой этого файла, как и `ARCHITECTURE.md`._
