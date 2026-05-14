# Tenderland — индекс всех автопоисков (4 файла, 19 поисков)

**Дата:** 2026-05-14
**Назначение:** единая точка входа для менеджера, который настраивает автопоиски в Tenderland UI. Каждая ячейка таблицы — ссылка на конкретный файл и секцию.

---

## Сводка по доменам

| Домен                     | Файл                                                   | Поисков | Готовность | Назначение                              |
|---------------------------|--------------------------------------------------------|---------|------------|-----------------------------------------|
| `analytical`              | [`keywords_config.md`](keywords_config.md)             | 8 + 2 опц. | 🟢 v1.0    | Инструментальная аналитика (хроматография, спектрометрия, элементный анализ) |
| `molecular_diagnostics`   | [`keywords_config_molecular_diagnostics.md`](keywords_config_molecular_diagnostics.md) | 4 + 1 опц. + 1 нов. | 🟢 v1.1    | NGS-секвенаторы, реагенты, онкопанели, НИПТ/ПГТ/HLA, услуги CES/WES/WGS |
| `general_lab`             | [`keywords_config_general_lab.md`](keywords_config_general_lab.md) | 5 + 1 опц. | 🆕 v1.0    | Инкубаторы, термостаты, стерилизаторы, испарители, мешалки, реакторы |
| `capillary_centrifuges_robotics` | [`keywords_config_capillary_centrifuges_robotics.md`](keywords_config_capillary_centrifuges_robotics.md) | 3       | 🆕 v1.0    | Капиллярный электрофорез (НЕ Sanger), центрифуги, liquid handling robotics |
| **Итого**                 |                                                        | **19 основных + 4 опц.** |            |                                         |

---

## Полная карта 19 поисков

### 🔬 Инструментальная аналитика — `analytical` (8 + 2 опц.)
*файл: `keywords_config.md`*

| №  | Имя                       | Что ищем                                                            | Ключевые бренды                                            |
|----|---------------------------|---------------------------------------------------------------------|------------------------------------------------------------|
| 01 | `01_LC_LCMS_GPC_Prep`    | ВЭЖХ / УВЭЖХ / ЖХ-МС/МС / ГПХ / препаративная                       | Agilent, Shimadzu, Waters, Thermo, PerkinElmer, SCIEX     |
| 02 | `02_GC_GCMS`             | ГХ, ГХ-МС/МС, FID/ECD/NPD/TCD, пиролизеры                           | Agilent 7890/8890, Shimadzu GC-2030, Thermo TRACE, PE Clarus, Хроматэк, Хромос |
| 03 | `03_ICP_OES`             | ИСП-ОЭС / ИСП-АЭС                                                   | Agilent 5800/5900, PE Avio, Thermo iCAP, Spectro, Shimadzu ICPE |
| 04 | `04_AAS`                 | Атомно-абсорбционная (пламя + ЭТА)                                  | Agilent 240/280, PE PinAAcle, Shimadzu AA-7800, Thermo iCE |
| 05 | `05_ICP_MS`              | ИСП-МС, тандем, секторные HR-ICP-MS                                 | Agilent 7900/8800/8900, PE NexION, Thermo iCAP Q/TQ, Element XR |
| 06 | `06_IC`                  | Ионная хроматография (анионная/катионная)                           | Dionex ICS, Metrohm 882/930                                |
| 07 | `07_UV_Vis`              | УФ-видимая спектрофотометрия                                        | Agilent Cary, Shimadzu UV-1900/2700, Thermo Evolution, PE Lambda |
| 08 | `08_FTIR`                | ФТИР / ИК-Фурье                                                     | Agilent Cary 630, Shimadzu IRTracer, Thermo Nicolet, PE Frontier |
| —  | `09_Service` *(опц.)*    | Сервис на аналитические приборы                                     | Любые из 01-08                                              |
| —  | `10_Consumables` *(опц.)*| Колонки, картриджи, лампы, ГСО                                      | Любые из 01-08                                              |

### 🧬 Молекулярная диагностика — `molecular_diagnostics` (4 + 1 опц. + 1 нов.)
*файл: `keywords_config_molecular_diagnostics.md`*

| №   | Имя                            | Что ищем                                                         | Ключевые бренды/модели                                          |
|-----|--------------------------------|------------------------------------------------------------------|-----------------------------------------------------------------|
| 01  | `MDX_01_Sequencers`           | **NGS** + **Sanger CE / капиллярные генетические анализаторы** + ONT, PacBio, Element AVITI | Illumina (MiSeq..NovaSeq X+), MGI DNBSEQ, **ABI 3500/3500xL/3130/3730, SeqStudio/SeqStudio Flex** (Sanger CE), ONT MinION/PromethION, PacBio Revio, Helicon, Salus, Р-Ген |
| 02  | `MDX_02_Reagents_Libraries`   | Картриджи, flow cells, library prep, выделение НК                | Illumina TruSeq/Nextera, MGIEasy, KAPA, NEBNext, QIAGEN QIAseq, Twist, IDT xGen, Agilent SureSelect, KingFisher, MGISP, **+Pillar, Burning Rock, Novogene** |
| 03  | `MDX_03_Oncology_Panels`      | Онкопанели, BRCA/EGFR/KRAS/HRD/TMB/CGP                            | AmoyDx, **Pillar ONCO/Reveal, Burning Rock OncoScreen+, Novogene WES**, Parseq, OncoAtlas, TestGen, FoundationOne, Oncomine, Archer, Twist Pan-Cancer, TSO500, **+Personalis, Tempus, Caris** |
| 04  | `MDX_04_NIPT_PGT_HLA`         | НИПТ (Veriseq/Harmony/Vanadis), ПГТ-А/М, HLA, биочипы            | Illumina VeriSeq, Vanadis, BambniTest, LinkSeq, AllType, Olerup, Affymetrix CytoScan, Infinium BeadChip |
| 05  | `MDX_05_Service` *(опц.)*     | Сервис ТОЛЬКО Illumina/MGI/ABI 3500                              | Illumina, MGI, ABI 3500/3500xL                                  |
| 06  | `MDX_06_Sequencing_Services` 🆕 | **Услуги** CES/WES/WGS, биоинф. интерпретация, аутсорс NGS       | Genotek, Атлас Биомед, Парсек-Лаб, Хеликон-CRO, Macrogen, BGI-CRO, Novogene-services, Foundation Medicine как услуга |

### 🌡️ Общелаб — `general_lab` (5 + 1 опц.) 🆕
*файл: `keywords_config_general_lab.md`*

| №  | Имя                            | Что ищем                                                       | Ключевые бренды                                                  |
|----|--------------------------------|----------------------------------------------------------------|------------------------------------------------------------------|
| 01 | `LAB_01_Climate`              | CO2-инкубаторы, термостаты, климатокамеры, сушильные шкафы, муфельные печи | Memmert (UN/UF/IN/IF/IPP/ICO/HCP/HPP), Binder, Thermo Heracell/Heratherm, Lauda, Julabo, Huber, Nabertherm, Carbolite, Eppendorf ThermoMixer, СНОЛ, ШС |
| 02 | `LAB_02_Sterilization`        | Паровые автоклавы, сухожаровые стерилизаторы                  | Tuttnauer, Systec, Steris, Memmert SF, ВК-30/75, ГК-100, ГП-560, ШСС |
| 03 | `LAB_03_Evaporation`          | Роторные испарители, концентраторы, лиофилизаторы, ультразвук | Buchi Rotavapor, Heidolph Hei-VAP, IKA RV, Christ Alpha, Labconco FreeZone, Eppendorf Concentrator, Elma, Bandelin, Hielscher |
| 04 | `LAB_04_Mixing_Homogenization` | Мешалки, шейкеры, вортексы, гомогенизаторы, мельницы          | IKA (Eurostar, Ultra-Turrax, RCT, KS, T10..T50, A11/M20), Heidolph (Hei-TORQUE, SilentCrusher, Unimax), Velp, Stuart, Eppendorf Innova/Multitron, Retsch (PM/SM/GM/MM), Fritsch Pulverisette, BioSan, Корвет |
| 05 | `LAB_05_Reactors`             | Биореакторы, химические реакторы, синтезаторы, микроволновые  | Sartorius BIOSTAT/ambr, Eppendorf BioFlo/DASGIP, INFORS Multifors/Labfors, Applikon, Cytiva Xuri/XCellerex, Buchi miniclave/midiclave, Asynt ReactoMate, Radleys, Mettler OptiMax/EasyMax, Anton Paar Monowave, CEM Discover/Liberty Blue, Milestone Ethos, Parr 4848/4566, Berghof BR |
| —  | `LAB_06_Weighing_Water_pH` *(опц.)* | Аналитические весы, Milli-Q, pH-метры                       | Mettler-Toledo XPR/Cubis, Sartorius arium, OHAUS, Millipore Milli-Q, ELGA, Hanna, WTW |

### ⚗️ Капиллярный электрофорез / центрифуги / роботизация — `capillary_centrifuges_robotics` (3) 🆕
*файл: `keywords_config_capillary_centrifuges_robotics.md`*

| №  | Имя                                 | Что ищем                                                | Ключевые бренды                                                  |
|----|-------------------------------------|---------------------------------------------------------|------------------------------------------------------------------|
| 01 | `CER_01_Capillary_Electrophoresis` | CE для фармы/биохимии **НЕ Sanger** (CZE, MEKC, CIEF, CGE). Sanger CE-секвенаторы (ABI/SeqStudio) — в `MDX_01_Sequencers`, не здесь | Beckman PA 800 Plus / P/ACE / CESI 8000, Sciex BioPhase 8800, Agilent 7100 CE, Bio-Rad BioFocus, Lumex Капель |
| 02 | `CER_02_Centrifuges`               | Лабораторные центрифуги (все классы)                    | Eppendorf 5418..5920R, Hettich Universal/EBA/Mikro/Rotanta/Rotina, Sigma 1-7..6-16, Thermo Sorvall (Legend/ST/LYNX/WX), Beckman Avanti/Optima/Allegra/Microfuge, Hermle Z206..Z446, Kubota, Heraeus Megafuge, Hitachi Himac, ОПН, Liston, ELMI, BioSan |
| 03 | `CER_03_Liquid_Handling_Robotics`  | Liquid handlers, dispensers, acoustic, automated NGS prep | Tecan Freedom EVO/Fluent, Hamilton STAR/Vantage/NIMBUS, Beckman Biomek (i5/i7/NX/FX)/Echo 525/650, Eppendorf epMotion 5070..5075, Opentrons OT-2/Flex, Andrew+, Agilent Bravo/AssayMAP, PerkinElmer JANUS/Sciclone/Zephyr, **MGI Tech (MGISP-100/960/Smart 8, MGISTP-3000/7000, Stomatic, ZTRON, DNBelab C4)**, **Vazyme (VAHTS Smart 8, Hieff NGS Smart/Auto/MaxUp)**, **Nanodigm (IsoFlux, Nanodigm-1/А Анализатор для CTC/циркулирующих опухолевых клеток)** |

---

## Соответствие 8 темам из ТЗ заказчика

| ТЗ # | Тема                                                                    | Покрытие в файлах                                                  |
|------|-------------------------------------------------------------------------|--------------------------------------------------------------------|
| 1    | ГХ и ГХ-МС (параметры и бренды)                                        | `analytical` → `02_GC_GCMS`                                        |
| 2    | ВЭЖХ и ВЭЖХ-МС (параметры и бренды)                                    | `analytical` → `01_LC_LCMS_GPC_Prep`                              |
| 3    | Элементный анализ (АА, ИСП-ОЭС, ИСП-МС)                                | `analytical` → `03_ICP_OES` + `04_AAS` + `05_ICP_MS`              |
| 4    | Спектроскопия (UV, UV-vis, FTIR, UV-NIR)                               | `analytical` → `07_UV_Vis` + `08_FTIR`                            |
| 5    | Общелабораторные (инкубаторы, реакторы, термостаты, испарители)        | `general_lab` → `LAB_01..05` 🆕                                    |
| 6    | Генетика (Illumina, MGI, Сэнгер, Р-ГЕН, Хеликон, Thermo) + реагенты    | `molecular_diagnostics` → `MDX_01` + `MDX_02`                      |
| 7    | Панели (НИПТ, ПГТ, онкопанели, Archer, Pillar, AmoyDx, Burning Rock, Nanodigm, Novogene, Agilent, OncoAtlas, Парсек) + экзомы/геномы | `molecular_diagnostics` → `MDX_03` (онко) + `MDX_04` (НИПТ/ПГТ) + `MDX_06` (услуги CES/WES/WGS) 🆕 |
| 8    | Капиллярный электрофорез, центрифуги, роботизация                       | `capillary_centrifuges_robotics` → `CER_01..03` 🆕                 |

---

## Глобальные правила для всех 19 поисков

Едины для всех файлов (раздел «Глобальные параметры» в каждом):

| Параметр                       | Значение                                                  |
|--------------------------------|-----------------------------------------------------------|
| Фильтр include                 | `tender_keywords_include` (id 136, тип `text`)            |
| Фильтр exclude                 | `tender_keywords_exclude` (id 137, тип `text`)            |
| Тип закупки                    | Все: 44-ФЗ, 223-ФЗ, коммерческие, СНГ                     |
| Регион                         | Все регионы РФ + СНГ                                      |
| Дата публикации                | range, `от = СЕГОДНЯ−7`, `до = пусто`                     |
| Дата окончания подачи          | range, `от = СЕГОДНЯ`, `до = пусто`                       |
| Сортировка                     | `tender_sysPublishDate.desc`                              |
| Ключ дедупа (CLI)              | `tender_id` (формат `TL*`)                                |
| Метод API                      | `Export/Create` + `Export/Get`                            |
| Частота прогона CLI            | 1 раз в сутки в рабочие дни (cron `0 8 * * 1-5`)          |

---

## План внедрения (рекомендуемый порядок)

### Phase 1 — основные кластеры (уже почти готово)
1. ✅ Аналитика — 8 поисков уже настроены (см. id в `autosearches.toml`)
2. ✅ Молекулярка MDX_01..04 — настроены
3. 🆕 **Молекулярка MDX_06 (услуги CES/WES/WGS)** — настроить в этот спринт

### Phase 2 — общелабораторное (этот спринт)
4. 🆕 LAB_01 Climate — настроить первым (самый широкий охват по тендерам)
5. 🆕 LAB_02 Sterilization — настроить вместе с LAB_01 (часто в одних лотах)
6. 🆕 LAB_03 Evaporation — настроить
7. 🆕 LAB_04 Mixing_Homogenization — настроить
8. 🆕 LAB_05 Reactors — настроить

### Phase 3 — узкие специализации (этот или следующий спринт)
9. 🆕 CER_01 Capillary_Electrophoresis — низкий объём тендеров, может подождать
10. 🆕 CER_02 Centrifuges — высокий объём
11. 🆕 CER_03 Liquid_Handling_Robotics — средний объём

### Phase 4 — опциональные
- `09_Service`, `10_Consumables` (аналитика)
- `MDX_05_Service` (молекулярка)
- `LAB_06_Weighing_Water_pH` (общелаб)

---

## Operations cheat sheet

### Создать новый автопоиск в Tenderland UI
6 шагов одинаковые для всех — см. раздел 2/3 в любом из 4 файлов.

### Обновить даты в существующих автопоисках
Tenderland хранит **абсолютные** даты. Раз в неделю обновлять `от` в фильтрах публикации/окончания вручную, либо включить `--active-only` фильтр в CLI (Этап 3 разработки).

### Добавить новый бренд / модель в существующий поиск
1. Найти соответствующий файл и секцию (по таблице выше)
2. Добавить термин в одну INCLUDE-строку (помнить про синтаксис: `++` = AND-стемминг, `=` = точное совпадение)
3. Сохранить → перенастроить в Tenderland UI (там копи-пейст INCLUDE заново)

### Жалоба «слишком много шума» в каком-то поиске
1. Открыть Чеклист (раздел 9 в каждом файле)
2. Найти соответствующий пункт
3. Усилить EXCLUDE по конкретному ключу

### Жалоба «упускаем тендеры на X»
1. Проверить — в каком поиске X должен быть (по таблице выше)
2. Открыть INCLUDE этого поиска
3. Добавить X со всеми вариантами написания + транслит + русское название
4. Если X — отдельный домен (например, новый тип прибора) — рассмотреть создание нового файла/поиска

---

## Следующие шаги (для разработки)

1. **`md_parser.py`** — парсер INCLUDE/EXCLUDE строк из MD в JSON-фильтры (`config/searches/<topic>.json`). См. `ARCHITECTURE.md` раздел 6.2.
2. **`config/autosearches.toml`** — мапинг `topic` → Tenderland `autosearch_id` после ручной настройки 19 поисков в UI.
3. **`searcher/orchestrator.py`** — запускать все 19 поисков параллельно через `asyncio.gather`.
4. **Postgres `tenders` table** — единый dedup через `tender_id` независимо от того, в каком автопоиске пойман.

---

## Источники по 4 файлам

Каждый файл содержит свой раздел 11 «Источники для верификации» — ссылки на официальные страницы вендоров. Используются при доработке модельных линеек.
