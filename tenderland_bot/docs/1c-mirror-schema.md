# 1С УТ 11.5 → Gluvex Postgres mirror — спецификация

**Версия:** 1.0
**Дата:** 2026-05-13
**Связанные миграции:** `006_1c_mirror_nomenclature.sql`, `007_1c_mirror_partners_contacts.sql`, `008_pricing.sql`, `009_stock.sql`

## Принципы

1. **1С — source of truth** для всех сущностей которые там ведутся. У нас полная зеркальная копия.
2. **Join key = `Code`** (внутренний код Глювекса, alphanumeric `text`). Используется везде: Postgres ↔ Twenty CRM ↔ MinIO ↔ MemPalace ↔ tender pipeline.
3. **Поля переименованы** с русских CamelCase 1С → English snake_case Postgres. Соответствие фиксируется через `COMMENT ON COLUMN` (русский синоним) + эту таблицу.
4. **Twenty CRM custom fields** используют English camelCase + русский label.
5. **MemPalace tags** содержат оба имени для двуязычного поиска: `[ru]:наименование_полное`, `[en]:full_name`.
6. **Идемпотентные UPSERT** при синхронизации по `Code`.
7. **Все ENUM из 1С** реплицированы как Postgres `ENUM` типы.
8. **EAV (`ДополнительныеРеквизиты`)** — отдельные таблицы `<entity>_additional_attribute` с FK на `property_definition`.

## Сводная таблица сущностей

| 1С Сущность | Postgres table | 1C-Ref Owner | Twenty CRM mirror |
|---|---|---|---|
| Номенклатура | `nomenclature` | — | (нет, продукты не в CRM) |
| Партнёры | `partners` | — | `Company` extended |
| Контрагенты | `counterparties` | Партнёр | `Company` extended (or related Company) |
| КонтактныеЛица | `contact_persons` | Партнёр | `Person` |
| КонтактнаяИнформация | `contact_information` | Партнёр/Контрагент/КонтактноеЛицо | inline в Twenty |

## Сводный mapping полей

### Номенклатура / Nomenclature

**Standard catalog fields (универсальны для всех 1С каталогов):**

| 1С имя | Русский синоним | Postgres column | Тип PG | 1С тип | Notes |
|---|---|---|---|---|---|
| `Ref` | Ссылка | `one_c_ref` | uuid UNIQUE | CatalogRef | UUID 1С |
| `Code` | Код | `code` | text PK | xs:string | **Join key** |
| `Description` | Наименование | `name` | text NOT NULL | xs:string | короткое имя |
| `Parent` | Родитель | `parent_code` | text REF nomenclature(code) | CatalogRef | NULL для root |
| `IsFolder` | Это группа | `is_group` | bool NOT NULL DEFAULT false | xs:boolean | true = категория, false = товар |
| `DeletionMark` | Пометка удаления | `is_deleted` | bool NOT NULL DEFAULT false | xs:boolean | soft delete |
| `Predefined` | Предопределенный | `is_predefined` | bool NOT NULL DEFAULT false | xs:boolean | системные группы |
| `PredefinedDataName` | Имя предопределенных данных | `predefined_data_name` | text | xs:string | имя для системных |

**Main fields Номенклатуры:**

| 1С имя | Русский синоним | Postgres column | Тип PG | Notes |
|---|---|---|---|---|
| `Артикул` | Артикул | `sku` | text | артикул производителя — `G7117B`, `LCMS-8060` etc. |
| `НаименованиеПолное` | Наименование для печати | `full_name` | text | длинное имя для печати/КП |
| `Описание` | Текстовое описание | `description_text` | text | |
| `КодДляПоиска` | Код для поиска | `search_code` | text | + GIN trgm индекс |
| `ТипНоменклатуры` | Тип номенклатуры | `item_type` | item_type_t ENUM | `Товар`/`Услуга`/`Тара`/`Набор`/etc |
| `ВидНоменклатуры` | Вид номенклатуры | `item_kind_id` | uuid REF item_kind(id) | классификатор Глювекса |
| `Марка` | Марка (бренд) | `brand_id` | uuid REF brand(id) | trademark — "Agilent", "Shimadzu" |
| `Производитель` | Производитель | `manufacturer_id` | uuid REF manufacturer(id) | юр.лицо производителя |
| `СтранаПроисхождения` | Страна происхождения | `country_of_origin_id` | uuid REF country(id) | ISO-страна |
| `ЕдиницаИзмерения` | Единица хранения | `storage_unit_id` | uuid REF unit_of_measure(id) | шт/кг/л/упак |
| `ТоварнаяКатегория` | Товарная категория | `product_category_1c_id` | uuid REF product_category_1c(id) | классификатор Глювекса (≠ наш `category` enum) |
| `СкладскаяГруппа` | Складская группа | `warehouse_group_id` | uuid REF warehouse_group(id) | |
| `СтавкаНДС` | Ставка НДС | `vat_rate_id` | uuid REF vat_rate(id) | 0% / 10% / 20% / Без НДС |
| `СрокГодности` | Срок годности | `shelf_life` | numeric(10,2) | в единицах `shelf_life_unit_id` |
| `ЕдиницаИзмеренияСрокаГодности` | Единица срока годности | `shelf_life_unit` | time_unit_t ENUM | день/месяц/год |
| `Качество` | Качество | `quality_grade_id` | uuid REF quality_grade(id) | |
| `ПрослеживаемыйТовар` | Прослеживаемый товар | `is_traceable_product` | bool DEFAULT false | для маркировки |
| `ВестиУчетСертификатовНоменклатуры` | Вести учёт сертификатов | `track_certificates` | bool DEFAULT false | |
| `ИспользованиеХарактеристик` | Использование характеристик | `variant_usage_mode` | variant_usage_mode_t ENUM | |
| `ВладелецХарактеристик` | Владелец характеристик | `variant_settings_owner_id` | uuid REF item_kind(id) | |
| **(Глювекс-extension)** | **РУ Росздравнадзора есть** | `has_ru` | bool NOT NULL DEFAULT false | упрощение от EAV |
| **(Глювекс-extension)** | **РУ номер** | `ru_number` | text | "РЗН 2013/1350" |
| **(Глювекс-extension)** | **РУ дата получения** | `ru_received_date` | date | дата выдачи |
| `КодТНВЭД` | ТН ВЭД | `hs_code_id` | uuid REF hs_code(id) | для гос.тендеров |
| `КодОКПД2` | ОКПД 2 | `okpd2_code_id` | uuid REF okpd2_code(id) | для гос.тендеров |
| `КодОКВЭД2` | ОКВЭД 2 | `okved2_code` | text | |
| `КодОКП` | ОКП | `okp_code_id` | uuid REF okp_code(id) | |
| `КодТРУ` | ТРУ | `tru_code` | text | для гос.закупок |
| `КодВидаНоменклатурнойКлассификации` | Вид номен. классификации | `item_classification_type_code` | text | |
| `НаименованиеВидаНоменклатурнойКлассификации` | Наим. вида классификации | `item_classification_type_name` | text | |

**Размеры и вес (8 групп по 4 поля):**

| 1С группы | Postgres | Notes |
|---|---|---|
| `ВесЧислитель / ВесЗнаменатель / ВесЕдиницаИзмерения / ВесИспользовать / ВесМожноУказывать` | `weight_numerator`, `weight_denominator`, `weight_unit_id`, `use_weight`, `allow_weight_in_documents` | |
| `Длина...` 5 полей | `length_*` | |
| `Объем...` 6 полей | `volume_*` (+ `volume_decaliters` для алко) | |
| `Площадь...` 5 полей | `area_*` | |

**Изображения / файлы:**

| 1С | Postgres |
|---|---|
| `ФайлКартинки` | `image_file_id` text (1C ref) |
| `ФайлОписанияДляСайта` | `website_description_file_id` text |

**Алкоголь / маркировка ГИСМ / ВетИС** — оставляем все поля как в 1С, хоть и не используются Глювексом. Это будущая адаптивность.

**Tabular parts:**

1. **`nomenclature_additional_attribute`** (EAV — ДополнительныеРеквизиты):
   ```sql
   nomenclature_code text REF nomenclature(code) ON DELETE CASCADE,
   property_id uuid REF property_definition(id),
   value jsonb,           -- typed value (string/number/bool/date/ref)
   text_value text,       -- сырое представление
   PRIMARY KEY (nomenclature_code, property_id)
   ```

2. **`nomenclature_presentation`** (Представления — переводы):
   ```sql
   nomenclature_code text REF nomenclature(code),
   language_code text,   -- 'ru', 'en', 'zh', 'de', ...
   full_name text,
   PRIMARY KEY (nomenclature_code, language_code)
   ```

3. **`nomenclature_precious_material`** (Драгоценные металлы) — если будет применимо.

---

### Партнёры / Partners

| 1С | Postgres | Notes |
|---|---|---|
| `Ref` | `one_c_ref` uuid UNIQUE | |
| `Code` | `code` text PK | внутренний код Партнёра |
| `Description` | `name` text NOT NULL | |
| `НаименованиеПолное` | `public_name` text | публичное имя для маркетинга |
| `Parent` | `parent_code` text REF self | |
| `IsFolder` | `is_group` bool | |
| `DeletionMark` | `is_deleted` bool | |
| `БизнесРегион` | `business_region_id` uuid REF business_region | |
| `ГруппаДоступа` | `access_group_id` uuid REF access_group | |
| `ДатаРегистрации` | `registration_date` timestamptz | |
| `Клиент` | `is_customer` bool | |
| `Поставщик` | `is_supplier` bool | |
| `Конкурент` | `is_competitor` bool | |
| `Перевозчик` | `is_carrier` bool | |
| `ПрочиеОтношения` | `has_other_relationships` bool | |
| `Комментарий` | `comment` text | |
| `ДополнительнаяИнформация` | `additional_information` text | |
| `ОсновнойМенеджер` | `primary_manager_id` uuid REF user(id) | |
| `ОбслуживаетсяТорговымиПредставителями` | `served_by_sales_representatives` bool | |
| `ЮрФизЛицо` | `legal_entity_or_individual_type` legal_entity_kind_t ENUM | `company` / `private_person` |
| `Пол` | `gender` gender_t ENUM | (для физлиц) |
| `ДатаРождения` | `birth_date` date | (для физлиц) |
| `ВидЦен` | `price_type_id` uuid REF price_type(id) | дефолтный прайс для этого партнёра |
| `ИндивидуальныйВидЦены` | `individual_price_type_id` uuid REF price_type(id) | |
| `ВариантОтправкиЭлектронногоЧека` | `electronic_receipt_sending_option` ENUM | |
| `ЗонаДоставки` | `delivery_zone_id` uuid REF delivery_zone(id) | |
| `ШаблонЭтикетки` | `label_template_id` uuid REF label_template(id) | |
| `НазначениеПереработчика` | `processor_assignment_id` uuid REF purpose(id) | |

**Tabular parts:**
- `partner_additional_attribute` — EAV
- `partner_contact_information` — общая шина связи

---

### Контрагенты / Counterparties

| 1С | Postgres | Notes |
|---|---|---|
| `Ref` | `one_c_ref` uuid UNIQUE | |
| `Code` | `code` text PK | |
| `Description` | `name` text NOT NULL | |
| `НаименованиеПолное` | `short_legal_name` text | сокращ. юр. наименование |
| `Parent` | `parent_code` text REF self | |
| `IsFolder` | `is_group` bool | |
| `DeletionMark` | `is_deleted` bool | |
| `Партнер` | `partner_code` text REF partners(code) | **owner — каждый Контрагент ⊂ Партнёр** |
| `ОбособленноеПодразделение` | `is_separate_subdivision` bool | |
| `ЮридическоеФизическоеЛицо` | `legal_or_individual_person` legal_entity_kind_t ENUM | |
| `СтранаРегистрации` | `registration_country_id` uuid REF country(id) | |
| `ГоловнойКонтрагент` | `parent_counterparty_code` text REF self | для филиалов |
| `ИНН` | `taxpayer_identification_number` text | UNIQUE INDEX (per tenant) |
| `КПП` | `tax_registration_reason_code` text | |
| `КодПоОКПО` | `okpo_code` text | |
| `РегистрационныйНомер` | `registration_number` text | ОГРН/ОГРНИП |
| `НалоговыйНомер` | `tax_number` text | |
| `НаименованиеМеждународное` | `international_name` text | |
| `НаименованиеВТранскрипции` | `transliterated_name` text | |
| `ДополнительнаяИнформация` | `additional_information` text | |

**Tabular parts:**
- `counterparty_additional_attribute` — EAV
- `counterparty_contact_information`
- `counterparty_kpp_history` — `(period date, tax_registration_reason_code text)`
- `counterparty_name_history` — `(period date, short_name text)`

---

### Контактные лица / Contact persons

| 1С | Postgres | Notes |
|---|---|---|
| `Ref` | `one_c_ref` uuid UNIQUE | |
| `Code` | `code` text PK | |
| `Description` | `name` text NOT NULL | ФИО |
| `Parent` | `parent_code` text REF self | для папок-групп |
| `IsFolder` | `is_group` bool | |
| `DeletionMark` | `is_deleted` bool | |
| `Owner` | `partner_code` text REF partners(code) | **owner — каждое контакт-лицо ⊂ Партнёр** |
| `ДатаРегистрацииСвязи` | `relationship_registration_date` timestamptz | |
| `ДатаПрекращенияСвязи` | `relationship_termination_date` timestamptz | NULL = активен |
| `Автор` | `author_id` uuid | |
| `Комментарий` | `comment` text | |
| `ДополнительнаяИнформация` | `additional_information` text | |
| `ДолжностьПоВизитке` | `job_title_on_business_card` text | |
| `Пол` | `gender` gender_t ENUM | |
| `ДатаРождения` | `birth_date` timestamptz | |

**Tabular parts:**
- `contact_person_additional_attribute` — EAV
- `contact_person_role` — many-to-many с `contact_role(id)`
- `contact_person_contact_information`

---

### Контактная информация (общая шина)

Используется во всех трёх сущностях (Партнёр/Контрагент/КонтактноеЛицо). У нас 3 параллельных таблицы или 1 polymorphic? Выбираем **polymorphic** — одна таблица с дискриминатором.

```sql
contact_information(
    id uuid PK,
    owner_entity_type contact_owner_t ENUM ('partner','counterparty','contact_person'),
    owner_code text NOT NULL,        -- code из соответствующей таблицы
    contact_type contact_type_t ENUM ('email','phone','address','site','fax','skype','other'),
    contact_kind_id uuid REF contact_kind(id),  -- Вид (детализация типа: рабочий/мобильный/и пр.)
    presentation text,
    field_values text,
    country text,
    region text,
    city text,
    email_address text,
    server_domain_name text,
    phone_number text,
    phone_number_without_codes text,
    list_view_kind_id uuid REF contact_kind(id),
    effective_from timestamptz,  -- только для Контрагентов
    value text,
    INDEX (owner_entity_type, owner_code)
)
```

---

## ENUM types

```sql
CREATE TYPE item_type_t AS ENUM ('product','service','container','set','work','other');
CREATE TYPE time_unit_t AS ENUM ('day','month','year','hour');
CREATE TYPE variant_usage_mode_t AS ENUM ('none','common','individual','common_for_kind');
CREATE TYPE legal_entity_kind_t AS ENUM ('company','private_person','individual_entrepreneur','foreign_company');
CREATE TYPE gender_t AS ENUM ('male','female','not_specified');
CREATE TYPE contact_owner_t AS ENUM ('partner','counterparty','contact_person');
CREATE TYPE contact_type_t AS ENUM ('email','phone','address','site','fax','skype','telegram','other');
CREATE TYPE currency_t AS ENUM ('RUB','USD','EUR','CNY','GBP','CHF','JPY','KRW');  -- (уже есть в catalog-architecture)
CREATE TYPE stock_event_type_t AS ENUM ('incoming','sale','reserve','unreserve','adjustment','transfer','writeoff');
```

## Reference catalogs (мини-таблицы из 1С)

Каждый — Postgres table с `(id uuid PK, code text, name text, one_c_ref uuid)`:

- `item_kind` (ВидыНоменклатуры)
- `unit_of_measure` (УпаковкиЕдиницыИзмерения)
- `brand` (Марки) — главное поле для бренда продукта
- `manufacturer` (Производители)
- `vat_rate` (СтавкиНДС) — `(name, rate numeric, is_active)`
- `product_category_1c` (ТоварныеКатегории)
- `country` (СтраныМира) — `(alpha2, alpha3, name_ru, name_en)`
- `hs_code` (КлассификаторТНВЭД) — `(code text PK, name text)`
- `okpd2_code` (КлассификаторОКПД2)
- `okp_code` (ОбщероссийскийКлассификаторПродукции)
- `okved2_code` (КлассификаторОКВЭД2)
- `quality_grade` (ГрадацииКачества)
- `price_group` (ЦеновыеГруппы)
- `season_group` (СезонныеГруппы)
- `warehouse_group` (СкладскиеГруппыНоменклатуры)
- `business_region` (БизнесРегионы)
- `access_group` (ГруппыДоступаПартнеров + Номенклатуры — разделим)
- `delivery_zone` (ЗоныДоставки)
- `label_template` (ШаблоныЭтикетокИЦенников)
- `purpose` (Назначения)
- `contact_kind` (ВидыКонтактнойИнформации)
- `contact_role` (РолиКонтактныхЛицПартнеров)
- `property_definition` (ChartOfCharacteristicTypes.ДополнительныеРеквизитыИСведения) — словарь EAV-свойств

## Pricing — отдельная схема (migration 008)

```sql
exchange_rate(
    currency currency_t NOT NULL,
    rate_to_rub numeric(20,6) NOT NULL,
    as_of date NOT NULL,
    source text NOT NULL DEFAULT '1c',  -- 'cbr' / '1c' / 'manual'
    PRIMARY KEY (currency, as_of)
);

nomenclature_price(
    nomenclature_code text PK REF nomenclature(code) ON DELETE CASCADE,

    -- ЗАКУПОЧНАЯ (sensitive — REVOKE с gluvex_app, доступ через gluvex_purchasing_view роль)
    purchase_amount numeric(20,4),
    purchase_currency currency_t,        -- 'USD' / 'CNY' / 'EUR'
    purchase_valid_from date,
    purchase_supplier_code text REF partners(code),

    -- РРЦ (recommended retail price) — публичная, в рублях
    rrp_rub numeric(20,2),
    rrp_valid_from date,

    -- Дефолтная дилерская скидка
    default_dealer_discount_pct numeric(5,2) DEFAULT 20.00,

    updated_at timestamptz DEFAULT now()
);

-- Формула цены для конкретного партнёра (или базовая если customer_partner_code NULL)
pricing_formula(
    id uuid PK,
    name text,
    customer_partner_code text REF partners(code),   -- NULL = базовая формула
    is_active bool DEFAULT true,
    valid_from date,
    valid_until date,
    notes text
);

-- Per-brand коэффициент в рамках формулы (1.5x для Agilent, 2.2x для Shimadzu и т.п.)
pricing_formula_brand_multiplier(
    formula_id uuid REF pricing_formula(id) ON DELETE CASCADE,
    brand_id uuid REF brand(id),
    multiplier numeric(6,3) NOT NULL,
    PRIMARY KEY (formula_id, brand_id)
);

-- Column-level security
REVOKE ALL ON nomenclature_price FROM gluvex_app;
GRANT SELECT (nomenclature_code, rrp_rub, default_dealer_discount_pct, updated_at) ON nomenclature_price TO gluvex_app;

CREATE ROLE gluvex_purchasing_view;
GRANT SELECT ON nomenclature_price TO gluvex_purchasing_view;
GRANT SELECT ON exchange_rate, pricing_formula, pricing_formula_brand_multiplier TO gluvex_purchasing_view;
```

## Stock — отдельная схема (migration 009)

```sql
stock_current(
    nomenclature_code text PK REF nomenclature(code) ON DELETE CASCADE,
    quantity_on_hand numeric(15,3) NOT NULL DEFAULT 0,
    quantity_reserved numeric(15,3) NOT NULL DEFAULT 0,
    quantity_available numeric(15,3) GENERATED ALWAYS AS
        (quantity_on_hand - quantity_reserved) STORED,
    last_event_id bigint,
    updated_at timestamptz DEFAULT now()
);

stock_event(
    id bigserial PK,
    nomenclature_code text NOT NULL REF nomenclature(code),
    event_type stock_event_type_t NOT NULL,
    delta_qty numeric(15,3) NOT NULL,
    delta_reserved numeric(15,3) NOT NULL DEFAULT 0,
    counterparty_code text REF counterparties(code),
    document_ref text,            -- 1С document reference (Поступление/Реализация/Резерв и т.п.)
    occurred_at timestamptz NOT NULL,
    recorded_at timestamptz DEFAULT now(),
    source text DEFAULT '1c',
    notes text
);

-- Trigger: на каждый INSERT в stock_event обновляем stock_current
CREATE OR REPLACE FUNCTION trg_stock_apply_event() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO stock_current (nomenclature_code, quantity_on_hand, quantity_reserved, last_event_id, updated_at)
    VALUES (NEW.nomenclature_code, NEW.delta_qty, NEW.delta_reserved, NEW.id, now())
    ON CONFLICT (nomenclature_code) DO UPDATE SET
        quantity_on_hand = stock_current.quantity_on_hand + NEW.delta_qty,
        quantity_reserved = stock_current.quantity_reserved + NEW.delta_reserved,
        last_event_id = NEW.id,
        updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Twenty CRM mirror

**Companies** (custom fields):
- `oneCPartnerRef` UUID — связь с `partners.one_c_ref`
- `oneCCounterpartyRef` UUID — связь с `counterparties.one_c_ref`
- `inn`, `kpp`, `ogrn` (уже есть)
- `okpoCode`, `taxNumber`, `registrationNumber`, `internationalName`, `transliteratedName`
- `isCustomer`, `isSupplier`, `isCompetitor`, `isCarrier` (booleans)
- `kppHistory`, `nameHistory` (JSONB)
- `primaryManagerId` (для назначения менеджера)

**People** (custom fields):
- `oneCContactRef` UUID
- `oneCPartnerRef` UUID
- `jobTitleOnBusinessCard`
- `birthDate`, `gender`
- `relationshipRegistrationDate`, `relationshipTerminationDate`
- `additionalInformation`

## CSV import contract

ZIP-архив с CSV-файлами + `manifest.json`. Header у каждого CSV = **English column names** из этой таблицы:

```
nomenclature.csv               — основной справочник
nomenclature_attribute.csv     — EAV ДопРеквизитов
nomenclature_presentation.csv  — переводы
partners.csv
partner_contact_information.csv
counterparties.csv
counterparty_kpp_history.csv
counterparty_name_history.csv
contact_persons.csv
contact_person_role.csv
contact_information.csv        — общая (с дискриминатором owner_entity_type)
price_list.csv                 → exchange_rate.csv + nomenclature_price.csv
stock_snapshot.csv             → stock_event инициализация
property_definitions.csv       ← словарь EAV свойств с типами
brand.csv, manufacturer.csv, unit_of_measure.csv, ... (reference)
```

Endpoint: `POST /1c-bridge/import/csv` (multipart, ZIP body, header `X-Sync-Mode: full|delta`).

## Open vs Decided

| Тема | Статус |
|---|---|
| Code = text (alphanumeric) | ✅ decided |
| РУ = 2 поля (has_ru + number + date) | ✅ decided |
| 1 склад, real-time push | ✅ decided |
| Multi-currency purchase (USD/CNY) | ✅ decided |
| Column-level GRANT на purchase | ✅ decided |
| Per-customer formulas + per-brand multipliers | ✅ decided |
| Dealer discount default 20% | ✅ decided |
| Source of truth = 1С | ✅ decided |
| CSV first, API later | ✅ decided |
| Twenty Custom Object vs Custom Fields | 🟡 решено: **Custom Fields на Companies/People**, не отдельный Object |
| Хранение 1С Code для папок (is_group) | 🟡 оставляем те же таблицы — `is_group=true` |
| Sync направление CRM → 1С | 🟡 только на стадии "запрос КП", определим Twenty Stage позже |
| Mock 1C для CI | 🔴 потом |
| Webhook contract от 1С (event-based delta) | 🔴 потом |
