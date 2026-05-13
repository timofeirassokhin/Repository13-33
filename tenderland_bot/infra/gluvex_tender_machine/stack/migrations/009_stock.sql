-- =====================================================================
-- migration 009 — Stock (остатки на складе)
-- =====================================================================
-- 1 склад у Глювекса. Real-time события (push от 1С).
-- 2 таблицы:
--   stock_current  — снапшот текущего остатка per номенклатура
--   stock_event    — append-only журнал событий (поступление/продажа/резерв/...)
-- Trigger на stock_event автоматически обновляет stock_current.

BEGIN;

-- =====================================================================
-- ENUM
-- =====================================================================

CREATE TYPE stock_event_type_t AS ENUM (
    'incoming',         -- поступление (приход)
    'sale',             -- продажа (расход)
    'reserve',          -- резерв (под заказ — забронировано но физически на складе)
    'unreserve',        -- снятие резерва
    'reserve_to_sale',  -- резерв → продажа (списание зарезервированного)
    'adjustment',       -- инвентаризационная корректировка (может быть + или -)
    'transfer',         -- перемещение (для будущей мультискладной модели)
    'writeoff',         -- списание (брак/потери)
    'return_from_customer',
    'return_to_supplier'
);
COMMENT ON TYPE stock_event_type_t IS '1С: ВидыДвиженияТоваров — типы движения на складе';


-- =====================================================================
-- stock_current — снапшот текущего остатка
-- =====================================================================

CREATE TABLE stock_current (
    nomenclature_code text PRIMARY KEY REFERENCES nomenclature(code) ON DELETE CASCADE,
    quantity_on_hand numeric(15,3) NOT NULL DEFAULT 0,
    quantity_reserved numeric(15,3) NOT NULL DEFAULT 0,
    quantity_available numeric(15,3) GENERATED ALWAYS AS
        (quantity_on_hand - quantity_reserved) STORED,
    last_event_id bigint,
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE stock_current IS
'Текущий остаток per номенклатура (1 склад). Обновляется триггером на stock_event.';
COMMENT ON COLUMN stock_current.quantity_on_hand IS 'Физический остаток на складе';
COMMENT ON COLUMN stock_current.quantity_reserved IS 'Зарезервировано (под заказы)';
COMMENT ON COLUMN stock_current.quantity_available IS
'Доступно для продажи (computed: on_hand - reserved)';

CREATE INDEX idx_stock_current_available ON stock_current(quantity_available)
  WHERE quantity_available > 0;


-- =====================================================================
-- stock_event — append-only журнал
-- =====================================================================

CREATE TABLE stock_event (
    id bigserial PRIMARY KEY,
    nomenclature_code text NOT NULL REFERENCES nomenclature(code),
    event_type stock_event_type_t NOT NULL,
    delta_on_hand numeric(15,3) NOT NULL DEFAULT 0,
    delta_reserved numeric(15,3) NOT NULL DEFAULT 0,
    counterparty_code text REFERENCES counterparties(code),
    partner_code text REFERENCES partners(code),
    document_ref text,                     -- ссылка на 1С документ (Поступление/Реализация/Резерв)
    document_number text,                  -- номер документа в 1С
    occurred_at timestamptz NOT NULL,      -- когда фактически произошло
    recorded_at timestamptz NOT NULL DEFAULT now(),  -- когда дошло до нас
    source text NOT NULL DEFAULT '1c',
    notes text,
    metadata jsonb DEFAULT '{}'
);

COMMENT ON TABLE stock_event IS
'1С: Append-only журнал движений товаров. Источник: push от 1С (real-time).';
COMMENT ON COLUMN stock_event.delta_on_hand IS
'Изменение quantity_on_hand (+ приход / − расход)';
COMMENT ON COLUMN stock_event.delta_reserved IS
'Изменение quantity_reserved (+ резерв / − снятие резерва)';
COMMENT ON COLUMN stock_event.document_ref IS
'1С документ — для traceability (Поступление товаров от поставщика, Реализация, и т.п.)';

CREATE INDEX idx_stock_event_nomenclature ON stock_event(nomenclature_code, occurred_at DESC);
CREATE INDEX idx_stock_event_recorded ON stock_event(recorded_at DESC);
CREATE INDEX idx_stock_event_type ON stock_event(event_type);
CREATE INDEX idx_stock_event_document ON stock_event(document_ref) WHERE document_ref IS NOT NULL;
CREATE INDEX idx_stock_event_counterparty ON stock_event(counterparty_code) WHERE counterparty_code IS NOT NULL;

-- =====================================================================
-- Trigger: каждый INSERT в stock_event обновляет stock_current атомарно
-- =====================================================================

CREATE OR REPLACE FUNCTION trg_stock_apply_event() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO stock_current (
        nomenclature_code, quantity_on_hand, quantity_reserved,
        last_event_id, updated_at
    )
    VALUES (
        NEW.nomenclature_code, NEW.delta_on_hand, NEW.delta_reserved,
        NEW.id, now()
    )
    ON CONFLICT (nomenclature_code) DO UPDATE SET
        quantity_on_hand = stock_current.quantity_on_hand + NEW.delta_on_hand,
        quantity_reserved = stock_current.quantity_reserved + NEW.delta_reserved,
        last_event_id = NEW.id,
        updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_stock_event_apply
    AFTER INSERT ON stock_event
    FOR EACH ROW EXECUTE FUNCTION trg_stock_apply_event();


-- =====================================================================
-- Helper view: остаток + базовая инфа о товаре
-- =====================================================================

CREATE OR REPLACE VIEW stock_overview AS
SELECT
    sc.nomenclature_code,
    n.name AS nomenclature_name,
    n.sku AS sku,
    b.name AS brand_name,
    sc.quantity_on_hand,
    sc.quantity_reserved,
    sc.quantity_available,
    sc.updated_at AS stock_updated_at
FROM stock_current sc
JOIN nomenclature n ON n.code = sc.nomenclature_code
LEFT JOIN brand b ON b.id = n.brand_id;

COMMENT ON VIEW stock_overview IS 'Удобная view остатков с именами товара и бренда';


-- =====================================================================
-- Grants
-- =====================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON stock_current TO gluvex_app;
-- stock_event — INSERT only (append-only), UPDATE запрещаем
GRANT SELECT, INSERT ON stock_event TO gluvex_app;
GRANT USAGE, SELECT ON SEQUENCE stock_event_id_seq TO gluvex_app;
GRANT SELECT ON stock_overview TO gluvex_app;

-- ВАЖНО: REVOKE UPDATE/DELETE на stock_event — append-only гарантия
REVOKE UPDATE, DELETE ON stock_event FROM gluvex_app;

COMMIT;

\echo ''
\echo '== Migration 009 applied — stock =='
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('stock_current','stock_event')
UNION ALL
SELECT table_name FROM information_schema.views
WHERE table_name = 'stock_overview'
ORDER BY 1;
