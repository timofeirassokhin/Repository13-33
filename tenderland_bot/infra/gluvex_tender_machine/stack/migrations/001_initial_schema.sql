-- =====================================================================
-- gluvex_documents — initial schema (migration 001)
-- =====================================================================
-- Содержимое:
--   • 4 ENUM-типа
--   • 11 таблиц
--   • индексы, FK, append-only-защита через REVOKE
--
-- Источники истины:
--   • tenderland_bot/docs/master-data-architecture.md (раздел 8)
--   • tenderland_bot/docs/storage-architecture.md     (раздел 8)
--
-- Применение (через apply.sh):
--   PGPASSWORD=... psql -h app-db -U postgres -d gluvex_documents -f 001_initial_schema.sql
--
-- Идемпотентно: повторное применение безвредно (все объекты создаются с IF NOT EXISTS
-- или в DO-блоке с проверкой существования).

BEGIN;

-- =====================================================================
-- 1. ENUM-типы
-- =====================================================================

DO $$ BEGIN
  CREATE TYPE document_status AS ENUM (
    'draft', 'pending_review', 'actual', 'archive', 'forbidden', 'expired'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE document_type_t AS ENUM (
    'brochure', 'price', 'sop', 'tz', 'offer', 'kp_template', 'kp_generated',
    'contract', 'methodology', 'brand_book', 'email_thread', 'crm_notes',
    'configurator', 'compatibility', 'discount_rule', 'client_request',
    'call_recording', 'call_transcript', 'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE access_level_t AS ENUM ('public', 'internal', 'confidential', 'restricted');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE source_type_t AS ENUM (
    '1c_supplier', '1c_export', '1c_bridge',
    'tenderland', 'manual_upload', 'gdrive', 'webdav',
    'email_attachment', 'webhook', 'agent_generated', 'twenty'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================
-- 2. document_registry — единый реестр документов
-- =====================================================================
-- Master-данные о каждом файле системы. Сам файл живёт в MinIO.
CREATE TABLE IF NOT EXISTS document_registry (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_id     UUID,                          -- ссылка на entity_links.internal_id (тендер/клиент/лид)
  tenant_id       UUID NOT NULL,
  source_id       TEXT,                          -- ID в источнике (1С code, TL*, GoogleDrive fileId)
  source_type     source_type_t NOT NULL,

  bucket          TEXT NOT NULL,
  object_key      TEXT NOT NULL,
  filename        TEXT NOT NULL,
  content_type    TEXT NOT NULL,
  content_hash    BYTEA NOT NULL,                -- sha256 raw bytes
  size_bytes      BIGINT,

  document_type   document_type_t NOT NULL,
  language        TEXT,                          -- ru / en / mixed / auto
  project_id      UUID,
  is_pii          BOOLEAN NOT NULL DEFAULT false,

  status          document_status NOT NULL DEFAULT 'draft',
  access_level    access_level_t NOT NULL DEFAULT 'internal',
  valid_from      DATE,
  valid_until     DATE,
  supersedes_id   UUID REFERENCES document_registry(id),

  indexed_at      TIMESTAMPTZ,
  embedding_model TEXT,
  chunk_count     INTEGER,
  ocr_applied     BOOLEAN NOT NULL DEFAULT false,

  metadata        JSONB NOT NULL DEFAULT '{}',

  owner_id        UUID NOT NULL,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT document_registry_hash_unique UNIQUE (tenant_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_doc_registry_tenant_status ON document_registry(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_doc_registry_type          ON document_registry(tenant_id, document_type);
CREATE INDEX IF NOT EXISTS idx_doc_registry_source        ON document_registry(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_doc_registry_internal      ON document_registry(internal_id) WHERE internal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_doc_registry_validity      ON document_registry(valid_from, valid_until) WHERE status = 'actual';
CREATE INDEX IF NOT EXISTS idx_doc_registry_filename_trgm ON document_registry USING GIN (filename gin_trgm_ops);

-- =====================================================================
-- 3. document_chunks — чанки для hybrid retrieval (FTS half; vector half в Qdrant)
-- =====================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id     UUID NOT NULL REFERENCES document_registry(id) ON DELETE CASCADE,
  version_id      UUID NOT NULL,                  -- = sha256(content_hash + chunker_config + embedding_model)
  chunk_index     INTEGER NOT NULL,
  chunk_text      TEXT NOT NULL,
  chunk_hash      BYTEA NOT NULL,
  embedding_model TEXT NOT NULL,
  -- pgvector временно не используется (см. 001 — extension закомментирован)
  -- vector сам живёт в Qdrant с payload = {document_id, chunk_id, version_id}
  tsv             tsvector GENERATED ALWAYS AS (to_tsvector('russian', chunk_text)) STORED,
  metadata        JSONB NOT NULL DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT document_chunks_unique UNIQUE (document_id, version_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_version  ON document_chunks(version_id);
CREATE INDEX IF NOT EXISTS idx_chunks_fts      ON document_chunks USING GIN (tsv);

-- =====================================================================
-- 4. entity_links — cross-system identifier mapping
-- =====================================================================
-- Каждая бизнес-сущность имеет stable internal_id + опциональные ID других систем
CREATE TABLE IF NOT EXISTS entity_links (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  internal_id           UUID NOT NULL UNIQUE,
  entity_type           TEXT NOT NULL,           -- company | person | product | tender | lead | kp | deal
  one_c_id              TEXT,
  twenty_company_id     UUID,
  twenty_person_id      UUID,
  twenty_lead_id        UUID,
  twenty_opportunity_id UUID,
  tenderland_id         TEXT,                    -- TL*
  inn                   TEXT,                    -- ключ дедупа company
  one_c_kp_id           TEXT,                    -- ID КП в 1С
  one_c_deal_id         TEXT,                    -- ID сделки в 1С
  metadata              JSONB NOT NULL DEFAULT '{}',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_links_type           ON entity_links(entity_type);
CREATE INDEX IF NOT EXISTS idx_links_one_c          ON entity_links(one_c_id) WHERE one_c_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_twenty_co      ON entity_links(twenty_company_id) WHERE twenty_company_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_twenty_lead    ON entity_links(twenty_lead_id) WHERE twenty_lead_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_twenty_opp     ON entity_links(twenty_opportunity_id) WHERE twenty_opportunity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_inn            ON entity_links(inn) WHERE inn IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_tl             ON entity_links(tenderland_id) WHERE tenderland_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_links_one_c_kp       ON entity_links(one_c_kp_id) WHERE one_c_kp_id IS NOT NULL;

-- FK от document_registry.internal_id → entity_links.internal_id
-- Делаем DEFERRABLE INITIALLY DEFERRED чтобы можно было создать оба в одной транзакции
ALTER TABLE document_registry
  DROP CONSTRAINT IF EXISTS fk_doc_registry_internal;
ALTER TABLE document_registry
  ADD CONSTRAINT fk_doc_registry_internal
  FOREIGN KEY (internal_id) REFERENCES entity_links(internal_id)
  ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;

-- =====================================================================
-- 5. audit_events — append-only журнал всего
-- =====================================================================
-- НИКОГДА не редактируется и не удаляется. REVOKE ниже даёт runtime-защиту.
CREATE TABLE IF NOT EXISTS audit_events (
  id              BIGSERIAL PRIMARY KEY,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,                          -- entity_links.internal_id
  entity_type     TEXT NOT NULL,
  actor_id        UUID,
  actor_type      TEXT NOT NULL,                 -- user | agent | system | scheduled | external
  action          TEXT NOT NULL,                 -- created | updated | status_changed | accessed | sync_in | sync_out | ai_decision | human_decision | conflict
  payload_diff    JSONB,                         -- {field: {from, to}}
  context         JSONB,                         -- {session_id, request_id, ...}
  ip_address      INET,
  user_agent      TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_internal_ts ON audit_events(internal_id, ts DESC) WHERE internal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_actor_ts    ON audit_events(actor_id, ts DESC) WHERE actor_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_action_ts   ON audit_events(action, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_entity_ts   ON audit_events(entity_type, ts DESC);

-- =====================================================================
-- 6. llm_runs — трассировка AI-решений
-- =====================================================================
CREATE TABLE IF NOT EXISTS llm_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,                          -- к какой entity относится решение
  agent_id        TEXT NOT NULL,                 -- tender_analyzer | kp_agent | ...
  task            TEXT NOT NULL,                 -- classify_files | extract_specs | match_products | ...

  model           TEXT NOT NULL,                 -- claude-sonnet-4.5 | bge-m3 | ...
  provider        TEXT NOT NULL,                 -- openrouter | anthropic | local
  prompt_version  TEXT NOT NULL,

  input_refs      JSONB NOT NULL,                -- ссылки на input docs/chunks/data
  input_summary   TEXT,

  output          JSONB NOT NULL,
  explanation     TEXT,                          -- человекочитаемое объяснение
  confidence      NUMERIC(5,2),                  -- 0..100

  tokens_in       INTEGER,
  tokens_out      INTEGER,
  cost_usd        NUMERIC(10,6),
  latency_ms      INTEGER,

  fallback_chain  JSONB,                         -- [{model, error}, ...]
  error           TEXT,
  status          TEXT NOT NULL                  -- success | error | partial
);

CREATE INDEX IF NOT EXISTS idx_llm_internal_ts ON llm_runs(internal_id, ts DESC) WHERE internal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_llm_agent_ts    ON llm_runs(agent_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_llm_task_ts     ON llm_runs(task, ts DESC);
CREATE INDEX IF NOT EXISTS idx_llm_status      ON llm_runs(status) WHERE status != 'success';

-- =====================================================================
-- 7. retrieval_log — каждый retrieval-event агента
-- =====================================================================
CREATE TABLE IF NOT EXISTS retrieval_log (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts                    TIMESTAMPTZ NOT NULL DEFAULT now(),
  agent_id              TEXT NOT NULL,
  session_id            UUID,
  query                 TEXT NOT NULL,
  query_embedding_model TEXT,
  hits                  JSONB NOT NULL,          -- [{chunk_id, document_id, version_id, score, retrieval_method}]
  allowed_filter        JSONB NOT NULL,          -- snapshot agent_policy в момент запроса
  result_count          INTEGER NOT NULL,
  duration_ms           INTEGER
);

CREATE INDEX IF NOT EXISTS idx_retrieval_agent_ts ON retrieval_log(agent_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_retrieval_session  ON retrieval_log(session_id) WHERE session_id IS NOT NULL;

-- =====================================================================
-- 8. agent_policies — retrieval whitelist per agent
-- =====================================================================
CREATE TABLE IF NOT EXISTS agent_policies (
  agent_id        TEXT PRIMARY KEY,
  allow_rules     JSONB NOT NULL,                -- [{document_type, status: []}]
  deny_explicit   JSONB,
  historical_ok   BOOLEAN NOT NULL DEFAULT false,
  max_results     INTEGER NOT NULL DEFAULT 10,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- 9. sync_runs / sync_errors — обмен с внешними системами
-- =====================================================================
CREATE TABLE IF NOT EXISTS sync_runs (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts_started       TIMESTAMPTZ NOT NULL DEFAULT now(),
  ts_finished      TIMESTAMPTZ,
  service          TEXT NOT NULL,                -- 1c-bridge | tenderland-search | twenty-sync
  direction        TEXT NOT NULL,                -- in | out | bidirectional
  operation        TEXT NOT NULL,                -- import_companies | export_kp | search_tenders | ...
  idempotency_key  TEXT UNIQUE,
  request_payload  JSONB,
  response_payload JSONB,
  records_in       INTEGER,
  records_out      INTEGER,
  status           TEXT NOT NULL,                -- success | partial | failed | running
  error_summary    TEXT
);

CREATE INDEX IF NOT EXISTS idx_sync_service_ts ON sync_runs(service, ts_started DESC);
CREATE INDEX IF NOT EXISTS idx_sync_unfinished ON sync_runs(status) WHERE status IN ('running', 'failed', 'partial');

CREATE TABLE IF NOT EXISTS sync_errors (
  id              BIGSERIAL PRIMARY KEY,
  sync_run_id     UUID NOT NULL REFERENCES sync_runs(id) ON DELETE CASCADE,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID,
  error_code      TEXT,
  error_message   TEXT NOT NULL,
  payload         JSONB,
  retry_count     INTEGER NOT NULL DEFAULT 0,
  resolved_at     TIMESTAMPTZ,
  resolved_by     UUID
);

CREATE INDEX IF NOT EXISTS idx_sync_errors_run     ON sync_errors(sync_run_id);
CREATE INDEX IF NOT EXISTS idx_sync_errors_unresolved ON sync_errors(ts DESC) WHERE resolved_at IS NULL;

-- =====================================================================
-- 10. status_history — история смены статусов
-- =====================================================================
CREATE TABLE IF NOT EXISTS status_history (
  id              BIGSERIAL PRIMARY KEY,
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID NOT NULL,
  entity_type     TEXT NOT NULL,                 -- tender | lead | kp | deal | document
  field           TEXT NOT NULL,                 -- status | analysis_status | decision | ...
  status_from     TEXT,
  status_to       TEXT NOT NULL,
  changed_by      UUID,
  changed_by_type TEXT NOT NULL,                 -- user | agent | system | external
  reason          TEXT,
  llm_run_id      UUID REFERENCES llm_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_status_internal_ts ON status_history(internal_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_status_entity_ts   ON status_history(entity_type, ts DESC);

-- =====================================================================
-- 11. human_reviews — ручные решения менеджеров
-- =====================================================================
CREATE TABLE IF NOT EXISTS human_reviews (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
  internal_id     UUID NOT NULL,
  entity_type     TEXT NOT NULL,
  reviewer_id     UUID NOT NULL,
  decision        TEXT NOT NULL,                 -- accept | reject | needs_clarification | escalate
  ai_decision     TEXT,                          -- что предложил AI (для метрики расхождения)
  ai_run_id       UUID REFERENCES llm_runs(id),
  comment         TEXT,
  takes_ai_advice BOOLEAN                        -- accept = AI совет; reject ≠ AI совет
);

CREATE INDEX IF NOT EXISTS idx_reviews_internal     ON human_reviews(internal_id);
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer_ts  ON human_reviews(reviewer_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_reviews_ai_advice    ON human_reviews(ts DESC) WHERE takes_ai_advice IS NOT NULL;

-- =====================================================================
-- 12. Append-only защита через REVOKE на уровне БД
-- =====================================================================
-- audit_events и retrieval_log нельзя редактировать НИКОМУ кроме superuser
-- (на случай SQL-injection в приложении или ошибки разработчика).
DO $$ BEGIN
  -- даём gluvex_app полные права на mutable таблицы
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO gluvex_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gluvex_app;
  -- но забираем UPDATE/DELETE с append-only
  REVOKE UPDATE, DELETE ON audit_events FROM gluvex_app;
  REVOKE UPDATE, DELETE ON retrieval_log FROM gluvex_app;
EXCEPTION WHEN undefined_object THEN
  RAISE NOTICE 'gluvex_app role not found, skipping grants';
END $$;

-- =====================================================================
-- 13. Триггеры updated_at
-- =====================================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- document_registry.updated_at
DROP TRIGGER IF EXISTS trg_doc_registry_updated_at ON document_registry;
CREATE TRIGGER trg_doc_registry_updated_at
  BEFORE UPDATE ON document_registry
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- entity_links.updated_at
DROP TRIGGER IF EXISTS trg_entity_links_updated_at ON entity_links;
CREATE TRIGGER trg_entity_links_updated_at
  BEFORE UPDATE ON entity_links
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- agent_policies.updated_at
DROP TRIGGER IF EXISTS trg_agent_policies_updated_at ON agent_policies;
CREATE TRIGGER trg_agent_policies_updated_at
  BEFORE UPDATE ON agent_policies
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =====================================================================
-- 14. Seed: стартовые agent_policies (4 агента из master-data-architecture.md раздел 6)
-- =====================================================================
INSERT INTO agent_policies (agent_id, allow_rules, deny_explicit, historical_ok, max_results) VALUES
  ('tender_analyzer',
    '[
      {"document_type": "tz",              "status": ["actual"]},
      {"document_type": "sop",             "status": ["actual"]},
      {"document_type": "methodology",     "status": ["actual"]},
      {"document_type": "brochure",        "status": ["actual"]},
      {"document_type": "client_request",  "status": ["actual", "archive"]}
    ]'::jsonb,
    '[{"access_level": "restricted"}]'::jsonb,
    false, 10
  ),
  ('product_manager',
    '[
      {"document_type": "brochure",      "status": ["actual"]},
      {"document_type": "price",         "status": ["actual"]},
      {"document_type": "methodology",   "status": ["actual"]},
      {"document_type": "configurator",  "status": ["actual"]},
      {"document_type": "compatibility", "status": ["actual"]}
    ]'::jsonb,
    NULL, false, 10
  ),
  ('kp_agent',
    '[
      {"document_type": "kp_template",   "status": ["actual"]},
      {"document_type": "price",         "status": ["actual"]},
      {"document_type": "discount_rule", "status": ["actual"]},
      {"document_type": "brochure",      "status": ["actual"]},
      {"document_type": "brand_book",    "status": ["actual"]}
    ]'::jsonb,
    NULL, false, 15
  ),
  ('email_agent',
    '[
      {"document_type": "email_thread",  "status": ["actual", "archive"]},
      {"document_type": "kp_template",   "status": ["actual"]},
      {"document_type": "crm_notes",     "status": ["actual"]}
    ]'::jsonb,
    '[{"is_pii": true, "scope": "cross_customer"}]'::jsonb,
    true, 10
  )
ON CONFLICT (agent_id) DO NOTHING;

COMMIT;

-- =====================================================================
-- Sanity check (вне транзакции)
-- =====================================================================
DO $$
DECLARE
  table_count INT;
  policy_count INT;
BEGIN
  SELECT COUNT(*) INTO table_count FROM information_schema.tables WHERE table_schema = 'public';
  SELECT COUNT(*) INTO policy_count FROM agent_policies;
  RAISE NOTICE 'Migration 001 OK: % tables, % seeded agent_policies', table_count, policy_count;
END $$;
