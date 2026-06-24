-- =====================================================================
-- 011_tenderland_pipeline.sql — Tenderland tender registry + Tier-2/3 decisions
-- =====================================================================
-- Stores tenders pulled from Tenderland API and AI-pipeline decisions:
--   tenderland_tender         — registry of unique tenders (by tender_id)
--   tenderland_run            — each daily pipeline execution (audit + quota tracking)
--   tenderland_tier2_decision — LLM relevance verdict (metadata only)
--   tenderland_tier3_decision — post-ТЗ-download tech + commercial analysis
--   tenderland_archive_file   — per-file records of downloaded zip archives
--
-- Conventions:
--   * tender_id (TLXXXXXX) is the natural unique key from Tenderland.
--   * Tier-2 + Tier-3 decisions are run-scoped (one decision per tender per run)
--     so re-runs append new decisions, full history preserved.
--   * search_topic mirrors topic name from config/keywords_config*.md
--     (e.g. "01_LC_LCMS_GPC_Prep", "MDX_01_Sequencers").
--   * Counterparty integration: customer_inn references counterparties.inn
--     informally (not FK — tenders may have INNs not yet in counterparty registry).

-- =====================================================================
-- 1. tenderland_tender
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenderland_tender (
  id                BIGSERIAL PRIMARY KEY,
  tender_id         TEXT UNIQUE NOT NULL,            -- TL2596426057
  reg_number        TEXT NOT NULL,
  name              TEXT NOT NULL,
  begin_price       NUMERIC(18,2),
  publish_date      TIMESTAMPTZ,
  end_date          TIMESTAMPTZ,
  region            TEXT,
  type_name         TEXT,
  customer_short    TEXT,
  customer_full     TEXT,
  customer_inn      TEXT,
  customer_ogrn     TEXT,
  customer_kpp      TEXT,
  customer_contacts TEXT,
  lot_categories    TEXT[],                          -- сырые названия категорий из Tenderland
  module            TEXT,                            -- "Государственные закупки", "Контракты" и т.д.
  etp_link          TEXT,
  files_url         TEXT,                            -- ссылка Tenderland на zip
  file_count        INTEGER,
  raw_json          JSONB,                           -- полный ответ для отладки
  search_topic      TEXT NOT NULL,                   -- 01_LC_LCMS_GPC_Prep | MDX_01_Sequencers | ...
  search_domain     TEXT,                            -- analytical | molecular_diagnostics | general_lab | ...
  first_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_run_id  BIGINT                           -- last tenderland_run.id that re-encountered this tender
);

CREATE INDEX IF NOT EXISTS idx_tenderland_tender_reg          ON tenderland_tender(reg_number);
CREATE INDEX IF NOT EXISTS idx_tenderland_tender_inn          ON tenderland_tender(customer_inn);
CREATE INDEX IF NOT EXISTS idx_tenderland_tender_topic        ON tenderland_tender(search_topic);
CREATE INDEX IF NOT EXISTS idx_tenderland_tender_first_seen   ON tenderland_tender(first_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_tenderland_tender_end_date     ON tenderland_tender(end_date);
CREATE INDEX IF NOT EXISTS idx_tenderland_tender_categories   ON tenderland_tender USING GIN (lot_categories);

-- =====================================================================
-- 2. tenderland_run — каждый запуск pipeline (для аудита и трекинга квот)
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenderland_run (
  id                BIGSERIAL PRIMARY KEY,
  started_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at       TIMESTAMPTZ,
  status            TEXT NOT NULL DEFAULT 'running', -- running | done | failed
  total_collected   INTEGER,                         -- сколько тендеров пришло из Export
  total_tier2_pass  INTEGER,
  total_tier2_review INTEGER,
  total_tier2_drop  INTEGER,
  total_tier3       INTEGER,                         -- сколько обработано Tier-3
  api_requests      INTEGER,
  api_units_used    INTEGER,
  llm_cost_usd      NUMERIC(8,5),
  llm_input_tokens  INTEGER,
  llm_output_tokens INTEGER,
  error_message     TEXT,
  notes             TEXT
);

CREATE INDEX IF NOT EXISTS idx_tenderland_run_started ON tenderland_run(started_at DESC);

-- =====================================================================
-- 3. tenderland_tier2_decision — LLM-классификатор (по метаданным)
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenderland_tier2_decision (
  id                BIGSERIAL PRIMARY KEY,
  run_id            BIGINT NOT NULL REFERENCES tenderland_run(id) ON DELETE CASCADE,
  tender_pk         BIGINT NOT NULL REFERENCES tenderland_tender(id) ON DELETE CASCADE,
  relevance         TEXT NOT NULL CHECK (relevance IN ('pass','review','fail')),
  confidence        NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  score_breakdown   JSONB,
  matched_signals   TEXT[],
  customer_class    TEXT,                            -- whitelist | blacklist | gray | unknown
  customer_type     TEXT,                            -- НИИ | медцентр | университет | ...
  detected_class    TEXT,                            -- HPLC | LCMS-TQ | NGS-Illumina | ...
  flags             TEXT[],
  reasoning         TEXT,
  model             TEXT,                            -- claude-haiku-4-5
  input_tokens      INTEGER,
  output_tokens     INTEGER,
  cost_usd          NUMERIC(8,5),
  error             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, tender_pk)
);

CREATE INDEX IF NOT EXISTS idx_tenderland_tier2_relevance  ON tenderland_tier2_decision(relevance);
CREATE INDEX IF NOT EXISTS idx_tenderland_tier2_confidence ON tenderland_tier2_decision(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_tenderland_tier2_run        ON tenderland_tier2_decision(run_id);
CREATE INDEX IF NOT EXISTS idx_tenderland_tier2_tender     ON tenderland_tier2_decision(tender_pk);

-- =====================================================================
-- 4. tenderland_tier3_decision — после скачки ТЗ (техника + коммерция)
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenderland_tier3_decision (
  id                  BIGSERIAL PRIMARY KEY,
  run_id              BIGINT NOT NULL REFERENCES tenderland_run(id) ON DELETE CASCADE,
  tender_pk           BIGINT NOT NULL REFERENCES tenderland_tender(id) ON DELETE CASCADE,

  -- Технический анализ
  extracted_specs     JSONB,                         -- [{name, value, unit, required}, ...]
  brands_detected     TEXT[],                        -- бренды/модели, упомянутые в ТЗ
  classified_files    JSONB,                         -- {tz: [...], contract: [...], price_calc: [...], ...}

  -- Коммерческий и юридический анализ
  delivery_term       TEXT,                          -- "30 дней с даты заключения", "по требованию заказчика"
  delivery_terms_raw  TEXT,                          -- полный исходный текст условий поставки
  payment_term        TEXT,                          -- "100% постоплата", "30% аванс"
  bid_bond_rub        NUMERIC(18,2),                 -- обеспечение заявки
  bid_bond_pct        NUMERIC(5,2),                  -- % от НМЦК
  contract_bond_rub   NUMERIC(18,2),                 -- обеспечение контракта
  contract_bond_pct   NUMERIC(5,2),
  participant_req     JSONB,                         -- {sro: [...], experience: ..., natregime: bool, ...}

  -- Матчинг с нашим каталогом
  matched_products    JSONB,                         -- [{product_id, score, reasoning, fails_on}, ...]
  best_match_id       INTEGER,                       -- лучший кандидат из public.product
  best_match_score    NUMERIC(5,2),
  recommendation      TEXT,                          -- что предлагаем
  feasibility         TEXT CHECK (feasibility IN ('realistic','partial','not_realistic')),
  reasoning           TEXT,

  -- Meta
  model               TEXT,
  cost_usd            NUMERIC(8,5),
  input_tokens        INTEGER,
  output_tokens       INTEGER,
  error               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, tender_pk)
);

CREATE INDEX IF NOT EXISTS idx_tenderland_tier3_feasibility ON tenderland_tier3_decision(feasibility);
CREATE INDEX IF NOT EXISTS idx_tenderland_tier3_run         ON tenderland_tier3_decision(run_id);
CREATE INDEX IF NOT EXISTS idx_tenderland_tier3_tender      ON tenderland_tier3_decision(tender_pk);

-- =====================================================================
-- 5. tenderland_archive_file — файлы в скачанных архивах
-- =====================================================================
CREATE TABLE IF NOT EXISTS tenderland_archive_file (
  id                BIGSERIAL PRIMARY KEY,
  tender_pk         BIGINT NOT NULL REFERENCES tenderland_tender(id) ON DELETE CASCADE,
  run_id            BIGINT REFERENCES tenderland_run(id) ON DELETE SET NULL,
  file_name         TEXT NOT NULL,
  file_type         TEXT,                            -- tz | contract | notification | price_calc | application | unknown
  size_bytes        BIGINT,
  minio_bucket      TEXT,                            -- gluvex-tenders
  minio_path        TEXT,                            -- 2026/05/TL2596426057/файл.docx
  content_chars     INTEGER,                         -- сколько символов извлекли
  extracted_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tenderland_archive_tender ON tenderland_archive_file(tender_pk);
CREATE INDEX IF NOT EXISTS idx_tenderland_archive_type   ON tenderland_archive_file(file_type);

-- =====================================================================
-- 6. Grants для приложения gluvex_app
-- =====================================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON tenderland_tender            TO gluvex_app;
GRANT SELECT, INSERT, UPDATE         ON tenderland_run                TO gluvex_app;
GRANT SELECT, INSERT, UPDATE         ON tenderland_tier2_decision    TO gluvex_app;
GRANT SELECT, INSERT, UPDATE         ON tenderland_tier3_decision    TO gluvex_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON tenderland_archive_file       TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE tenderland_tender_id_seq             TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE tenderland_run_id_seq                TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE tenderland_tier2_decision_id_seq     TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE tenderland_tier3_decision_id_seq     TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE tenderland_archive_file_id_seq       TO gluvex_app;
