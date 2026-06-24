-- =====================================================================
-- migration 006 — 1С-mirror: Nomenclature + reference catalogs + ENUMs + EAV
-- =====================================================================
-- Зеркальная копия Номенклатуры из 1С УТ 11.5. Полная семантическая
-- калька, English snake_case имена, русские синонимы в COMMENT ON COLUMN.
-- Источник истины — 1С. Cross-system join key = nomenclature.code.
--
-- См. docs/1c-mirror-schema.md для полного mapping.
-- См. catalog-architecture.md для существующей `product` (crawler-driven).
-- Здесь новые таблицы, существующая `product` пока не трогаем.

BEGIN;

-- =====================================================================
-- ENUM types
-- =====================================================================

CREATE TYPE item_type_t AS ENUM (
    'product', 'service', 'container', 'set', 'work', 'other'
);
COMMENT ON TYPE item_type_t IS '1С: EnumRef.ТипыНоменклатуры (Товар/Услуга/Тара/Набор/Работа/Прочее)';

CREATE TYPE time_unit_t AS ENUM ('hour', 'day', 'month', 'year');
COMMENT ON TYPE time_unit_t IS '1С: EnumRef.ЕдиницыИзмеренияВремени';

CREATE TYPE variant_usage_mode_t AS ENUM (
    'none', 'common', 'individual', 'common_for_kind'
);
COMMENT ON TYPE variant_usage_mode_t IS '1С: EnumRef.ВариантыИспользованияХарактеристикНоменклатуры';

CREATE TYPE legal_entity_kind_t AS ENUM (
    'company', 'private_person', 'individual_entrepreneur', 'foreign_company'
);
COMMENT ON TYPE legal_entity_kind_t IS '1С: EnumRef.ЮрФизЛицо / КомпанияЧастноеЛицо';

CREATE TYPE gender_t AS ENUM ('male', 'female', 'not_specified');
COMMENT ON TYPE gender_t IS '1С: EnumRef.ПолФизическогоЛица';

CREATE TYPE property_value_type_t AS ENUM (
    'string', 'number', 'boolean', 'date', 'datetime', 'reference', 'enum'
);
COMMENT ON TYPE property_value_type_t IS 'Тип значения свойства EAV (ДополнительныеРеквизиты)';


-- =====================================================================
-- Reference catalogs — мини-справочники из 1С
-- =====================================================================

-- Все справочники имеют единообразную структуру:
--   id uuid PK, one_c_ref uuid UNIQUE, code text, name text, ...

CREATE TABLE brand (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE brand IS '1С: Catalog.Марки (бренды/торговые марки)';

CREATE TABLE manufacturer (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE manufacturer IS '1С: Catalog.Производители';

CREATE TABLE country (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    alpha2 text,
    alpha3 text,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE country IS '1С: Catalog.СтраныМира';

CREATE TABLE unit_of_measure (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    short_name text,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE unit_of_measure IS '1С: Catalog.УпаковкиЕдиницыИзмерения';

CREATE TABLE vat_rate (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    rate numeric(5,2),
    is_active bool DEFAULT true,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE vat_rate IS '1С: Catalog.СтавкиНДС';

CREATE TABLE item_kind (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    parent_id uuid REFERENCES item_kind(id),
    is_deleted bool NOT NULL DEFAULT false,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE item_kind IS '1С: Catalog.ВидыНоменклатуры';

CREATE TABLE product_category_1c (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    parent_id uuid REFERENCES product_category_1c(id),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE product_category_1c IS
'1С: Catalog.ТоварныеКатегории — категоризация Глювекса в 1С (≠ нашему product.category enum)';

CREATE TABLE warehouse_group (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE warehouse_group IS '1С: Catalog.СкладскиеГруппыНоменклатуры';

CREATE TABLE quality_grade (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE quality_grade IS '1С: EnumRef.ГрадацииКачества';

CREATE TABLE hs_code (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE,
    name text NOT NULL,
    parent_code text REFERENCES hs_code(code),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE hs_code IS '1С: Catalog.КлассификаторТНВЭД — критично для гос.тендеров';

CREATE TABLE okpd2_code (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE,
    name text NOT NULL,
    parent_code text REFERENCES okpd2_code(code),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE okpd2_code IS '1С: Catalog.КлассификаторОКПД2 — критично для гос.тендеров';

CREATE TABLE okp_code (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE,
    name text NOT NULL,
    parent_code text REFERENCES okp_code(code),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE okp_code IS '1С: Catalog.ОбщероссийскийКлассификаторПродукции';

CREATE TABLE okved2_code (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE,
    name text NOT NULL,
    parent_code text REFERENCES okved2_code(code),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE okved2_code IS '1С: Catalog.КлассификаторОКВЭД2';

CREATE TABLE price_group (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE price_group IS '1С: Catalog.ЦеновыеГруппы';

CREATE TABLE season_group (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE season_group IS '1С: Catalog.СезонныеГруппы';

CREATE TABLE access_group (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    applies_to text,    -- 'nomenclature' / 'partner' / ...
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE access_group IS '1С: Catalog.ГруппыДоступа* (Номенклатуры, Партнёров, ...)';

-- Словарь свойств для EAV (ДополнительныеРеквизиты)
CREATE TABLE property_definition (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    applies_to text,                          -- 'nomenclature' / 'partner' / ...
    value_type property_value_type_t NOT NULL DEFAULT 'string',
    reference_type text,                      -- для value_type='reference' — имя 1С каталога
    enum_values text[],                       -- для value_type='enum'
    is_required bool DEFAULT false,
    is_multilingual bool DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    description text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE property_definition IS
'1С: ChartOfCharacteristicTypes.ДополнительныеРеквизитыИСведения — словарь EAV-свойств';


-- =====================================================================
-- Nomenclature — главная таблица, зеркало 1С Catalog.Номенклатура
-- =====================================================================

CREATE TABLE nomenclature (
    -- ====== СТАНДАРТНЫЕ РЕКВИЗИТЫ КАТАЛОГА ======
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE NOT NULL,
    name text NOT NULL,
    parent_code text REFERENCES nomenclature(code),
    is_group bool NOT NULL DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    is_predefined bool NOT NULL DEFAULT false,
    predefined_data_name text,

    -- ====== ОСНОВНЫЕ РЕКВИЗИТЫ ======
    sku text,                                                       -- 1С: Артикул (G7117B, LCMS-8060)
    full_name text,                                                 -- 1С: НаименованиеПолное (для печати)
    description_text text,                                          -- 1С: Описание
    search_code text,                                               -- 1С: КодДляПоиска

    item_type item_type_t,                                          -- 1С: ТипНоменклатуры
    item_kind_id uuid REFERENCES item_kind(id),                     -- 1С: ВидНоменклатуры
    brand_id uuid REFERENCES brand(id),                             -- 1С: Марка
    manufacturer_id uuid REFERENCES manufacturer(id),               -- 1С: Производитель
    country_of_origin_id uuid REFERENCES country(id),               -- 1С: СтранаПроисхождения
    storage_unit_id uuid REFERENCES unit_of_measure(id),            -- 1С: ЕдиницаИзмерения (хранения)
    reporting_unit_id uuid REFERENCES unit_of_measure(id),          -- 1С: ЕдиницаДляОтчетов
    reporting_unit_coefficient numeric(15,4),                       -- 1С: КоэффициентЕдиницыДляОтчетов
    product_category_1c_id uuid REFERENCES product_category_1c(id), -- 1С: ТоварнаяКатегория
    warehouse_group_id uuid REFERENCES warehouse_group(id),         -- 1С: СкладскаяГруппа

    vat_rate_id uuid REFERENCES vat_rate(id),                       -- 1С: СтавкаНДС
    quality_grade_id uuid REFERENCES quality_grade(id),             -- 1С: Качество

    -- Сроки годности
    shelf_life numeric(10,2),                                       -- 1С: СрокГодности
    shelf_life_unit time_unit_t,                                    -- 1С: ЕдиницаИзмеренияСрокаГодности

    -- Прослеживаемость и сертификаты
    is_traceable_product bool NOT NULL DEFAULT false,               -- 1С: ПрослеживаемыйТовар
    track_certificates bool NOT NULL DEFAULT false,                 -- 1С: ВестиУчетСертификатовНоменклатуры
    track_by_customs_declaration bool NOT NULL DEFAULT false,       -- 1С: ВестиУчетПоГТД

    -- РУ Росздравнадзора (упрощено от EAV — три прямых поля)
    has_ru bool NOT NULL DEFAULT false,                             -- Расширение Глювекса
    ru_number text,                                                 -- Расширение Глювекса
    ru_received_date date,                                          -- Расширение Глювекса

    -- Характеристики (варианты конфигураций)
    variant_usage_mode variant_usage_mode_t,                        -- 1С: ИспользованиеХарактеристик
    variant_settings_owner_id uuid REFERENCES item_kind(id),        -- 1С: ВладелецХарактеристик
    serial_settings_owner_id uuid REFERENCES item_kind(id),         -- 1С: ВладелецСерий
    product_category_owner_id uuid REFERENCES item_kind(id),        -- 1С: ВладелецТоварныхКатегорий

    -- Классификаторы (критично для гос.тендеров)
    hs_code text REFERENCES hs_code(code),                          -- 1С: КодТНВЭД
    okpd2_code text REFERENCES okpd2_code(code),                    -- 1С: КодОКПД2
    okved2_code text REFERENCES okved2_code(code),                  -- 1С: КодОКВЭД2
    okp_code text REFERENCES okp_code(code),                        -- 1С: КодОКП
    tru_code text,                                                  -- 1С: КодТРУ
    kvpd_code text,                                                 -- 1С: КодПоКВПД
    hs_unit_id uuid REFERENCES unit_of_measure(id),                 -- 1С: ЕдиницаИзмеренияТНВЭД
    item_classification_type_code text,                             -- 1С: КодВидаНоменклатурнойКлассификации
    item_classification_type_name text,                             -- 1С: НаименованиеВидаНоменклатурнойКлассификации

    -- Размеры — вес (8 полей пары числитель/знаменатель)
    weight_numerator numeric(15,4),
    weight_denominator numeric(15,4),
    weight_unit_id uuid REFERENCES unit_of_measure(id),
    use_weight bool DEFAULT false,
    allow_weight_in_documents bool DEFAULT false,

    -- Размеры — длина
    length_numerator numeric(15,4),
    length_denominator numeric(15,4),
    length_unit_id uuid REFERENCES unit_of_measure(id),
    use_length bool DEFAULT false,
    allow_length_in_documents bool DEFAULT false,

    -- Размеры — объем
    volume_numerator numeric(15,4),
    volume_denominator numeric(15,4),
    volume_unit_id uuid REFERENCES unit_of_measure(id),
    use_volume bool DEFAULT false,
    allow_volume_in_documents bool DEFAULT false,
    volume_decaliters numeric(15,4),                                -- для алкогольной продукции

    -- Размеры — площадь
    area_numerator numeric(15,4),
    area_denominator numeric(15,4),
    area_unit_id uuid REFERENCES unit_of_measure(id),
    use_area bool DEFAULT false,
    allow_area_in_documents bool DEFAULT false,

    -- Алкогольная продукция (резервируем, у Глювекса не используется но для совместимости с 1С)
    is_alcohol_product bool DEFAULT false,
    is_imported_alcohol_product bool DEFAULT false,
    is_open_container_alcohol_product bool DEFAULT false,
    alcohol_strength numeric(5,2),
    alcohol_importer_counterparty_code text,                        -- FK на counterparties (создаётся в migration 007)
    alcohol_product_type_id uuid,                                   -- 1С: ВидАлкогольнойПродукции

    -- ГИСМ (маркировка)
    is_gism_marked_product bool DEFAULT false,
    gism_identification_mark bool DEFAULT false,
    gism_mark_type text,
    gism_mark_release_method text,
    gism_mark_gtin text,
    gism_mark_size text,

    -- ВетИС
    is_vetis_controlled_product bool DEFAULT false,

    -- Прочее
    is_excise_product_legacy bool DEFAULT false,                    -- 1С: УдалитьПодакцизныйТовар (legacy)
    is_mineral_tax_percent_based bool DEFAULT false,                -- 1С: ОблагаетсяНДПИПоПроцентнойСтавке
    vat_paid_by_buyer bool DEFAULT false,                           -- 1С: ОблагаетсяНДСУПокупателя
    vat_section_7_code text,                                        -- 1С: КодРаздел7ДекларацииНДС
    vat_zero_rate_operations text,                                  -- 1С: Операции0
    requires_sale_permission bool DEFAULT false,                    -- 1С: ПродаетсяПоРазрешению
    control_received_goods_quality bool DEFAULT false,
    quality_control_period numeric(10,2),

    -- Финансовый учёт
    financial_accounting_group_id uuid,                             -- 1С: ГруппаФинансовогоУчета
    analytical_accounting_group_id uuid,                            -- 1С: ГруппаАналитическогоУчета
    accounting_feature text,                                        -- 1С: ОсобенностьУчета
    sales_processing_option text,                                   -- 1С: ВариантОформленияПродажи

    -- Доступ
    access_group_id uuid REFERENCES access_group(id),               -- 1С: ГруппаДоступа

    -- Изображения и файлы
    image_file_id text,                                             -- 1С: ФайлКартинки
    website_description_file_id text,                               -- 1С: ФайлОписанияДляСайта
    label_template_id uuid,                                         -- 1С: ШаблонЭтикетки
    price_tag_template_id uuid,                                     -- 1С: ШаблонЦенника
    use_individual_price_tag_template bool DEFAULT false,
    use_individual_label_template bool DEFAULT false,

    -- Прочие классификаторы
    sales_rating_id uuid,                                           -- 1С: РейтингПродаж
    collection_id uuid,                                             -- 1С: КоллекцияНоменклатуры (сезон)
    season_group_id uuid REFERENCES season_group(id),
    price_group_id uuid REFERENCES price_group(id),

    -- Обеспечение
    supply_scheme_id uuid,                                          -- 1С: СхемаОбеспечения
    supply_method text,                                             -- 1С: СпособОбеспеченияПотребностей
    dedicated_procurement_and_sale bool DEFAULT false,              -- 1С: ОбособленнаяЗакупкаПродажа

    -- Многооборотная тара
    returnable_container_item_code text,                            -- 1С: НоменклатураМногооборотнаяТара
    returnable_container_variant_id uuid,                           -- 1С: ХарактеристикаМногооборотнаяТара
    supplied_in_returnable_container bool DEFAULT false,

    -- Прочее
    has_other_quality_items bool DEFAULT false,                     -- 1С: ЕстьТоварыДругогоКачества
    use_packaging_sets bool DEFAULT false,                          -- 1С: ИспользоватьУпаковки
    packaging_set_id uuid,                                          -- 1С: НаборУпаковок
    principal_code text,                                            -- 1С: Принципал (комиссия)
    counterparty_code text,                                         -- 1С: Контрагент (комиссия)

    -- Метаданные миграции
    metadata jsonb DEFAULT '{}',
    one_c_imported_at timestamptz,
    one_c_source text DEFAULT '1c_ut115',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE nomenclature IS
'1С УТ 11.5: Catalog.Номенклатура — полный mirror. Source of truth = 1С.';
COMMENT ON COLUMN nomenclature.code IS '1С: Code (внутренний код Глювекса, join key)';
COMMENT ON COLUMN nomenclature.one_c_ref IS '1С: Ref (UUID в 1С)';
COMMENT ON COLUMN nomenclature.name IS '1С: Description (Наименование)';
COMMENT ON COLUMN nomenclature.parent_code IS '1С: Parent (Родитель)';
COMMENT ON COLUMN nomenclature.is_group IS '1С: IsFolder (Это группа)';
COMMENT ON COLUMN nomenclature.is_deleted IS '1С: DeletionMark (Пометка удаления)';
COMMENT ON COLUMN nomenclature.sku IS '1С: Артикул (артикул производителя — G7117B)';
COMMENT ON COLUMN nomenclature.full_name IS '1С: НаименованиеПолное (для печати/КП)';
COMMENT ON COLUMN nomenclature.description_text IS '1С: Описание (текстовое)';
COMMENT ON COLUMN nomenclature.search_code IS '1С: КодДляПоиска';
COMMENT ON COLUMN nomenclature.brand_id IS '1С: Марка (FK на brand)';
COMMENT ON COLUMN nomenclature.manufacturer_id IS '1С: Производитель (FK на manufacturer)';
COMMENT ON COLUMN nomenclature.has_ru IS 'Расширение Глювекса: есть ли РУ Росздравнадзора';
COMMENT ON COLUMN nomenclature.ru_number IS 'Расширение Глювекса: номер РУ (когда has_ru=true)';
COMMENT ON COLUMN nomenclature.ru_received_date IS 'Расширение Глювекса: дата получения РУ';
COMMENT ON COLUMN nomenclature.hs_code IS '1С: КодТНВЭД (для гос.тендеров)';
COMMENT ON COLUMN nomenclature.okpd2_code IS '1С: КодОКПД2 (для гос.тендеров)';
COMMENT ON COLUMN nomenclature.tru_code IS '1С: КодТРУ (для гос.закупок)';

-- Индексы
CREATE INDEX idx_nomenclature_parent ON nomenclature(parent_code) WHERE parent_code IS NOT NULL;
CREATE INDEX idx_nomenclature_brand ON nomenclature(brand_id) WHERE brand_id IS NOT NULL;
CREATE INDEX idx_nomenclature_manufacturer ON nomenclature(manufacturer_id) WHERE manufacturer_id IS NOT NULL;
CREATE INDEX idx_nomenclature_sku ON nomenclature(sku) WHERE sku IS NOT NULL;
CREATE INDEX idx_nomenclature_is_group ON nomenclature(is_group);
CREATE INDEX idx_nomenclature_active ON nomenclature(is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_nomenclature_has_ru ON nomenclature(has_ru) WHERE has_ru = true;
CREATE INDEX idx_nomenclature_hs_code ON nomenclature(hs_code) WHERE hs_code IS NOT NULL;
CREATE INDEX idx_nomenclature_okpd2 ON nomenclature(okpd2_code) WHERE okpd2_code IS NOT NULL;
CREATE INDEX idx_nomenclature_tru ON nomenclature(tru_code) WHERE tru_code IS NOT NULL;
-- GIN trgm индексы для FTS
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_nomenclature_name_trgm ON nomenclature USING gin (name gin_trgm_ops);
CREATE INDEX idx_nomenclature_full_name_trgm ON nomenclature USING gin (full_name gin_trgm_ops) WHERE full_name IS NOT NULL;
CREATE INDEX idx_nomenclature_sku_trgm ON nomenclature USING gin (sku gin_trgm_ops) WHERE sku IS NOT NULL;


-- =====================================================================
-- Tabular parts — Дополнительные реквизиты (EAV) и Представления
-- =====================================================================

CREATE TABLE nomenclature_additional_attribute (
    nomenclature_code text NOT NULL REFERENCES nomenclature(code) ON DELETE CASCADE,
    property_id uuid NOT NULL REFERENCES property_definition(id),
    value jsonb,                            -- типизированное значение
    text_value text,                        -- сырое строковое представление (как в 1С)
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (nomenclature_code, property_id)
);
COMMENT ON TABLE nomenclature_additional_attribute IS
'1С: TabularSection.ДополнительныеРеквизиты у Номенклатуры — EAV ключ-значение';

CREATE INDEX idx_nomenclature_attr_property ON nomenclature_additional_attribute(property_id);
CREATE INDEX idx_nomenclature_attr_value ON nomenclature_additional_attribute USING gin(value);

CREATE TABLE nomenclature_presentation (
    nomenclature_code text NOT NULL REFERENCES nomenclature(code) ON DELETE CASCADE,
    language_code text NOT NULL,            -- 'ru', 'en', 'zh', 'de', ...
    full_name text,
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (nomenclature_code, language_code)
);
COMMENT ON TABLE nomenclature_presentation IS
'1С: TabularSection.Представления у Номенклатуры — переводы НаименованиеПолное';

CREATE TABLE nomenclature_precious_material (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nomenclature_code text NOT NULL REFERENCES nomenclature(code) ON DELETE CASCADE,
    precious_material text NOT NULL,        -- 1С: ДрагоценныйМатериал (текст)
    quantity numeric(15,4),
    unit_id uuid REFERENCES unit_of_measure(id),
    placement_classification text,          -- 1С: Расположение (для 1-ДМ)
    comment text
);
COMMENT ON TABLE nomenclature_precious_material IS
'1С: TabularSection.ДрагоценныеМатериалы у Номенклатуры';


-- =====================================================================
-- Trigger для updated_at
-- =====================================================================

CREATE OR REPLACE FUNCTION trg_nomenclature_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_nomenclature_set_updated_at
    BEFORE UPDATE ON nomenclature
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_brand_set_updated_at
    BEFORE UPDATE ON brand
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_manufacturer_set_updated_at
    BEFORE UPDATE ON manufacturer
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();


-- =====================================================================
-- Grants для gluvex_app роли (приложений)
-- =====================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON
    nomenclature, nomenclature_additional_attribute,
    nomenclature_presentation, nomenclature_precious_material,
    brand, manufacturer, country, unit_of_measure, vat_rate,
    item_kind, product_category_1c, warehouse_group, quality_grade,
    hs_code, okpd2_code, okp_code, okved2_code,
    price_group, season_group, access_group, property_definition
TO gluvex_app;

COMMIT;

-- =====================================================================
-- Verification (вне транзакции)
-- =====================================================================
\echo ''
\echo '== Migration 006 applied — sanity check =='
SELECT 'nomenclature' AS table_name, COUNT(*) AS columns
FROM information_schema.columns WHERE table_name = 'nomenclature';
SELECT 'reference tables' AS group_name, COUNT(*) AS n FROM information_schema.tables
WHERE table_name IN ('brand','manufacturer','country','unit_of_measure','vat_rate',
                     'item_kind','product_category_1c','warehouse_group','quality_grade',
                     'hs_code','okpd2_code','okp_code','okved2_code',
                     'price_group','season_group','access_group','property_definition');
