-- =====================================================================
-- migration 002 — products catalog (gluvex_documents)
-- =====================================================================
-- Источник: catalog-architecture.md (раздел 3)
--
-- Создаёт:
--   • 6 ENUM-типов (product_category_t, product_domain_t, ru_status_t, config_type_t,
--     compatibility_type_t, pricing_type_t, currency_t)
--   • 6 таблиц: product, product_configuration, product_compatibility,
--     product_slot, sequencer_runtime_metric, product_pricing
--   • fx_rate (для пересчёта валют)
--
-- Идемпотентно: повторное применение безвредно (IF NOT EXISTS / DO duplicate_object).

BEGIN;

-- =====================================================================
-- 1. ENUM-типы
-- =====================================================================

DO $$ BEGIN
  CREATE TYPE product_category_t AS ENUM (
    -- Аналитика — системы
    'hplc_system', 'hplc_pump', 'hplc_autosampler', 'hplc_column_oven', 'hplc_detector',
    'gc_system', 'gc_module', 'mass_spectrometer',
    'aas_system', 'icp_oes', 'icp_ms',
    'uv_vis_spectrometer', 'ftir_spectrometer', 'nir_spectrometer', 'raman_spectrometer',
    -- Хроматография — расходники
    'hplc_column', 'gc_column', 'vial', 'syringe_filter', 'spe_cartridge', 'septa',
    -- NGS платформы
    'sequencer_platform',
    -- NGS компоненты
    'sequencer_flowcell', 'sequencer_reagent_kit',
    -- NGS реагенты и панели
    'ngs_library_prep_kit', 'ngs_target_capture_panel', 'ngs_amplicon_panel',
    'pcr_kit', 'realtime_pcr_kit', 'dna_extraction_kit', 'rna_extraction_kit',
    -- Общая лаборатория
    'centrifuge', 'shaker_vortex', 'incubator', 'drying_oven', 'climate_chamber',
    'biological_safety_cabinet', 'laminar_hood', 'balance', 'titrator', 'water_purifier',
    'pcr_thermal_cycler', 'realtime_pcr', 'gel_documentation', 'electrophoresis',
    -- Прочее
    'consumable', 'spare_part', 'accessory', 'software', 'service', 'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE product_domain_t AS ENUM (
    'analytical', 'genetics_ngs', 'molecular_diagnostics',
    'life_science_general', 'general_lab', 'pharmaceutical', 'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE ru_status_t AS ENUM (
    'none', 'pending', 'active', 'expired', 'revoked', 'not_applicable'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE config_type_t AS ENUM (
    'flowcell', 'sequencer_kit', 'run_mode',
    'pump_module', 'autosampler_module', 'column_oven_module', 'detector_module',
    'column', 'atomizer', 'lamp', 'sample_introduction',
    'panel_variant', 'compatible_platform',
    'option', 'firmware_version', 'other'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE compatibility_type_t AS ENUM (
    'installable_in', 'requires', 'replaces', 'compatible_with',
    'incompatible_with', 'recommended_with', 'paired_with'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE pricing_type_t AS ENUM (
    'purchase', 'sale', 'list', 'distributor', 'msrp'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE currency_t AS ENUM (
    'USD', 'EUR', 'CNY', 'RUB', 'GBP', 'CHF', 'JPY'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================
-- 2. product — основная таблица каталога
-- =====================================================================
CREATE TABLE IF NOT EXISTS product (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,
  product_code          TEXT,
  vendor_code           TEXT,
  brand                 TEXT NOT NULL,
  model                 TEXT NOT NULL,
  oem_of_id             UUID REFERENCES product(id),
  category              product_category_t NOT NULL,
  subcategory           TEXT,
  domain                product_domain_t NOT NULL,
  display_name          TEXT NOT NULL,
  description           TEXT,
  synonyms              TEXT[],
  base_specs            JSONB NOT NULL DEFAULT '{}',
  -- РУ
  ru_status             ru_status_t NOT NULL DEFAULT 'none',
  ru_number             TEXT,
  ru_valid_from         DATE,
  ru_valid_until        DATE,
  ru_url                TEXT,
  ru_class              TEXT,
  -- жизненный цикл
  status                TEXT NOT NULL DEFAULT 'active',
  release_date          DATE,
  discontinue_date      DATE,
  manufacturer_country  TEXT,
  -- источники
  source_urls           TEXT[],
  datasheet_paths       TEXT[],
  brochure_urls         TEXT[],
  -- метаданные
  metadata              JSONB DEFAULT '{}',
  content_hash          BYTEA,
  imported_at           TIMESTAMPTZ,
  imported_from         TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT product_brand_model_unique UNIQUE (tenant_id, brand, model)
);

CREATE INDEX IF NOT EXISTS idx_product_brand           ON product(brand);
CREATE INDEX IF NOT EXISTS idx_product_category        ON product(category);
CREATE INDEX IF NOT EXISTS idx_product_domain          ON product(domain);
CREATE INDEX IF NOT EXISTS idx_product_ru_active       ON product(ru_status) WHERE ru_status = 'active';
CREATE INDEX IF NOT EXISTS idx_product_oem             ON product(oem_of_id) WHERE oem_of_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_product_status          ON product(status) WHERE status != 'active';
CREATE INDEX IF NOT EXISTS idx_product_synonyms_gin    ON product USING GIN (synonyms);
CREATE INDEX IF NOT EXISTS idx_product_model_trgm      ON product USING GIN (model gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_product_display_trgm    ON product USING GIN (display_name gin_trgm_ops);

-- =====================================================================
-- 3. product_configuration — варианты комплектации
-- =====================================================================
CREATE TABLE IF NOT EXISTS product_configuration (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,
  product_id            UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  config_type           config_type_t NOT NULL,
  configuration_code    TEXT,
  name                  TEXT NOT NULL,
  specs                 JSONB NOT NULL DEFAULT '{}',
  -- РУ конфигурации
  ru_status             ru_status_t NOT NULL DEFAULT 'none',
  ru_number             TEXT,
  ru_valid_from         DATE,
  ru_valid_until        DATE,
  ru_url                TEXT,
  -- prev/replacement
  replaces_id           UUID REFERENCES product_configuration(id),
  is_default            BOOLEAN NOT NULL DEFAULT false,
  status                TEXT NOT NULL DEFAULT 'active',
  -- источники
  source_urls           TEXT[],
  metadata              JSONB DEFAULT '{}',
  content_hash          BYTEA,
  imported_at           TIMESTAMPTZ,
  imported_from         TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_config_product_type ON product_configuration(product_id, config_type);
CREATE INDEX IF NOT EXISTS idx_config_type         ON product_configuration(config_type);
CREATE INDEX IF NOT EXISTS idx_config_ru_active    ON product_configuration(ru_status) WHERE ru_status = 'active';
CREATE INDEX IF NOT EXISTS idx_config_code         ON product_configuration(configuration_code) WHERE configuration_code IS NOT NULL;

-- =====================================================================
-- 4. product_compatibility — граф совместимости
-- =====================================================================
CREATE TABLE IF NOT EXISTS product_compatibility (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,
  a_product_id          UUID REFERENCES product(id) ON DELETE CASCADE,
  a_config_id           UUID REFERENCES product_configuration(id) ON DELETE CASCADE,
  b_product_id          UUID REFERENCES product(id) ON DELETE CASCADE,
  b_config_id           UUID REFERENCES product_configuration(id) ON DELETE CASCADE,
  compatibility_type    compatibility_type_t NOT NULL,
  notes                 TEXT,
  source_url            TEXT,
  confidence            NUMERIC(3,2) DEFAULT 1.0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT compat_has_a CHECK (a_product_id IS NOT NULL OR a_config_id IS NOT NULL),
  CONSTRAINT compat_has_b CHECK (b_product_id IS NOT NULL OR b_config_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_compat_a_product ON product_compatibility(a_product_id) WHERE a_product_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compat_b_product ON product_compatibility(b_product_id) WHERE b_product_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compat_a_config  ON product_compatibility(a_config_id)  WHERE a_config_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compat_b_config  ON product_compatibility(b_config_id)  WHERE b_config_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_compat_type      ON product_compatibility(compatibility_type);

-- =====================================================================
-- 5. product_slot — слоты конфигурации
-- =====================================================================
CREATE TABLE IF NOT EXISTS product_slot (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id            UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  slot_name             TEXT NOT NULL,
  slot_role             TEXT NOT NULL,
  min_count             INTEGER NOT NULL DEFAULT 0,
  max_count             INTEGER NOT NULL DEFAULT 1,
  required              BOOLEAN NOT NULL DEFAULT false,
  allowed_categories    product_category_t[],
  notes                 TEXT,
  CONSTRAINT slot_name_unique UNIQUE (product_id, slot_name)
);

CREATE INDEX IF NOT EXISTS idx_slot_product ON product_slot(product_id);
CREATE INDEX IF NOT EXISTS idx_slot_role    ON product_slot(slot_role);

-- =====================================================================
-- 6. sequencer_runtime_metric — реальные метрики прогона
-- =====================================================================
CREATE TABLE IF NOT EXISTS sequencer_runtime_metric (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                UUID NOT NULL,
  sequencer_id             UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  flowcell_config_id       UUID REFERENCES product_configuration(id) ON DELETE SET NULL,
  reagent_kit_id           UUID REFERENCES product_configuration(id) ON DELETE SET NULL,
  read_mode                TEXT NOT NULL,
  read_length_max          INTEGER,
  is_paired_end            BOOLEAN,
  cycles                   INTEGER,
  total_reads_million_max  NUMERIC,
  total_reads_million_typ  NUMERIC,
  total_output_gb_max      NUMERIC,
  total_output_gb_typ      NUMERIC,
  run_time_hours_min       NUMERIC,
  run_time_hours_max       NUMERIC,
  q30_pct                  NUMERIC(5,2),
  q40_pct                  NUMERIC(5,2),
  cost_per_gb_usd          NUMERIC(10,4),
  cost_per_reaction_usd    NUMERIC(10,2),
  applications             TEXT[],
  notes                    TEXT,
  source_url               TEXT,
  source_confidence        NUMERIC(3,2) DEFAULT 1.0,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runtime_seq            ON sequencer_runtime_metric(sequencer_id);
CREATE INDEX IF NOT EXISTS idx_runtime_flowcell       ON sequencer_runtime_metric(flowcell_config_id) WHERE flowcell_config_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_runtime_output_gb      ON sequencer_runtime_metric(total_output_gb_typ);
CREATE INDEX IF NOT EXISTS idx_runtime_reads_m        ON sequencer_runtime_metric(total_reads_million_typ);
CREATE INDEX IF NOT EXISTS idx_runtime_read_mode      ON sequencer_runtime_metric(read_mode);
CREATE INDEX IF NOT EXISTS idx_runtime_applications   ON sequencer_runtime_metric USING GIN (applications);

-- =====================================================================
-- 7. product_pricing — цены (наполняется из 1С)
-- =====================================================================
CREATE TABLE IF NOT EXISTS product_pricing (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,
  product_id            UUID REFERENCES product(id) ON DELETE CASCADE,
  configuration_id      UUID REFERENCES product_configuration(id) ON DELETE CASCADE,
  pricing_type          pricing_type_t NOT NULL,
  amount                NUMERIC,
  currency              currency_t NOT NULL,
  formula_expr          TEXT,
  derived_from_id       UUID REFERENCES product_pricing(id),
  multiplier            NUMERIC,
  vat_rate              NUMERIC(4,2),
  vat_rule              TEXT,
  effective_from        DATE NOT NULL,
  effective_until       DATE,
  source                TEXT,
  notes                 TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT pricing_has_target CHECK (product_id IS NOT NULL OR configuration_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_pricing_product   ON product_pricing(product_id) WHERE product_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pricing_config    ON product_pricing(configuration_id) WHERE configuration_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_pricing_effective ON product_pricing(effective_from, effective_until);
CREATE INDEX IF NOT EXISTS idx_pricing_type      ON product_pricing(pricing_type, currency);

-- =====================================================================
-- 8. fx_rate — курсы валют (ЦБ РФ + другие источники)
-- =====================================================================
CREATE TABLE IF NOT EXISTS fx_rate (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  currency_from         currency_t NOT NULL,
  currency_to           currency_t NOT NULL,
  rate                  NUMERIC(20, 8) NOT NULL,
  rate_date             DATE NOT NULL,
  source                TEXT NOT NULL DEFAULT 'cbr_ru',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT fx_unique UNIQUE (currency_from, currency_to, rate_date, source)
);

CREATE INDEX IF NOT EXISTS idx_fx_pair_date ON fx_rate(currency_from, currency_to, rate_date DESC);

-- =====================================================================
-- 9. Триггеры updated_at
-- =====================================================================
DROP TRIGGER IF EXISTS trg_product_updated_at ON product;
CREATE TRIGGER trg_product_updated_at BEFORE UPDATE ON product
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS trg_config_updated_at ON product_configuration;
CREATE TRIGGER trg_config_updated_at BEFORE UPDATE ON product_configuration
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS trg_metric_updated_at ON sequencer_runtime_metric;
CREATE TRIGGER trg_metric_updated_at BEFORE UPDATE ON sequencer_runtime_metric
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

DROP TRIGGER IF EXISTS trg_pricing_updated_at ON product_pricing;
CREATE TRIGGER trg_pricing_updated_at BEFORE UPDATE ON product_pricing
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =====================================================================
-- 10. Grants для gluvex_app
-- =====================================================================
DO $$ BEGIN
  GRANT SELECT, INSERT, UPDATE, DELETE ON
    product, product_configuration, product_compatibility, product_slot,
    sequencer_runtime_metric, product_pricing, fx_rate
    TO gluvex_app;
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gluvex_app;
EXCEPTION WHEN undefined_object THEN
  RAISE NOTICE 'gluvex_app role missing, skipping grants';
END $$;

COMMIT;

-- =====================================================================
-- Sanity check
-- =====================================================================
DO $$
DECLARE
  total_tables INT;
BEGIN
  SELECT COUNT(*) INTO total_tables FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name IN
      ('product', 'product_configuration', 'product_compatibility', 'product_slot',
       'sequencer_runtime_metric', 'product_pricing', 'fx_rate');
  RAISE NOTICE 'Migration 002 OK: % of 7 catalog tables exist', total_tables;
END $$;
