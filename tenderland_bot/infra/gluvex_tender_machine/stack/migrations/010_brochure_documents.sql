-- =====================================================================
-- 010_brochure_documents.sql — RAG-ready brochure text store
-- =====================================================================
-- Centralizes Markdown content extracted from vendor PDF brochures
-- with PostgreSQL FTS for tender-matching queries.
--
-- Why this approach (vs qdrant embeddings):
--   * Already have postgres infrastructure, no new service needed
--   * Industrial product brochures are SPEC-heavy (numbers, units, model
--     codes) — keyword/phrase search dominates over semantic similarity
--   * FTS rank function gives "good enough" relevance; can add embeddings
--     later as a re-rank layer

CREATE TABLE IF NOT EXISTS brochure_documents (
  id            BIGSERIAL PRIMARY KEY,
  brand         TEXT NOT NULL,
  minio_path    TEXT NOT NULL UNIQUE,
  pdf_path      TEXT,
  title         TEXT,
  content       TEXT NOT NULL,
  fts           TSVECTOR GENERATED ALWAYS AS (
                  to_tsvector('english',
                              coalesce(title,'') || ' ' || content)
                ) STORED,
  size_bytes    INTEGER,
  page_count    INTEGER,
  imported_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brochure_fts        ON brochure_documents USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_brochure_brand      ON brochure_documents(brand);
CREATE INDEX IF NOT EXISTS idx_brochure_title_trgm ON brochure_documents USING GIN (title gin_trgm_ops);

-- Grant to gluvex_app
GRANT SELECT, INSERT, UPDATE, DELETE ON brochure_documents TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE brochure_documents_id_seq TO gluvex_app;
