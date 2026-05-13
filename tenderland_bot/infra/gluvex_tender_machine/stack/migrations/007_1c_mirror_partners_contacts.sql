-- =====================================================================
-- migration 007 — 1С-mirror: Партнёры + Контрагенты + КонтактныеЛица +
--                  общая шина КонтактнаяИнформация + EAV для всех
-- =====================================================================
-- Полная семантическая калька. Owner-цепочка:
--   Партнёр (центральная сущность бизнес-отношения)
--   ├─ Контрагент (юр.лицо/ИП/физлицо — может быть несколько на партнёра)
--   └─ КонтактноеЛицо (физлицо-сотрудник партнёра)
--
-- Контактная информация — общая polymorphic таблица для всех трёх.

BEGIN;

-- =====================================================================
-- Дополнительные reference catalogs
-- =====================================================================

CREATE TABLE business_region (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    parent_id uuid REFERENCES business_region(id),
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE business_region IS '1С: Catalog.БизнесРегионы';

CREATE TABLE delivery_zone (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE delivery_zone IS '1С: Catalog.ЗоныДоставки';

CREATE TABLE one_c_user (
    -- зеркало 1С Пользователи + ВнешниеПользователи (нужно для author_id, primary_manager_id)
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_external bool DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    email text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE one_c_user IS '1С: Catalog.Пользователи + ВнешниеПользователи (для FK author/manager)';

CREATE TABLE contact_kind (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    applies_to text,                              -- 'partner' / 'counterparty' / 'contact_person'
    contact_type_hint text,                       -- 'email' / 'phone' / 'address' / 'site' / ...
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE contact_kind IS '1С: Catalog.ВидыКонтактнойИнформации (рабочий/мобильный/etc.)';

CREATE TABLE contact_role (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE contact_role IS '1С: Catalog.РолиКонтактныхЛицПартнеров';

CREATE TABLE purpose (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    is_deleted bool NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE purpose IS '1С: Catalog.Назначения (напр. НазначениеПереработчика)';

CREATE TABLE price_type (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    one_c_ref uuid UNIQUE,
    code text,
    name text NOT NULL,
    currency currency_t,
    is_active bool DEFAULT true,
    is_deleted bool NOT NULL DEFAULT false,
    description text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);
COMMENT ON TABLE price_type IS '1С: Catalog.ВидыЦен (Закупочная / РРЦ / Договорная / Дилерская / ...)';

-- =====================================================================
-- ENUM types для Контактной Информации
-- =====================================================================

CREATE TYPE contact_owner_t AS ENUM ('partner', 'counterparty', 'contact_person');
COMMENT ON TYPE contact_owner_t IS 'Polymorphic discriminator — кому принадлежит контактная информация';

CREATE TYPE contact_type_t AS ENUM (
    'email', 'phone', 'address', 'site', 'fax', 'skype',
    'telegram', 'whatsapp', 'other'
);
COMMENT ON TYPE contact_type_t IS '1С: EnumRef.ТипыКонтактнойИнформации';


-- =====================================================================
-- partners — 1С Catalog.Партнёры
-- =====================================================================

CREATE TABLE partners (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE NOT NULL,
    name text NOT NULL,
    parent_code text REFERENCES partners(code),
    is_group bool NOT NULL DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    is_predefined bool NOT NULL DEFAULT false,
    predefined_data_name text,

    public_name text,                                              -- 1С: НаименованиеПолное
    business_region_id uuid REFERENCES business_region(id),
    access_group_id uuid REFERENCES access_group(id),
    registration_date timestamptz,
    is_customer bool NOT NULL DEFAULT false,
    is_supplier bool NOT NULL DEFAULT false,
    is_competitor bool NOT NULL DEFAULT false,
    is_carrier bool NOT NULL DEFAULT false,
    has_other_relationships bool NOT NULL DEFAULT false,
    served_by_sales_representatives bool NOT NULL DEFAULT false,

    comment text,
    additional_information text,
    primary_manager_id uuid REFERENCES one_c_user(id),

    label_template_id uuid,
    legal_entity_or_individual_type legal_entity_kind_t,            -- 1С: ЮрФизЛицо (Company/Private)
    gender gender_t,
    birth_date timestamptz,
    processor_assignment_id uuid REFERENCES purpose(id),
    electronic_receipt_sending_option text,                         -- 1С: ВариантОтправкиЭлектронногоЧека
    delivery_zone_id uuid REFERENCES delivery_zone(id),
    price_type_id uuid REFERENCES price_type(id),                   -- 1С: ВидЦен (дефолтный)
    individual_price_type_id uuid REFERENCES price_type(id),

    metadata jsonb DEFAULT '{}',
    one_c_imported_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE partners IS '1С УТ 11.5: Catalog.Партнёры — бизнес-отношения';
COMMENT ON COLUMN partners.code IS '1С: Code (внутренний код Партнёра)';
COMMENT ON COLUMN partners.one_c_ref IS '1С: Ref (UUID Партнёра)';
COMMENT ON COLUMN partners.name IS '1С: Description (Наименование)';
COMMENT ON COLUMN partners.public_name IS '1С: НаименованиеПолное (публичное имя)';
COMMENT ON COLUMN partners.is_customer IS '1С: Клиент';
COMMENT ON COLUMN partners.is_supplier IS '1С: Поставщик';
COMMENT ON COLUMN partners.is_competitor IS '1С: Конкурент';
COMMENT ON COLUMN partners.is_carrier IS '1С: Перевозчик';

CREATE INDEX idx_partners_parent ON partners(parent_code) WHERE parent_code IS NOT NULL;
CREATE INDEX idx_partners_active ON partners(is_deleted) WHERE is_deleted = false;
CREATE INDEX idx_partners_customer ON partners(is_customer) WHERE is_customer = true;
CREATE INDEX idx_partners_supplier ON partners(is_supplier) WHERE is_supplier = true;
CREATE INDEX idx_partners_manager ON partners(primary_manager_id) WHERE primary_manager_id IS NOT NULL;
CREATE INDEX idx_partners_name_trgm ON partners USING gin (name gin_trgm_ops);

CREATE TABLE partner_additional_attribute (
    partner_code text NOT NULL REFERENCES partners(code) ON DELETE CASCADE,
    property_id uuid NOT NULL REFERENCES property_definition(id),
    value jsonb,
    text_value text,
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (partner_code, property_id)
);
COMMENT ON TABLE partner_additional_attribute IS
'1С: TabularSection.ДополнительныеРеквизиты у Партнёра — EAV';


-- =====================================================================
-- counterparties — 1С Catalog.Контрагенты (юр.лица)
-- =====================================================================

CREATE TABLE counterparties (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE NOT NULL,
    name text NOT NULL,
    parent_code text REFERENCES counterparties(code),
    is_group bool NOT NULL DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    is_predefined bool NOT NULL DEFAULT false,
    predefined_data_name text,

    short_legal_name text,                                          -- 1С: НаименованиеПолное
    partner_code text NOT NULL REFERENCES partners(code),           -- 1С: Партнер (owner)
    is_separate_subdivision bool NOT NULL DEFAULT false,            -- 1С: ОбособленноеПодразделение
    legal_or_individual_person legal_entity_kind_t,                 -- 1С: ЮридическоеФизическоеЛицо
    registration_country_id uuid REFERENCES country(id),
    parent_counterparty_code text REFERENCES counterparties(code),  -- 1С: ГоловнойКонтрагент

    -- Российские реквизиты
    taxpayer_identification_number text,                            -- 1С: ИНН
    tax_registration_reason_code text,                              -- 1С: КПП
    okpo_code text,                                                 -- 1С: КодПоОКПО
    registration_number text,                                       -- 1С: РегистрационныйНомер (ОГРН)
    tax_number text,                                                -- 1С: НалоговыйНомер

    -- Международные
    international_name text,                                        -- 1С: НаименованиеМеждународное
    transliterated_name text,                                       -- 1С: НаименованиеВТранскрипции

    additional_information text,
    applies_vat_rates_4_and_2_legacy bool DEFAULT false,            -- 1С: УдалитьНДСПоСтавкам4и2 (legacy)

    metadata jsonb DEFAULT '{}',
    one_c_imported_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE counterparties IS '1С УТ 11.5: Catalog.Контрагенты — юр.лица и ИП';
COMMENT ON COLUMN counterparties.partner_code IS '1С: Партнер (FK на partners.code, owner)';
COMMENT ON COLUMN counterparties.taxpayer_identification_number IS '1С: ИНН';
COMMENT ON COLUMN counterparties.tax_registration_reason_code IS '1С: КПП';
COMMENT ON COLUMN counterparties.registration_number IS '1С: РегистрационныйНомер (ОГРН/ОГРНИП)';

CREATE INDEX idx_counterparties_partner ON counterparties(partner_code);
CREATE INDEX idx_counterparties_parent ON counterparties(parent_code) WHERE parent_code IS NOT NULL;
CREATE INDEX idx_counterparties_active ON counterparties(is_deleted) WHERE is_deleted = false;
CREATE UNIQUE INDEX idx_counterparties_inn ON counterparties(taxpayer_identification_number)
  WHERE taxpayer_identification_number IS NOT NULL AND is_deleted = false;
CREATE INDEX idx_counterparties_name_trgm ON counterparties USING gin (name gin_trgm_ops);
CREATE INDEX idx_counterparties_short_legal_trgm ON counterparties USING gin (short_legal_name gin_trgm_ops) WHERE short_legal_name IS NOT NULL;

-- Forward-fix: алкогольный импортёр у Номенклатуры — теперь можно повесить FK
ALTER TABLE nomenclature
    ADD CONSTRAINT fk_nomenclature_alcohol_importer
    FOREIGN KEY (alcohol_importer_counterparty_code) REFERENCES counterparties(code);

CREATE TABLE counterparty_additional_attribute (
    counterparty_code text NOT NULL REFERENCES counterparties(code) ON DELETE CASCADE,
    property_id uuid NOT NULL REFERENCES property_definition(id),
    value jsonb,
    text_value text,
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (counterparty_code, property_id)
);

CREATE TABLE counterparty_kpp_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    counterparty_code text NOT NULL REFERENCES counterparties(code) ON DELETE CASCADE,
    period timestamptz NOT NULL,
    tax_registration_reason_code text NOT NULL,
    UNIQUE (counterparty_code, period)
);
COMMENT ON TABLE counterparty_kpp_history IS '1С: TabularSection.ИсторияКПП';

CREATE TABLE counterparty_name_history (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    counterparty_code text NOT NULL REFERENCES counterparties(code) ON DELETE CASCADE,
    period timestamptz NOT NULL,
    short_name text NOT NULL,
    UNIQUE (counterparty_code, period)
);
COMMENT ON TABLE counterparty_name_history IS '1С: TabularSection.ИсторияНаименований';


-- =====================================================================
-- contact_persons — 1С Catalog.КонтактныеЛицаПартнеров
-- =====================================================================

CREATE TABLE contact_persons (
    code text PRIMARY KEY,
    one_c_ref uuid UNIQUE NOT NULL,
    name text NOT NULL,                                             -- ФИО
    parent_code text REFERENCES contact_persons(code),
    is_group bool NOT NULL DEFAULT false,
    is_deleted bool NOT NULL DEFAULT false,
    is_predefined bool NOT NULL DEFAULT false,
    predefined_data_name text,

    partner_code text NOT NULL REFERENCES partners(code),           -- 1С: Owner (Партнёр)

    relationship_registration_date timestamptz,                     -- 1С: ДатаРегистрацииСвязи
    relationship_termination_date timestamptz,                      -- 1С: ДатаПрекращенияСвязи (NULL = активен)
    author_id uuid REFERENCES one_c_user(id),                       -- 1С: Автор
    comment text,
    additional_information text,
    job_title_on_business_card text,                                -- 1С: ДолжностьПоВизитке
    gender gender_t,
    birth_date timestamptz,

    metadata jsonb DEFAULT '{}',
    one_c_imported_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE contact_persons IS '1С УТ 11.5: Catalog.КонтактныеЛицаПартнеров';
COMMENT ON COLUMN contact_persons.partner_code IS '1С: Owner (FK на partners.code)';
COMMENT ON COLUMN contact_persons.relationship_termination_date IS '1С: ДатаПрекращенияСвязи (NULL = активен)';

CREATE INDEX idx_contact_persons_partner ON contact_persons(partner_code);
CREATE INDEX idx_contact_persons_active ON contact_persons(is_deleted, relationship_termination_date)
  WHERE is_deleted = false AND relationship_termination_date IS NULL;
CREATE INDEX idx_contact_persons_name_trgm ON contact_persons USING gin (name gin_trgm_ops);

CREATE TABLE contact_person_additional_attribute (
    contact_person_code text NOT NULL REFERENCES contact_persons(code) ON DELETE CASCADE,
    property_id uuid NOT NULL REFERENCES property_definition(id),
    value jsonb,
    text_value text,
    updated_at timestamptz DEFAULT now(),
    PRIMARY KEY (contact_person_code, property_id)
);

CREATE TABLE contact_person_role (
    contact_person_code text NOT NULL REFERENCES contact_persons(code) ON DELETE CASCADE,
    contact_role_id uuid NOT NULL REFERENCES contact_role(id),
    PRIMARY KEY (contact_person_code, contact_role_id)
);
COMMENT ON TABLE contact_person_role IS '1С: TabularSection.РолиКонтактногоЛица — many-to-many';


-- =====================================================================
-- contact_information — общая polymorphic шина
-- =====================================================================

CREATE TABLE contact_information (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_entity_type contact_owner_t NOT NULL,
    owner_code text NOT NULL,
    contact_type contact_type_t NOT NULL,
    contact_kind_id uuid REFERENCES contact_kind(id),               -- 1С: Вид (детализация типа)
    presentation text,                                              -- 1С: Представление (краткое отображение)
    field_values text,                                              -- 1С: ЗначенияПолей (структурированное)
    country text,
    region text,
    city text,
    email_address text,
    server_domain_name text,
    phone_number text,
    phone_number_without_codes text,
    list_view_kind_id uuid REFERENCES contact_kind(id),             -- 1С: ВидДляСписка
    effective_from timestamptz,                                     -- только для Контрагентов: ДействуетС
    value text,
    metadata jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE contact_information IS
'1С: TabularSection.КонтактнаяИнформация — polymorphic, для Партнёра/Контрагента/КонтактногоЛица';
COMMENT ON COLUMN contact_information.owner_entity_type IS 'Тип owner-сущности (discriminator)';
COMMENT ON COLUMN contact_information.owner_code IS 'Code в соответствующей таблице (partners/counterparties/contact_persons)';

CREATE INDEX idx_contact_information_owner ON contact_information(owner_entity_type, owner_code);
CREATE INDEX idx_contact_information_type ON contact_information(contact_type);
CREATE INDEX idx_contact_information_email ON contact_information(LOWER(email_address))
  WHERE email_address IS NOT NULL;
CREATE INDEX idx_contact_information_phone ON contact_information(phone_number_without_codes)
  WHERE phone_number_without_codes IS NOT NULL;


-- =====================================================================
-- Triggers updated_at
-- =====================================================================

CREATE TRIGGER trg_partners_set_updated_at
    BEFORE UPDATE ON partners
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_counterparties_set_updated_at
    BEFORE UPDATE ON counterparties
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_contact_persons_set_updated_at
    BEFORE UPDATE ON contact_persons
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();

CREATE TRIGGER trg_contact_information_set_updated_at
    BEFORE UPDATE ON contact_information
    FOR EACH ROW EXECUTE FUNCTION trg_nomenclature_updated_at();


-- =====================================================================
-- Grants
-- =====================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON
    partners, partner_additional_attribute,
    counterparties, counterparty_additional_attribute,
    counterparty_kpp_history, counterparty_name_history,
    contact_persons, contact_person_additional_attribute, contact_person_role,
    contact_information,
    business_region, delivery_zone, one_c_user, contact_kind, contact_role,
    purpose, price_type
TO gluvex_app;

COMMIT;

\echo ''
\echo '== Migration 007 applied =='
SELECT 'partners' AS t, COUNT(*) AS columns FROM information_schema.columns WHERE table_name = 'partners'
UNION ALL SELECT 'counterparties', COUNT(*) FROM information_schema.columns WHERE table_name = 'counterparties'
UNION ALL SELECT 'contact_persons', COUNT(*) FROM information_schema.columns WHERE table_name = 'contact_persons'
UNION ALL SELECT 'contact_information', COUNT(*) FROM information_schema.columns WHERE table_name = 'contact_information';
