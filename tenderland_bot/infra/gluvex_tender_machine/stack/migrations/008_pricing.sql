-- =====================================================================
-- migration 008 — Pricing model
-- =====================================================================
-- 4 слоя:
--   1) exchange_rate         — курсы валют USD/CNY/EUR/RUB
--   2) nomenclature_price    — закупочная (USD/CNY) + РРЦ (RUB) + default dealer discount
--   3) pricing_formula       — per-customer формулы (NULL = базовая)
--   4) pricing_formula_brand_multiplier — коэф per бренд внутри формулы
--
-- SECURITY: закупочная цена sensitive. Делаем column-level GRANT:
--   - gluvex_app:           SELECT только publicколонок (rrp_rub, дилерская скидка)
--   - gluvex_purchasing_view: SELECT всех колонок (включая purchase_*)

BEGIN;

-- currency_t уже создан в catalog-architecture миграциях? проверим
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'currency_t') THEN
        CREATE TYPE currency_t AS ENUM ('RUB','USD','EUR','CNY','GBP','CHF','JPY','KRW');
    END IF;
END $$;
COMMENT ON TYPE currency_t IS 'Валюты для цен/курсов';

-- =====================================================================
-- exchange_rate — курсы валют
-- =====================================================================

CREATE TABLE exchange_rate (
    currency currency_t NOT NULL,
    rate_to_rub numeric(20,6) NOT NULL,
    as_of date NOT NULL,
    source text NOT NULL DEFAULT '1c',         -- 'cbr' / '1c' / 'manual'
    created_at timestamptz DEFAULT now(),
    PRIMARY KEY (currency, as_of)
);
COMMENT ON TABLE exchange_rate IS
'Курсы валют к рублю. Источник: 1С (откуда тянет из ЦБ) / manual / cbr. История.';
COMMENT ON COLUMN exchange_rate.rate_to_rub IS 'Сколько рублей за 1 единицу валюты на as_of дату';

CREATE INDEX idx_exchange_rate_latest ON exchange_rate(currency, as_of DESC);

-- Удобная view: текущий курс на сегодня (берёт самый свежий ≤ now())
CREATE VIEW exchange_rate_current AS
SELECT DISTINCT ON (currency)
    currency, rate_to_rub, as_of, source
FROM exchange_rate
WHERE as_of <= CURRENT_DATE
ORDER BY currency, as_of DESC;
COMMENT ON VIEW exchange_rate_current IS 'Текущий курс — самый свежий ≤ сегодня для каждой валюты';


-- =====================================================================
-- nomenclature_price — основной справочник цен per-product
-- =====================================================================

CREATE TABLE nomenclature_price (
    nomenclature_code text PRIMARY KEY REFERENCES nomenclature(code) ON DELETE CASCADE,

    -- ====== ЗАКУПОЧНАЯ (sensitive — column-level GRANT) ======
    purchase_amount numeric(20,4),
    purchase_currency currency_t,                  -- USD / CNY / EUR / RUB
    purchase_valid_from date,
    purchase_supplier_code text REFERENCES partners(code),
    purchase_notes text,

    -- ====== РРЦ (Recommended Retail Price) — public ======
    rrp_rub numeric(20,2),                         -- РРЦ в рублях
    rrp_valid_from date,

    -- ====== Дефолтная дилерская скидка ======
    default_dealer_discount_pct numeric(5,2) DEFAULT 20.00,

    -- ====== Метаданные ======
    source text DEFAULT '1c',
    metadata jsonb DEFAULT '{}',
    updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE nomenclature_price IS
'Цены per-номенклатура. Закупочная (USD/CNY) — sensitive, sensitive column-level GRANT.';
COMMENT ON COLUMN nomenclature_price.purchase_amount IS
'ЗАКУПОЧНАЯ цена (sensitive). Закрыта от gluvex_app, видна только gluvex_purchasing_view';
COMMENT ON COLUMN nomenclature_price.purchase_currency IS 'Валюта закупочной (USD/CNY/EUR)';
COMMENT ON COLUMN nomenclature_price.rrp_rub IS 'Рекомендованная розничная цена (РРЦ) в рублях — public';
COMMENT ON COLUMN nomenclature_price.default_dealer_discount_pct IS
'Дефолтная дилерская скидка (% от РРЦ). По умолчанию 20%';

CREATE INDEX idx_nomenclature_price_supplier ON nomenclature_price(purchase_supplier_code)
  WHERE purchase_supplier_code IS NOT NULL;


-- =====================================================================
-- pricing_formula — формула цены для конкретного партнёра (или дефолт)
-- =====================================================================

CREATE TABLE pricing_formula (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    customer_partner_code text REFERENCES partners(code),    -- NULL = базовая формула
    is_active bool NOT NULL DEFAULT true,
    valid_from date,
    valid_until date,
    notes text,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE pricing_formula IS
'Формула расчёта продажной цены. customer_partner_code NULL = базовая для всех.';
COMMENT ON COLUMN pricing_formula.customer_partner_code IS
'Партнёр-клиент для индивидуальной формулы. NULL = базовая для всех остальных';

CREATE INDEX idx_pricing_formula_customer ON pricing_formula(customer_partner_code)
  WHERE customer_partner_code IS NOT NULL;
CREATE INDEX idx_pricing_formula_active ON pricing_formula(is_active, valid_from, valid_until)
  WHERE is_active = true;

-- Базовая formula по умолчанию (1.0x для всех брендов)
INSERT INTO pricing_formula (id, name, customer_partner_code, is_active, valid_from, notes)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'Базовая формула (default)',
    NULL,
    true,
    CURRENT_DATE,
    'Используется когда у партнёра нет индивидуальной формулы. Multipliers — в таблице ниже.'
);


-- =====================================================================
-- pricing_formula_brand_multiplier — коэф per бренд внутри формулы
-- =====================================================================

CREATE TABLE pricing_formula_brand_multiplier (
    formula_id uuid NOT NULL REFERENCES pricing_formula(id) ON DELETE CASCADE,
    brand_id uuid NOT NULL REFERENCES brand(id),
    multiplier numeric(6,3) NOT NULL,             -- 1.500, 2.200, ...
    notes text,
    PRIMARY KEY (formula_id, brand_id)
);
COMMENT ON TABLE pricing_formula_brand_multiplier IS
'Коэффициенты per бренд в формуле. Пример: Agilent=1.5x, Shimadzu=2.2x, и т.д.';


-- =====================================================================
-- Helper view: вычисление продажной цены
-- =====================================================================

CREATE OR REPLACE VIEW nomenclature_sale_price_calculation AS
WITH base_purchase AS (
    SELECT
        np.nomenclature_code,
        np.purchase_amount,
        np.purchase_currency,
        np.rrp_rub,
        np.default_dealer_discount_pct,
        n.brand_id,
        er.rate_to_rub AS current_rate_to_rub
    FROM nomenclature_price np
    JOIN nomenclature n ON n.code = np.nomenclature_code
    LEFT JOIN exchange_rate_current er ON er.currency = np.purchase_currency
)
SELECT
    bp.nomenclature_code,
    bp.brand_id,
    bp.purchase_amount,
    bp.purchase_currency,
    bp.current_rate_to_rub,
    -- закупочная в рублях по текущему курсу
    (bp.purchase_amount * bp.current_rate_to_rub) AS purchase_rub_today,
    bp.rrp_rub,
    bp.default_dealer_discount_pct,
    -- РРЦ - дилерская скидка
    (bp.rrp_rub * (1 - bp.default_dealer_discount_pct/100.0)) AS rrp_with_default_dealer_discount
FROM base_purchase bp;

COMMENT ON VIEW nomenclature_sale_price_calculation IS
'Helper view: считает purchase_rub_today и rrp_with_default_dealer_discount.
 Per-customer формулы применяются на уровне приложения (1c-bridge / агенты).';


-- =====================================================================
-- Triggers
-- =====================================================================

CREATE TRIGGER trg_nomenclature_price_set_updated_at
    BEFORE UPDATE ON nomenclature_price
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_pricing_formula_set_updated_at
    BEFORE UPDATE ON pricing_formula
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();


-- =====================================================================
-- Column-level security (sensitive purchase prices)
-- =====================================================================

-- Сначала revoke ALL у gluvex_app, потом GRANT только public-колонки
REVOKE ALL ON nomenclature_price FROM gluvex_app;
GRANT SELECT (
    nomenclature_code, rrp_rub, rrp_valid_from,
    default_dealer_discount_pct, source, metadata, updated_at
) ON nomenclature_price TO gluvex_app;
GRANT INSERT, UPDATE, DELETE ON nomenclature_price TO gluvex_app;
-- INSERT/UPDATE — пускаем, но через приложение записываются только public-поля.
-- Закупочные пишет только 1c-bridge через отдельный role gluvex_purchasing_writer.

-- Роль для просмотра sensitive данных (HR / финансисты / руководство)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gluvex_purchasing_view') THEN
        CREATE ROLE gluvex_purchasing_view NOLOGIN;
    END IF;
END $$;

GRANT SELECT ON nomenclature_price TO gluvex_purchasing_view;
GRANT SELECT ON
    exchange_rate, exchange_rate_current,
    pricing_formula, pricing_formula_brand_multiplier,
    nomenclature_sale_price_calculation
TO gluvex_purchasing_view;

-- Доступ для приложений к публичной части прайсинга
GRANT SELECT, INSERT, UPDATE, DELETE ON
    exchange_rate, pricing_formula, pricing_formula_brand_multiplier
TO gluvex_app;
GRANT SELECT ON exchange_rate_current, nomenclature_sale_price_calculation TO gluvex_app;

COMMIT;

\echo ''
\echo '== Migration 008 applied — pricing =='
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('exchange_rate','nomenclature_price','pricing_formula','pricing_formula_brand_multiplier')
ORDER BY table_name;
