# Gluvex — архитектура каталога продукции

**Версия:** 1.0
**Дата:** 2026-05-11
**Иерархия документов:**
1. [`master-data-architecture.md`](master-data-architecture.md) — 1С как master, контуры системы
2. [`storage-architecture.md`](storage-architecture.md) — слой хранения и retrieval
3. **(этот)** `catalog-architecture.md` — модель данных продуктового каталога
4. [`system-state.md`](system-state.md) — operational reference

> Этот документ описывает **схему данных для продуктового каталога**: приборы, конфигурации, совместимость, РУ, цены.
> Используется: crawler-сервис (пишет), tender-pipeline matcher (читает), kp_agent (читает), 1c-bridge (синхронизирует с 1С).

---

## 1. Принципы

1. **Открытая архитектура.** Прибор = composable из компонентов. HPLC = pump + autosampler + column oven + detectors (до 3). Секвенатор = base platform + flow cells + reagent kits.
2. **РУ — обязательное поле на каждом продукте.** Влияет на НДС (прибор с РУ — 0%, реагент с РУ — 10%, без РУ — 20%).
3. **Конфигурации как граф зависимостей.** Каждая комбинация (прибор + конфигурация + read mode) даёт свою производительность.
4. **Несколько источников = единая модель.** Парсер из gluvexlab.com, genohub.com, en.genemind.com, sesana.ru — пишут в одну схему через `source_url` и `content_hash`.
5. **Цены — поверх каталога, не часть его.** Каталог хранит характеристики; цены живут в отдельной таблице с историей, формулами и валютами. Заливается из 1С позднее.

---

## 2. Производители — что парсим (финальный список)

### 2.1. Аналитика — HPLC / HPLC-MS / GC / GC-MS
- **Agilent** (1290 Infinity II UHPLC, 6495 LC-MS Triple Quadrupole, 7890B GC, 7000 GC-MS, etc.)
- **Waters** (ACQUITY UPLC, Xevo TQ-S, Synapt G2-Si, etc.)
- **Shimadzu** (Nexera UHPLC, LCMS-8060, GC-2030, GCMS-TQ8050, etc.)
- **AB Sciex** (Triple Quad 7500, ZenoTOF, etc.)
- **Bruker** (timsTOF Pro 2, MaXis impact, SCION GC, etc.)
- **Thermo Fisher** (Vanquish UHPLC, Orbitrap Exploris, TSQ Altis, ISQ 7000, etc.)
- **SCION Instruments** (бывш. Bruker GC) — серии 456-GC, 8500 GC, SC600
- **Restek** — колонки и расходники

### 2.2. Аналитика — AAS / UV-Vis / FTIR / UV-NIR
- **Agilent** (Cary 60/3500 UV-Vis, Cary 7000 UMS, Cary 630 FTIR, AA 240/280FS AAS)
- **Shimadzu** (UV-1900i, IRSpirit FTIR, AA-7800 AAS)
- **Thermo Fisher** (Evolution UV-Vis, Nicolet iS50 FTIR, iCE 3000 AAS)
- **PerkinElmer** (Lambda series UV-Vis, Frontier IR, PinAAcle AAS)
- **Bruker** (TENSOR FTIR)
- **Analytik Jena** (Specord UV-Vis, novAA AAS)

### 2.3. Аналитика — ICP-OES / ICP-MS
- **Agilent** (5800 ICP-OES, 5900 ICP-OES, 7900 ICP-MS, 8900 ICP-MS/MS)
- **Thermo Fisher** (iCAP PRO ICP-OES, iCAP TQ ICP-MS, iCAP RQ ICP-MS)
- **PerkinElmer** (Avio ICP-OES, NexION ICP-MS)
- **Analytik Jena** (PlasmaQuant ICP-MS/OES)
- **Spectro Ametek**

### 2.4. Cell tech / Life science / Genomics

#### Agilent (большая линейка NGS):
- TapeStation 4150/4200/4150 — QC библиотек
- Bravo, Magnis NGS Prep — automation для library prep
- **SureSelect** (XT HS2, Custom, ClearSeq, Cancer All-In-One, etc.)
- **AVENIO** ctDNA panels
- **Resolution Bioscience** liquid biopsy

#### Thermo Fisher NGS:
- **Ion Torrent** платформы: Ion GeneStudio S5 (S5, S5 Plus, S5 XL, S5 Prime), Ion Proton, Ion Genexus
- **Ion AmpliSeq** library prep
- **Oncomine** panels (Comprehensive, Focus, Childhood Cancer, BRCA, etc.)

### 2.5. Секвенаторы NGS — производители и их OEM-партнёры

| Производитель | Модели | Российский OEM |
|---|---|---|
| **Illumina** | iSeq 100, MiniSeq, MiSeq, NextSeq 550/1000/2000, NovaSeq 6000, NovaSeq X / X Plus | — |
| **MGI Tech** | DNBSEQ-E5, DNBSEQ-G50, DNBSEQ-G99, DNBSEQ-G400, DNBSEQ-T7, DNBSEQ-T10, DNBSEQ-T20 | **Хеликон** (helicon.ru) — 2 модели OEM |
| **Genemind** | FASTASeq 300 (V3.0), SURFSeq 5000, SURFSeq Q, GenoLab M, GenoCare 1600 | **Сесана** (sesana.ru) — линейка **Геноскан** 3700/4000/5000/6000 |
| **Oxford Nanopore** | MinION, GridION, PromethION 2/24/48 | — |
| **PacBio** | Sequel IIe, Revio, Vega, Onso | — |
| **Element Biosciences** | AVITI, AVITI24 | — |
| **Ultima Genomics** | UG100 | — |
| **Singular Genomics** | G4 | — |

### 2.6. NGS реагенты, панели и library prep

- **IDT** (Integrated DNA Technologies) — xGen NGS panels, Lockdown probes, custom oligos, ssODN, primer pools
- **Twist Biosciences** — Twist Exome 2.5/Comprehensive Exome Spike-in, Custom Panels, Library Prep (Library Prep EF / Mag), Methylation Detection
- **Roche KAPA** — HyperPrep, EvoPrep, HyperCap, HyperPure beads, Library Quantification, RNA HyperPrep
- **AmoyDx** — HANDLE Classic (40 genes), HANDLE Plus (143 genes), HANDLE HRR, HANDLE Melanoma, ADx-SuperARMS, AmoyDx HRD Focus Panel
- **Burning Rock** — OncoScreen Plus, OncoCompanion CDx, OncoMAP, **OverC™ Multi-Cancer Detection** ⭐, OverC™ Multi-Cancer Screening
- **Ariosa Diagnostics** (теперь Roche) — Harmony NIPT
- **Pillar Biosciences** — oncoReveal CDx, oncoReveal Solid Tumor, oncoReveal Rapid AML, ATM Inhibitor RUO

---

## 3. Модель данных каталога

### 3.1. Базовая сущность — `product`

Любой каталожный объект: прибор, расходник, реагент, компонент, набор.

```sql
CREATE TYPE product_category_t AS ENUM (
  -- Аналитика
  'hplc_system', 'hplc_pump', 'hplc_autosampler', 'hplc_column_oven', 'hplc_detector',
  'gc_system', 'gc_module', 'mass_spectrometer',
  'aas_system', 'icp_oes', 'icp_ms',
  'uv_vis_spectrometer', 'ftir_spectrometer', 'nir_spectrometer',
  -- Хроматография расходники
  'hplc_column', 'gc_column', 'vial', 'syringe_filter', 'spe_cartridge',
  -- NGS платформы
  'sequencer_platform',
  -- NGS компоненты
  'sequencer_flowcell', 'sequencer_reagent_kit',
  -- NGS реагенты/панели
  'ngs_library_prep_kit', 'ngs_target_capture_panel', 'ngs_amplicon_panel',
  'pcr_kit', 'realtime_pcr_kit', 'dna_extraction_kit', 'rna_extraction_kit',
  -- Общая лаборатория
  'centrifuge', 'shaker_vortex', 'incubator', 'drying_oven', 'climate_chamber',
  'biological_safety_cabinet', 'laminar_hood', 'balance', 'titrator',
  -- Прочее
  'consumable', 'spare_part', 'accessory', 'software', 'service', 'other'
);

CREATE TYPE product_domain_t AS ENUM (
  'analytical', 'genetics_ngs', 'molecular_diagnostics',
  'life_science_general', 'general_lab', 'pharmaceutical', 'other'
);

CREATE TYPE ru_status_t AS ENUM (
  'none',          -- РУ нет (и не нужен)
  'pending',       -- в процессе регистрации
  'active',        -- действует
  'expired',       -- просрочен
  'revoked',       -- отозван
  'not_applicable' -- не требуется по виду продукции
);

CREATE TABLE product (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  -- Идентификация
  product_code          TEXT,                          -- наш внутренний код (для 1С связки)
  vendor_code           TEXT,                          -- артикул производителя
  brand                 TEXT NOT NULL,                 -- 'Illumina' / 'Agilent' / 'Сесана'
  model                 TEXT NOT NULL,                 -- 'NovaSeq 6000' / '1290 Infinity II' / 'Геноскан 4000'
  oem_of_id             UUID REFERENCES product(id),   -- если это OEM-rebrand другой модели

  category              product_category_t NOT NULL,
  subcategory           TEXT,                          -- свободный текст для уточнения
  domain                product_domain_t NOT NULL,

  display_name          TEXT NOT NULL,                 -- "Секвенатор Illumina NovaSeq 6000"
  description           TEXT,
  synonyms              TEXT[],                        -- для семантического матчинга в ТЗ

  -- Базовые характеристики (не зависящие от конфигурации)
  base_specs            JSONB NOT NULL DEFAULT '{}',

  -- Регистрационное удостоверение (РУ)
  ru_status             ru_status_t NOT NULL DEFAULT 'none',
  ru_number             TEXT,
  ru_valid_from         DATE,
  ru_valid_until        DATE,                          -- NULL = бессрочно
  ru_url                TEXT,                          -- ссылка на запись в реестре Росздравнадзора
  ru_class              TEXT,                          -- класс мед изделия 1/2а/2б/3

  -- Жизненный цикл и доступность
  status                TEXT NOT NULL DEFAULT 'active', -- active | discontinued | prerelease | recalled
  release_date          DATE,
  discontinue_date      DATE,
  manufacturer_country  TEXT,                          -- 'US', 'CN', 'RU', 'DE', ...

  -- Источники данных
  source_urls           TEXT[],
  datasheet_paths       TEXT[],                        -- MinIO object_keys
  brochure_urls         TEXT[],

  -- Метаданные
  metadata              JSONB DEFAULT '{}',
  content_hash          BYTEA,                         -- sha256 для дедупа при обновлении из crawler
  imported_at           TIMESTAMPTZ,
  imported_from         TEXT,                          -- 'gluvexlab' | 'genemind_official' | '1c' | ...

  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (tenant_id, brand, model)
);
```

### 3.2. Конфигурация продукта — `product_configuration`

Каждая возможная комплектация / вариант / опция базового продукта.

```sql
CREATE TYPE config_type_t AS ENUM (
  -- Секвенаторы
  'flowcell',           -- 'S4 flow cell', 'PE150 FCM'
  'sequencer_kit',      -- 'NovaSeq 6000 v1.5 Reagent Kit S4 300 cycles'
  'run_mode',           -- '2x150 PE @ S4 flow cell'
  -- HPLC / GC
  'pump_module',
  'autosampler_module',
  'column_oven_module',
  'detector_module',    -- UV/DAD/FLD/RID/MS
  'column',             -- 'C18 4.6x250mm'
  -- AAS / ICP-MS / прочее
  'atomizer',           -- 'graphite furnace', 'flame'
  'lamp',               -- 'HCL', 'EDL'
  'sample_introduction',-- 'cone', 'nebulizer', 'spray chamber'
  -- NGS панели
  'panel_variant',      -- разные ассортименты генов в одной серии
  'compatible_platform',-- "эта панель работает на платформах X"
  -- Прочее
  'option',
  'firmware_version',
  'other'
);

CREATE TABLE product_configuration (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  -- Принадлежность
  product_id            UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
                                                       -- "родительский" продукт (NovaSeq 6000)
                                                       -- или сам продукт-компонент (S4 flow cell)
  config_type           config_type_t NOT NULL,
  configuration_code    TEXT,                          -- артикул конфигурации/комплектации
  name                  TEXT NOT NULL,                 -- 'NovaSeq 6000 v1.5 S4 Reagent Kit 300 cycles'

  -- Спецификации именно этой конфигурации
  specs                 JSONB NOT NULL DEFAULT '{}',

  -- РУ конфигурации (часто отличается от прибора — реагент с РУ ставится в прибор без РУ)
  ru_status             ru_status_t NOT NULL DEFAULT 'none',
  ru_number             TEXT,
  ru_valid_from         DATE,
  ru_valid_until        DATE,
  ru_url                TEXT,

  -- Что заменяет (для апгрейдов)
  replaces_id           UUID REFERENCES product_configuration(id),
  is_default            BOOLEAN NOT NULL DEFAULT false,
  status                TEXT NOT NULL DEFAULT 'active',

  source_urls           TEXT[],
  metadata              JSONB DEFAULT '{}',
  content_hash          BYTEA,
  imported_at           TIMESTAMPTZ,
  imported_from         TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_config_product_type ON product_configuration(product_id, config_type);
```

### 3.3. Совместимость — `product_compatibility`

Граф зависимостей между компонентами. Какая ячейка работает с каким секвенатором; какой детектор стыкуется с какой системой HPLC; какая панель с какой платформой.

```sql
CREATE TYPE compatibility_type_t AS ENUM (
  'installable_in',       -- компонент → система (S4 flowcell installable_in NovaSeq 6000)
  'requires',             -- A требует наличия B (HPLC требует pump + autosampler)
  'replaces',             -- A заменяет B (S4 v1.5 replaces S4 v1.0)
  'compatible_with',      -- широкая совместимость (xGen panel compatible_with NovaSeq)
  'incompatible_with',    -- явная несовместимость (важно для матчера)
  'recommended_with',     -- рекомендуется в паре
  'paired_with'           -- идёт комплектом
);

CREATE TABLE product_compatibility (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  -- A → B
  a_product_id          UUID REFERENCES product(id),
  a_config_id           UUID REFERENCES product_configuration(id),
  b_product_id          UUID REFERENCES product(id),
  b_config_id           UUID REFERENCES product_configuration(id),

  compatibility_type    compatibility_type_t NOT NULL,
  notes                 TEXT,
  source_url            TEXT,
  confidence            NUMERIC(3,2) DEFAULT 1.0,      -- 0..1 насколько уверенно

  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

  CHECK (
    (a_product_id IS NOT NULL OR a_config_id IS NOT NULL) AND
    (b_product_id IS NOT NULL OR b_config_id IS NOT NULL)
  )
);

CREATE INDEX idx_compat_a ON product_compatibility(a_product_id, a_config_id);
CREATE INDEX idx_compat_b ON product_compatibility(b_product_id, b_config_id);
CREATE INDEX idx_compat_type ON product_compatibility(compatibility_type);
```

### 3.4. Слоты конфигурации — `product_slot`

Описывает «места куда вставляются компоненты». Для HPLC: 1× pump (обязательно), 1× autosampler (обязательно), 1× column oven (опционально), 1-3× detector. Для NovaSeq 6000: 1-2× flow cell.

```sql
CREATE TABLE product_slot (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id            UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
                                                       -- родительский прибор
  slot_name             TEXT NOT NULL,                 -- 'pump' | 'autosampler' | 'detector_1' | 'flowcell_a' | 'flowcell_b'
  slot_role             TEXT NOT NULL,                 -- semantic role: 'pump' | 'autosampler' | 'detector' | 'flowcell'
  min_count             INTEGER NOT NULL DEFAULT 0,    -- сколько минимум
  max_count             INTEGER NOT NULL DEFAULT 1,    -- сколько максимум
  required              BOOLEAN NOT NULL DEFAULT false,
  allowed_categories    product_category_t[],          -- какие категории сюда можно вставить
  notes                 TEXT,

  UNIQUE (product_id, slot_name)
);
```

Пример для Agilent 1290 Infinity II:
```sql
INSERT INTO product_slot (product_id, slot_name, slot_role, min_count, max_count, required, allowed_categories) VALUES
  (<1290_id>, 'pump',         'pump',         1, 1, true,  ARRAY['hplc_pump']::product_category_t[]),
  (<1290_id>, 'autosampler',  'autosampler',  1, 1, true,  ARRAY['hplc_autosampler']::product_category_t[]),
  (<1290_id>, 'column_oven',  'column_oven',  0, 1, false, ARRAY['hplc_column_oven']::product_category_t[]),
  (<1290_id>, 'detector',     'detector',     0, 3, false, ARRAY['hplc_detector']::product_category_t[]);
```

Для NovaSeq 6000:
```sql
INSERT INTO product_slot (product_id, slot_name, slot_role, min_count, max_count, required, allowed_categories) VALUES
  (<novaseq_id>, 'flowcell_a', 'flowcell', 0, 1, false, ARRAY['sequencer_flowcell']::product_category_t[]),
  (<novaseq_id>, 'flowcell_b', 'flowcell', 0, 1, false, ARRAY['sequencer_flowcell']::product_category_t[]);
```

Это даёт **конструктор** для агента — взять платформу, поняв список её слотов, найти совместимые конфигурации (через `product_compatibility WHERE type='installable_in'`), собрать полную конфигурацию.

### 3.5. Метрики run для секвенаторов — `sequencer_runtime_metric`

Декартово произведение `платформа × ячейка × run mode` → реальная производительность.

```sql
CREATE TABLE sequencer_runtime_metric (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  sequencer_id          UUID NOT NULL REFERENCES product(id) ON DELETE CASCADE,
  flowcell_config_id    UUID REFERENCES product_configuration(id),
  reagent_kit_id        UUID REFERENCES product_configuration(id),

  read_mode             TEXT NOT NULL,                 -- '2x150', '1x300', 'PE150', 'SE100'
  read_length_max       INTEGER,                       -- 150
  is_paired_end         BOOLEAN,
  cycles                INTEGER,                       -- 300 = 2x150 with cycles

  total_reads_million_max NUMERIC,
  total_reads_million_typ NUMERIC,
  total_output_gb_max   NUMERIC,
  total_output_gb_typ   NUMERIC,
  run_time_hours_min    NUMERIC,
  run_time_hours_max    NUMERIC,

  q30_pct               NUMERIC(5,2),                  -- 90.0
  q40_pct               NUMERIC(5,2),                  -- для современных платформ типа SurfSeq Q

  cost_per_gb_usd       NUMERIC(10,4),
  cost_per_reaction_usd NUMERIC(10,2),

  applications          TEXT[],                        -- ['WGS', 'WES', 'RNA-seq', 'targeted', 'NIPT']
  notes                 TEXT,

  source_url            TEXT,
  source_confidence     NUMERIC(3,2) DEFAULT 1.0,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_runtime_seq           ON sequencer_runtime_metric(sequencer_id);
CREATE INDEX idx_runtime_flowcell      ON sequencer_runtime_metric(flowcell_config_id);
CREATE INDEX idx_runtime_output_gb     ON sequencer_runtime_metric(total_output_gb_typ);
CREATE INDEX idx_runtime_reads_m       ON sequencer_runtime_metric(total_reads_million_typ);
CREATE INDEX idx_runtime_applications  ON sequencer_runtime_metric USING GIN (applications);
```

Пример — для NovaSeq 6000 будет ~8-12 строк:
```
(NovaSeq, S4 flowcell, S4 Reagent Kit 300, '2x150', 300, 10000M, 3000Gb, 36-44h, 90.0%, 5.53$/Gb, ['WGS','WES','RNA-seq'])
(NovaSeq, S2 flowcell, S2 Reagent Kit 300, '2x150', 300, 4100M,  833Gb,  29-36h, 90.0%, 7.12$/Gb, ['WGS','WES'])
(NovaSeq, S1 flowcell, S1 Reagent Kit 300, '2x150', 300, 1600M,  333Gb,  25-29h, 90.0%, 9.30$/Gb, ['WES','RNA-seq','targeted'])
(NovaSeq, SP flowcell, SP Reagent Kit 500, '2x250', 500, 800M,   400Gb,  22-25h, 80.0%, 11.50$/Gb, ['amplicon','small genomes'])
...
```

### 3.6. Цены — `product_pricing` (наполняется из 1С позднее)

```sql
CREATE TYPE pricing_type_t AS ENUM ('purchase', 'sale', 'list', 'distributor', 'msrp');
CREATE TYPE currency_t AS ENUM ('USD', 'EUR', 'CNY', 'RUB', 'GBP', 'CHF', 'JPY');

CREATE TABLE product_pricing (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL,

  product_id            UUID REFERENCES product(id),
  configuration_id      UUID REFERENCES product_configuration(id),

  pricing_type          pricing_type_t NOT NULL,
  amount                NUMERIC,                       -- если фиксированная цена
  currency              currency_t NOT NULL,

  -- Формулы и коэффициенты (когда цена не фиксированная)
  formula_expr          TEXT,                          -- например: 'purchase_usd * 1.35 * fx_usd_rub'
  derived_from_id       UUID REFERENCES product_pricing(id),  -- цена выведена из другой цены
  multiplier            NUMERIC,                       -- если простой коэффициент

  -- НДС
  vat_rate              NUMERIC(4,2),                  -- 0.00 / 0.10 / 0.20
  vat_rule              TEXT,                          -- 'ru_active_device' (0%), 'ru_active_reagent_med' (10%), 'standard' (20%)

  -- Период действия
  effective_from        DATE NOT NULL,
  effective_until       DATE,
  -- Источник (на момент 1С-импорта)
  source                TEXT,                          -- '1c_import' | 'manual' | 'distributor_price_list'

  notes                 TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),

  CHECK (product_id IS NOT NULL OR configuration_id IS NOT NULL)
);

CREATE INDEX idx_pricing_product       ON product_pricing(product_id) WHERE product_id IS NOT NULL;
CREATE INDEX idx_pricing_config        ON product_pricing(configuration_id) WHERE configuration_id IS NOT NULL;
CREATE INDEX idx_pricing_effective     ON product_pricing(effective_from, effective_until);
CREATE INDEX idx_pricing_type          ON product_pricing(pricing_type, currency);
```

Курсы валют — отдельная таблица `fx_rate(currency_from, currency_to, rate, date)`. Будем подтягивать из ЦБ РФ или фиксировать вручную.

---

## 4. Правила НДС (для расчёта продажи)

```python
def compute_vat_rate(product: Product) -> Decimal:
    if product.category == 'sequencer_platform' and product.ru_status == 'active':
        return Decimal('0.00')   # медицинское изделие → 0% НДС
    if product.category in REAGENT_CATEGORIES and product.ru_status == 'active':
        return Decimal('0.10')   # медицинский реагент с РУ → 10% НДС
    return Decimal('0.20')        # всё остальное → 20% НДС
```

REAGENT_CATEGORIES = `{ngs_library_prep_kit, ngs_target_capture_panel, ngs_amplicon_panel, pcr_kit, realtime_pcr_kit, dna_extraction_kit, rna_extraction_kit}`.

---

## 5. Источники данных и порядок парсинга

| # | Источник | URL | Что берём | Время |
|---|---|---|---|---|
| 1 | **gluvexlab.com** | https://gluvexlab.com/catalog/ + /brands/<slug>/ | 43 бренда, ~50k+ позиций (Gluvex 3013, Agilent 50231 артикулов) — ground truth | 1 день |
| 2 | **Genohub** | https://genohub.com/high-throughput-sequencers/ | все секвенаторы со структурированными specs | 0.5 дня |
| 3 | **en.genemind.com** | /products | Genemind: FASTASeq 300, SURFSeq 5000, SURFSeq Q + flow cells + run modes | 0.5 дня |
| 4 | **sesana.ru** | /ngs_sequencers + страницы Геноскан | российский OEM Genemind, **с РУ** | 0.5 дня |
| 5 | **helicon.ru** | публичный каталог | OEM MGI Tech (2 модели) | 0.5 дня |
| 6 | **illumina.com** | /systems/sequencing-platforms/<model>/specifications.html | официальные specs (~10-12 моделей) | 1 день |
| 7 | **en.mgi-tech.com** | /products/ | DNBSEQ platforms + flow cells + kits | 1 день |
| 8 | **amoydiagnostics.com** | /products | HANDLE panels + ADx-SuperARMS + HRD | 0.5 дня |
| 9 | **pillarbiosci.com** | /products/ | oncoReveal portfolio | 0.5 дня |
| 10 | **burningrock.com** | /products | OncoScreen, OncoMAP, **OverC** | 0.5 дня |
| 11 | **agilent.com** | /products/genomics/ + /products/liquid-chromatography/ | NGS (SureSelect/Magnis/AVENIO) + HPLC | 2 дня |
| 12 | **thermofisher.com** | /products/ion-torrent + другие | Ion Torrent + Oncomine + analytical | 2 дня |
| 13 | **shimadzu.com**, **waters.com**, **brukerstores.bruker.com**, **sciex.com** | официальные каталоги | analytical instruments | 2-3 дня |
| 14 | **idtdna.com**, **twistbioscience.com**, **sequencing.roche.com (KAPA)** | каталоги NGS реагентов | + методические данные | 1-2 дня |
| 15 | Российские реселлеры (Lacopa, Millab, IMC, Element-msc) | их каталоги | cross-check РУ и цен | 1 день |

**Итого: ~14-16 дней на полный первичный прогон.** Делается параллельно crawler-сервисом, не блокирует другую работу.

---

## 6. Crawler — архитектура

```
tenderland_bot/services/catalog-crawler/
├── pyproject.toml
├── Dockerfile
├── configs/                          # YAML конфиг на каждый источник
│   ├── gluvexlab.yaml
│   ├── genohub.yaml
│   ├── genemind-official.yaml
│   ├── sesana.yaml
│   ├── helicon.yaml
│   ├── illumina-official.yaml
│   ├── mgi-official.yaml
│   ├── amoydx.yaml
│   ├── pillar-biosciences.yaml
│   ├── burning-rock.yaml
│   ├── agilent-genomics.yaml
│   ├── agilent-hplc.yaml
│   └── ...
├── src/catalog_crawler/
│   ├── core/
│   │   ├── fetcher.py                # aiohttp + retry + rate limit + robots.txt
│   │   ├── parser.py                 # selectolax CSS / XPath
│   │   ├── normalizer.py             # унификация specs → JSONB
│   │   ├── deduper.py                # content_hash + idempotency
│   │   └── ru_lookup.py              # запрос к реестру Росздравнадзора (отложено)
│   ├── schemas/                       # Pydantic (source of truth для типов)
│   │   ├── product.py
│   │   ├── configuration.py
│   │   ├── compatibility.py
│   │   ├── sequencer_metric.py
│   │   └── ru.py
│   ├── adapters/
│   │   ├── gluvexlab.py
│   │   ├── genohub.py
│   │   └── ...
│   ├── pipelines/
│   │   ├── to_postgres.py            # → product / product_configuration / ...
│   │   ├── to_minio.py               # PDF брошюры → bucket product-brochures
│   │   └── to_mempalace.py           # → wing gluvex-products
│   └── main.py                        # CLI: crawl <source-name>
```

**Запуск:**
- В Docker, отдельный контейнер `catalog-crawler` в нашем стеке
- Через ARQ scheduler — раз в неделю полный прогон, ежедневно дельта
- CLI для ручного: `docker compose run --rm catalog-crawler crawl gluvexlab`

**Идемпотентность:** при обновлении того же `(brand, model)` сравнивается `content_hash`; если одинаковый — пропуск; если разный — UPDATE с записью в `audit_events` (action=`product_updated`, payload_diff=…).

---

## 7. Открытые вопросы

| # | Вопрос | Кому |
|---|---|---|
| Q1 | Откуда брать РУ — парсить реестр Росздравнадзора (roszdravnadzor.gov.ru), импорт из 1С, ручная заливка? | заказчик |
| Q2 | Курсы валют — ЦБ РФ API через `apirate.io` или Yandex.Money? Какая частота обновления? | мы (нужно решение когда займёмся pricing) |
| Q3 | Картинки приборов — парсить в MinIO bucket `product-brochures` или ссылками на источник? | мы (default — в MinIO для надёжности) |
| Q4 | Какие из «других важных» производителей я мог упустить? (Sysmex для гематологии? Roche Cobas для биохимии?) | заказчик |
| Q5 | Дочерние слоты на NGS-панелях (mini-panel, custom design) — отдельным `product_configuration` или метаданным? | мы (default — отдельная configuration) |

---

_Документ обновляется при каждом расширении модели каталога. Все изменения схемы — через миграцию `00X_*.sql` в `migrations/` + правка этого документа._
