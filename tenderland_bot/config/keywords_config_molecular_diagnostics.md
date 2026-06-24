# Tenderland — автопоиски по молекулярной диагностике

**Дата подготовки:** 2026-05-05
**Версия:** 1.1 (2026-05-14: добавлены Pillar Biosciences, Burning Rock, Novogene в MDX_02/03; новый MDX_06 — услуги секвенирования CES/WES/WGS)
**Источники:**
- `Tenderland_keywords_molecular_diagnostics.xlsx` — структура автопоисков, осмысленно адаптированный под молекулярку EXCLUDE, КТРУ-коды, российские реагентные бренды
- `tenderland_molecular_diagnostics_keywords.md` — расширенное покрытие моделей и реагентов, технические признаки NGS, гены/мишени, отдельные жёсткие EXCLUDE для приборов и расходников

> **Changelog 1.1 (2026-05-14):**
> - **MDX_03**: добавлены Pillar Biosciences (ONCO/Reveal Panel), Burning Rock (OncoScreen Plus, LungPlasma, LungCore), Novogene (NovaSeq-based panels), плюс пропущенные ранее `Caris MI Profile`, `Personalis ImmunoID`, `Tempus xT/xR`.
> - **MDX_02**: те же бренды добавлены как реагенты/library prep, плюс CleanNGS / SPRIselect.
> - Новый **MDX_06_Sequencing_Services** — услуги (а не приборы) полноэкзомного / полногеномного / целевого секвенирования (CES/WES/WGS), включая клиническую интерпретацию.

**Цель:** настроить набор автопоисков в кабинете Tenderland, покрывающих весь молекулярно-диагностический портфель (секвенаторы, расходники, NGS-панели, НИПТ/ПГТ/HLA, сервис), с явным исключением ПЦР-only рынка.

---

## 1. Карта автопоисков

| №  | Имя автопоиска                | Что ищем                                                                                  |
|----|--------------------------------|-------------------------------------------------------------------------------------------|
| 01 | `MDX_01_Sequencers`           | **NGS** (Illumina, MGI, GeneMind, Salus, Helicon, Р-Ген, ONT, PacBio, Element AVITI, Singular, Ultima) + **Sanger CE / капиллярные генетические анализаторы** (ABI 3500/3500xL/SeqStudio/3130xl/3730xl) — **только приборы** |
| 02 | `MDX_02_Reagents_Libraries`   | Расходники секвенирования (картриджи, flow cells, реагентные наборы), library prep (TruSeq/Nextera/MGIEasy/KAPA/NEBNext), выделение ДНК/РНК и автоматические станции (KingFisher/QIAamp/MGISP) |
| 03 | `MDX_03_Oncology_Panels`      | Онкологические NGS-панели и тесты: BRCA/EGFR/KRAS/BRAF/ALK/MSI/HRD/TMB/CGP, бренды AmoyDx/Parseq/OncoAtlas/TestGen/FoundationOne/Oncomine/QIAseq/Twist |
| 04 | `MDX_04_NIPT_PGT_HLA`         | НИПТ (Veriseq/Harmony/Panorama/Vanadis/BambniTest), ПГТ-А/М, HLA-типирование (LinkSeq/AllType/Olerup), биочипы (Affymetrix/Infinium/BeadChip) |
| —  | `MDX_05_Service` *(опц.)*     | Сервисные контракты только на Illumina, MGI/DNBSEQ, ABI 3500/3500xL — узкий скоуп                    |
| 06 | `MDX_06_Sequencing_Services` *(нов.)* | **Услуги** секвенирования: полноэкзомное (CES/WES), полногеномное (WGS), таргетное; клиническая интерпретация (биоинф.); ВКР/ГМП аутсорс |

**Опциональный 05** — включать когда будем системно охотиться за сервисными контрактами по НАШИМ инсталлированным платформам.

**Новый MDX_06** — отдельный кластер: НИИ/больницы заказывают **услугу** «выполнение полноэкзомного секвенирования образцов» вместо покупки прибора/реагентов. Это другой тип лота (часто 44-ФЗ услуги, ОКПД2 71.20). Включать сразу — растущий рынок аутсорса генетических исследований.

---

## 2. Скоуп — что включено / что нет

| Категория                                          | Решение  | Комментарий                                                                                  |
|----------------------------------------------------|----------|-----------------------------------------------------------------------------------------------|
| NGS-секвенаторы (Illumina, MGI, GeneMind и т.д.)   | ✅       | Полностью. В **MDX_01_Sequencers**                                                            |
| **Капиллярные секвенаторы Sanger CE** (ABI 3500/3500xL/SeqStudio/3130/3730) | ✅       | В **MDX_01_Sequencers** — это секвенирование по Сэнгеру (STR-анализ, мутации, HLA, идентификация). НЕ путать с фарма-CE (PA800, BioPhase) — те в `CER_01_Capillary_Electrophoresis` |
| Расходники Sanger CE (BigDye, POP-7, капилляры)    | ✅       | В **MDX_02_Reagents_Libraries**                                                               |
| Услуги Sanger-секвенирования                       | ✅       | В **MDX_06_Sequencing_Services** (включая `Sanger-услуг`, `Sanger++sequencing++service`)     |
| Нанопоровые (Oxford Nanopore)                      | ✅       | MinION/GridION/PromethION/Flongle                                                             |
| PacBio                                              | ✅       | Sequel/Revio/Vega                                                                             |
| Расходники секвенирования                           | ✅       | Картриджи, flow cells, реагентные наборы                                                      |
| Library prep                                        | ✅       | TruSeq, Nextera, MGIEasy, KAPA, NEBNext, AmpliSeq                                             |
| Выделение НК и автоматические станции               | ✅       | KingFisher, QIAamp, RNeasy, MGISP, MagMAX                                                     |
| Онкопанели                                          | ✅       | BRCA, EGFR, KRAS, BRAF, ALK, MSI, MMR, AKT, PTEN, TP53, HRD, TMB, CGP                         |
| НИПТ, ПГТ-А/М, HLA, биочипы                         | ✅       | Включая Vanadis, MaterniT21, Igenomix, GenDx                                                  |
| Сервис Illumina/MGI/ABI 3500                        | ✅       | Только наш инсталляционный портфель — отдельным автопоиском                                   |
| **ПЦР / RT-PCR / qPCR**                             | ❌       | Полностью отсечено через EXCLUDE (раздел 7.2). Это другой рынок                               |
| ИФА, экспресс-тесты, COVID/ВИЧ/гепатит PCR-only    | ❌       | Через EXCLUDE                                                                                 |
| Single-cell (10x Genomics, Visium, Xenium)         | ❌       | Другой рынок (одноклеточный анализ), не наша компетенция                                      |
| Микробиологические посевы                           | ❌       | Через EXCLUDE                                                                                 |
| Сервис всех остальных платформ                      | ❌       | Скоуп MDX_05 узкий — только то что мы реально обслуживаем                                     |
| **Услуги** секвенирования (CES/WES/WGS, биоинф.)    | ✅ MDX_06 | Аутсорс NGS, клиническая интерпретация, медицинские генетические сервисы. **Новый, отдельный кластер** |
| ВКР/ГМП аутсорс генетических исследований           | ✅ MDX_06 | Тендеры НИИ/больниц на «выполнение секвенирования образцов» вместо покупки оборудования       |

---

## 3. Алгоритм настройки в Tenderland UI

Один и тот же набор шагов **повторить 5 раз** (4 основных + опциональный сервис).

| Шаг | Действие                                                                                            |
|-----|-----------------------------------------------------------------------------------------------------|
| 1   | Создать новый автопоиск с именем из таблицы 1 (например `MDX_01_Sequencers`).                       |
| 2   | Добавить **один** фильтр «Поиск по ключевым словам». В поле «Включать» — INCLUDE-строка из раздела 6 для соответствующего автопоиска. В поле «Исключать» — EXCLUDE-строка из раздела 7.1 + 7.2 (или 7.3/7.4 если применимо). |
| 3   | Добавить фильтр «Дата публикации» (range): **от = СЕГОДНЯ−7 дней**, до = пусто.                      |
| 4   | Добавить фильтр «Дата окончания подачи» (range): **от = СЕГОДНЯ**, до = пусто.                       |
| 5   | *(опционально)* Добавить фильтр КТРУ/ОКПД2 (`tree_list`) — коды из раздела 8.                        |
| 6   | Сохранить → скопировать `id` из URL (`?id=XXXXX`).                                                  |
| 7   | Прислать 4-5 пар «имя → id» — внесу в `tenderland_bot/config/autosearches.toml`.                     |

> **Напоминание про даты:** Tenderland хранит абсолютные даты. Раз в неделю обновлять «от» в фильтрах публикации/окончания вручную. Альтернатива — клиентский фильтр `--active-only` в CLI (планируется).

---

## 4. Глобальные параметры (одинаковы для всех 5 автопоисков)

| Параметр                       | Значение                                                  | Комментарий                                          |
|--------------------------------|-----------------------------------------------------------|------------------------------------------------------|
| Фильтр include                 | `tender_keywords_include` (id 136, тип `text`)            | Полнотекст по name + notification + files            |
| Фильтр exclude                 | `tender_keywords_exclude` (id 137, тип `text`)            | То же поле                                           |
| Тип закупки                    | Все: 44-ФЗ, 223-ФЗ, коммерческие, СНГ                     | Не ограничивать                                      |
| Регион                         | Все регионы РФ + СНГ                                      | Не ограничивать                                      |
| Дата публикации                | range, `от` = СЕГОДНЯ−7, `до` = пусто                     | Скользящее окно с буфером на сбои                    |
| Дата окончания подачи          | range, `от` = СЕГОДНЯ, `до` = пусто                       | Только активные                                      |
| Сортировка (orderBy в API)     | `tender_sysPublishDate.desc`                              | Новые сверху                                         |
| Ключ дедупа (на стороне CLI)   | `tender_id` (формат `TL*`)                                | НЕ regNumber                                          |
| Метод API                      | `Export/Create` + `Export/Get`                            | Модуль API (бесплатный, free-tier 300/300/9000)      |
| Частота прогона CLI            | 1 раз в сутки в рабочие дни (cron `0 8 * * 1-5`)          | Внутри free-tier                                     |

---

## 5. Синтаксис ключевых слов Tenderland (краткая шпаргалка)

| Оператор   | Значение                                                    | Пример                              |
|------------|--------------------------------------------------------------|-------------------------------------|
| `(пробел)` | OR между терминами                                          | `Illumina MGI` → один из двух        |
| `++`       | AND со стеммингом — оба слова в любых формах                | `секвенирован++ДНК` → «секвенирование ДНК», «секвенированной ДНК» и т.д. |
| `+`        | соединение в фразу при точном совпадении                    | `тройн+квадрупол`                    |
| `=`        | префикс точного совпадения, отключает русскую морфологию    | `=NGS`, `=NovaSeq`, `=BRCA1`         |

Латинские бренды (Illumina, MGI, NovaSeq) можно писать без `=` — латиница и так трактуется как точное совпадение. Префикс `=` ставлю там, где морфология русского может разрушить смысл (например `=PGT-A` иначе превратится в «пгт» как «посёлок городского типа»).

---

## 6. INCLUDE-строки для 5 автопоисков

> Каждая строка ниже — **одной строкой** для копи-пэйст.

### 6.1. `MDX_01_Sequencers` — секвенаторы и генетические анализаторы

```text
секвенатор секвенатор++ДНК секвенатор++РНК секвенатор++нуклеинов секвенатор++генетическ генетическ++секвенатор генетическ++анализатор анализатор++генетическ молекулярно-генетическ++анализатор прибор++секвенирован аппарат++секвенирован система++секвенирован платформа++секвенирован система++генетическ++анализ высокопроизводительн++секвенирован массов++параллельн++секвенирован параллельн++секвенирован =NGS =MPS секвенирован++нового++поколен следующ++поколен++секвенир Next++Generation++Sequencing Next-Generation++Sequencing секвенирован++ДНК секвенирован++РНК =DNA-Seq =RNA-Seq =WGS =WES полногеномн++секвенир полноэкзомн++секвенир капиллярн++секвенатор капиллярн++генетическ++анализатор капиллярн++электрофорез секвенирован++Сенгер секвенирован++Сэнгер сэнгеровск++секвенирован =Sanger Sanger++sequencing Sanger++sequencer фрагментн++анализ fragment++analysis STR++анализ MLPA++фрагмент микросателлитн++анализ нанопоров++секвенатор нанопоров++секвенирован nanopore++sequencing nanopore++sequencer нанопорн++секвенирован одномолекулярн++секвенир =SMRT =DNB-секвенир длинн++прочтен =long-read long-read++sequencing сверхдлинн++прочтен real-time++sequencing =Iso-Seq Illumina Иллюмина Илюмина Альбиоген Albiogen MiSeq MiSeqDx MiSeq++Dx MiSeq++i100 MiniSeq iSeq iSeq++100 NextSeq NextSeq++500 NextSeq++550 NextSeq++550Dx NextSeq++1000 NextSeq++2000 NovaSeq NovaSeq++5000 NovaSeq++6000 NovaSeq++6000Dx NovaSeq++X NovaSeq++X++Plus HiSeq HiSeq++1500 HiSeq++2000 HiSeq++2500 HiSeq++3000 HiSeq++4000 Genome++Analyzer GAIIx iScan iScanDx Infinium BeadChip MGI MGI++Tech ЭмДжиАй МГИ BGI БГИ Beijing++Genomics++Institute Complete++Genomics DNBSEQ DNBSEQ-G50 DNBSEQ-G99 DNBSEQ-G400 DNBSEQ-G800 DNBSEQ-T1 DNBSEQ-T7 DNBSEQ-T10 DNBSEQ-T20 DNBSEQ-E25 MGISEQ MGISEQ-200 MGISEQ-2000 MGISEQ-T7 MGISEQ-G400RS BGISEQ HELICON Хеликон Helicon HELICON++G50 HELICON++G400 Хеликон++G50 Хеликон++G400 Геноскан Genoscan Genoskan Биофьюжн Biofusion BioFusion Salus Salus++Bio Salus++BioMed Salus++Pro Salus++Pro++RS Salus++Evo Р-Ген Р-Ген++2000 РГен++2000 P-Gen++2000 GeneMind Genemind ДжинМайнд Джинмайнд GenoLab GenoLab++M FASTASeq FASTASeq++300 FASTASeq++500 FASTASeq++S SURFSeq SURFSeq++5000 SURFSeq++Q GenoCare MrLH-96 Oxford++Nanopore Oxford++Nanopore++Technologies Оксфорд++Нанопор =ONT MinION MinION++Mk1B MinION++Mk1C GridION PromethION PromethION++2 PromethION++P2 PromethION++P24 PromethION++P48 Flongle VolTRAX PacBio Pacific++Biosciences Sequel Sequel++II Sequel++IIe Revio Vega SMRT++Cell Thermo++Fisher ThermoFisher Термо++Фишер Applied++Biosystems =ABI Эплайд++Биосистемс Life++Technologies Ion++Torrent IonTorrent Ion++PGM Ion++Proton Ion++S5 Ion++GeneStudio Ion++GeneStudio++S5 Ion++Chef Ion++OneTouch Ion++Genexus Genexus SeqStudio SeqStudio++Flex SeqStudio++Genetic++Analyzer SeqStudio++Plus +SeqStudio+8 +SeqStudio+24 ABI++3500 ABI++3500xL =3500xl =3500XL 3500++Genetic++Analyzer 3500xL++Genetic++Analyzer 3500++8-capillary 3500xL++24-capillary 3130 3130xl 3130++Genetic++Analyzer 3730 3730xl 3730++Genetic++Analyzer 3730xL++Genetic++Analyzer +ABI+3130 +ABI+3130xl +ABI+3730 +ABI+3730xl 310++Genetic++Analyzer ABI++310 Applied++Biosystems++3500 Applied++Biosystems++3500xL Applied++Biosystems++SeqStudio +Genetic+analyzer+24-capillary +Genetic+analyzer+8-capillary +Genetic+analyzer+5-dye +Genetic+analyzer+6-dye фрагментн++анализатор STR-анализатор STR-анализ STR++профилирован микросателлитн++генотипирован +Identifiler +PowerPlex +GlobalFiler +Yfiler =GeneMapper GeneMapper++ID GeneMapper++ID-X +GeneMapper+IDX +Geneoscan +GeneScan =Mixture+Analysis +Identifiler+Plus +Identifiler+Direct +VeriFiler судебно-медицинск++ДНК-идентификац ДНК-идентификац ДНК++профил++криминал генотипирован++для++криминалистическ криминалистическ++ДНК-анализ Element++Biosciences AVITI AVITI24 Singular++Genomics G4++Sequencing Ultima++Genomics UG-100 =UG100 Roche++454 GS++Junior GS++FLX PyroMark Verogen MiSeq++FGx ForenSeq Beckman++Coulter GenomeLab GeXP
```

### 6.2. `MDX_02_Reagents_Libraries` — расходники, библиотеки, выделение НК

```text
картридж++секвенатор картридж++секвенирован картридж++NGS картридж++Illumina картридж++MGI картридж++DNBSEQ =flow+cell =flowcell flow-cell проточн++ячейк проточная++ячейка проточн++чип ячейк++секвенатор ячейк++NGS sequencing++cell секвенирующ++ячейк sequencing++cartridge reagent++cartridge реактивн++картридж картридж++реагентов промывочн++картридж wash++cartridge wash++kit промывк++проточн++ячейк расходн++материал++секвенатор расходн++материал++секвенирован реагент++секвенатор реагент++секвенирован набор++реагент++секвенир набор++реагент++NGS sequencing++reagents sequencing++kit sequencing++reagent++kit SBS++reagent++kit cluster++kit cartridge++kit flow++cell++kit библиотек++секвенирован библиотек++NGS подготовк++библиотек приготовлен++библиотек создан++библиотек подготовка++NGS++библиотек =library+prep library++preparation library++preparation++kit NGS++library++prep DNA++library++prep RNA++library++prep stranded++RNA++library WGS++library WES++library exome++library target++enrichment таргетн++обогащен обогащен++библиотек hybrid++capture гибридизационн++захват capture++panel ампликонн++библиотек adapter++ligation лигирован++адаптеров адаптер++NGS адаптер++секвенирован индексн++адаптер adapter++kit index++kit barcode++kit баркод++NGS UMI++адаптер unique++dual++index выделен++ДНК выделение++ДНК очистк++ДНК очистка++ДНК выделен++РНК выделение++РНК очистк++РНК выделен++нуклеинов++кислот выделен++нуклеинов экстракц++нуклеинов экстракц++ДНК экстракц++РНК набор++выделен++ДНК набор++выделения++ДНК набор++выделен++ДНК/РНК набор++выделен++РНК набор++выделен++нуклеинов набор++экстракц++ДНК DNA++extraction DNA++purification RNA++extraction nucleic++acid++extraction cfDNA++extraction циркулирующ++ДНК внеклеточн++ДНК cell-free++DNA =ctDNA =cfDNA FFPE++DNA FFPE++RNA формалин++фиксирован парафин++залит =FFPE автоматическ++пробоподготовк автоматическ++выделен++ДНК станция++пробоподготовк магнитн++частиц++выделен магнитн++частиц магнитн++сорбент magnetic++beads =KingFisher =MagMAX =PureLink =QIAamp =RNeasy =DNeasy =AllPrep =QIAcube =QIAsymphony =MGISP-100 =MGISP-960 =AMPure =AMPure+XP =CleanNGS CleanNGS Beckman++CleanNGS SPRIselect SPRI++select SPRI bead++cleanup очистк++библиотек контроль++библиотек нормализац++библиотек quantification++library количественн++оценк++библиотек качество++библиотек Bioanalyzer TapeStation Fragment++Analyzer Qubit Quant-iT PicoGreen dsDNA++HS++Assay KAPA++Library++Quantification Illumina++DNA++Prep =Nextera =Nextera+XT =Nextera+Flex =Nextera+DNA =TruSeq =TruSight =AmpliSeq+for+Illumina DNA++Prep++with++Enrichment MiSeq++Reagent++Kit NextSeq++Reagent++Kit NovaSeq++Reagent++Kit iSeq++Reagent++Kit =MGIEasy MGIEasy++FS MGIEasy++RNA MGIEasy++Exome MGIEasy++Universal DNBSEQ++reagent DNBSEQ++sequencing++set DNBSEQ++flow++cell DNB++making++kit DNB++load++reagent DNA++nanoball++kit circularization++kit ONT++ligation ONT++rapid ONT++barcoding ONT++flow++cell MinION++flow++cell PromethION++flow++cell Flongle++flow++cell sequencing++buffer loading++beads motor++protein nanopore++wash++kit =KAPA =KAPA+HyperPrep =KAPA+HyperPlus =Roche+KAPA =Lexogen =NEBNext New++England++Biolabs =NEB =Swift =Accel-NGS =QIAGEN Киаген =QIAseq =Twist Twist++Bioscience Twist++Comprehensive Twist++Pan-cancer Twist++Exome =IDT Integrated++DNA++Technologies =xGen IDT++xGen =SureSelect Agilent++SureSelect Agilent++SureSelect+XT Agilent++SureSelect+XT+HS Agilent++SureSelect+QXT ArcherDX Archer++DX VariantPlex FusionPlex Archer++Fusion Archer++Reveal Beckman++Coulter Amoy++Dx =AmoyDx Эймой++Дикс Pillar++Biosciences =Pillar Pillar++ONCO Pillar++ONCO/Reveal Pillar++Reveal Pillar++Reveal+Panel Pillar++Heredity Pillar++Heredity++Panel Burning++Rock =BurningRock Burning++Rock++Dx Burning++Rock++Biotech Burning++Rock++OncoScreen OncoScreen++Plus LungPlasma LungCore Burning++Rock++LungPlasma Burning++Rock++LungCore Novogene Новоген Новожен =Novogene Novogene++library Novogene++NovaPath Novogene++WES Novogene++WGS Nanodigm NanoDigm Нанодигм НаноДигм Нанодайм НаноДайм Парсек Parseq Parsec Парсек++Лаб Parseq++Lab Prep&Seq Ready-U-Panel OncoScope OncoScope++NSCLC Онко++Атлас ОнкоАтлас Onco++Atlas =OncoAtlas ТестГен TestGen Тест++Ген =Testgen Personalis Personalis++ImmunoID ImmunoID Personalis++NeXT NeXT++Personal Tempus++xT Tempus++xR Tempus++Onco Caris Caris++MI Caris++MI++Profile BigDye =BigDye BigDye++Terminator BigDye++Terminator++v1.1 BigDye++Terminator++v3.1 BigDye++XTerminator BigDye++Direct +BDX64 POP-4 POP-6 POP-7 +POP4 +POP6 +POP7 POP++полимер полимер++POP-7 полимер++POP-4 полимер++POP-6 капиллярн++массив капиллярн++матриц 36++cm++array 50++cm++array 36-cm++array 50-cm++array 36++см++капиллярн 50++см++капиллярн 8-капиллярн++массив 24-капиллярн++массив capillary++array Genetic++Analyzer++capillary HiDi++Formamide HiDi-Formamide Hi-Di формамид формамид++Hi-Di GeneScan++600++LIZ GeneScan++500++LIZ GeneScan++LIZ Size++Standard внутрення++размерн++стандарт LIZ-стандарт LIZ++size++standard буферный++раствор++ABI ABI++Buffer 10X++Running++Buffer Anode++Buffer Cathode++Buffer Anode++Buffer++Container Cathode++Buffer++Container ABI++Running++Buffer Performance++Optimized++Polymer Vazyme Вазайм Вазим =Vazyme VAHTS VAHTS++Universal VAHTS++Pro VAHTS++Smart VAHTS++Stranded Hieff++NGS Hieff-NGS Hieff++FFPE Hieff++Onco Hieff++Smart MaxUp +Vazyme+VAHTS Vazyme++Smart+8 Vazyme++MaxUp Vazyme++Auto Vazyme++Hieff =FoundationOne Foundation++One Foundation++Medicine
```

### 6.3. `MDX_03_Oncology_Panels` — онкологические NGS-панели и тесты

```text
NGS++панел NGS-панел онкопанел онко++панел онкологическ++панел панел++генов панель++генов генетическ++панел молекулярн++панел молекулярно-генетическ++панел таргетн++панел таргетн++секвенирован targeted++sequencing targeted++panel cancer++panel oncology++panel solid++tumor++panel солидн++опухол опухолев++панел молекулярн++онколог комплексн++геномн++профилирован =CGP comprehensive++genomic++profiling комплексное++геномное++профилирование молекулярно-генетическ++профилирован геномн++профиль опухол профиль++мутац профилирован++опухол мутационн++профилирован генотипирован++опухол молекулярн++профилирован++опухол наследствен++онкологическ наследствен++онко hereditary++cancer tumor++profiling рак++молочн++желез молочн++желез breast++cancer РМЖ молочн++желез++онкомаркер наследственн++рак++молочн наследственн++рак++яичник ovarian++cancer рак++яичник BRCA-тест =BRCA =BRCA1 =BRCA2 =PALB2 =CHEK2 =ATM =TP53 =PTEN =AKT =AKT1 =AKT2 =AKT3 =PIK3CA =ESR1 =ERBB2 =HER2 =CDK12 HRD homologous++recombination++deficiency гомологичн++рекомбинац колоректальн++ра колоректальн++рак colorectal++cancer =CRC рак++толст++кишк рак++ободочн++кишк рак++прям++кишк =KRAS =NRAS =BRAF BRAF++V600E =V600E =MSI =MSS =MMR =MLH1 =MSH2 =MSH6 =PMS2 =EPCAM =POLE =POLD1 =APC =CTNNB1 рак++лёгк рак++легк лёгочн++ра легочн++ра рак++легк++немелкоклеточн немелкоклеточн++рак++легк =НМРЛ =NSCLC lung++cancer =EGFR =ALK =ROS1 KRAS++G12C =G12C =MET =METex14 MET++exon++14 =RET =NTRK =NTRK1 =NTRK2 =NTRK3 =STK11 =KEAP1 =DDR2 =FGFR1 =FGFR2 =FGFR3 рак++предстательн++желез рак++яичник меланом =TMB =LOH =CNV =CNA =SNV =InDel =indel =fusion =fusions gene++fusion слияни++генов транслокац copy++number++variation copy++number++alteration мутац++ген мутационный++статус генетическ++вариант соматическ++мутац герминальн++мутац germline somatic liquid++biopsy жидкостн++биопс AmoyDx Amoy++Dx Amoy++Diagnostics Амой АмойДх AmoyDx++Essential AmoyDx++Comprehensive AmoyDx++Master AmoyDx++HANDLE HANDLE++Classic HANDLE++OncoPro HANDLE++HRR HRD++Focus HRD++Complete BRCA++Pro =ANDAS =ARAS Pillar++Biosciences =Pillar Pillar++ONCO Pillar++ONCO/Reveal Pillar++Reveal Pillar++Reveal+Panel Pillar++Heredity Pillar++Heredity++Panel Pillar++Lung Pillar++Pan-Cancer Pillar++oncoReveal Pillar++stemSCREEN Burning++Rock =BurningRock Burning++Rock++Dx Burning++Rock++Biotech Burning++Rock++OncoScreen OncoScreen++Plus OncoScreen++Comprehensive LungPlasma LungCore Burning++Rock++LungPlasma Burning++Rock++LungCore Burning++Rock++OncoCommons Burning++Rock++OncoMix Burning++Rock++HRR Novogene Новоген Новожен =Novogene Novogene++NovaPath Novogene++WES Novogene++WGS Novogene++NGS++panel Novogene++clinical Parseq Парсек Parseq++Lab Prep&Seq Prep++Seq Ready-U-Panel OncoScope OncoScope++NSCLC OncoAtlas Онко++Атлас ОнкоАтлас Onco++Atlas TestGen ТестГен Тест++Ген Nanodigm NanoDigm Нанодигм НаноДигм =FoundationOne Foundation++One Foundation++Medicine =FoundationOne+CDx FoundationOne+Liquid FoundationOne+Liquid+CDx FoundationOne+CDx+xT FoundationOne+Heme =MSK-IMPACT MSK++IMPACT =Oncomine =OncoMine Oncomine++Comprehensive Oncomine++Focus Oncomine++Solid Oncomine++Pan-Cancer Oncomine++Precision =QIAseq QIAGEN++QIAseq QIAseq++TMB QIAseq++HRD QIAseq++FX =ArcherDx Archer++DX Archer Archer++VariantPlex Archer++FusionPlex Archer++Reveal Archer++Reveal+Lung Archer++Reveal+ALK Archer++LiquidPlex =xGen IDT++xGen IDT++xGen+Lung+v2 IDT++xGen+Pan-Cancer =SureSelect Agilent++SureSelect Agilent++SureSelect+XT Agilent++SureSelect+XT+HS Agilent++SureSelect+QXT Agilent++SureSelect+Cancer Twist++Bioscience Twist++Comprehensive Twist++Pan-cancer Twist++Exome Twist++Custom Twist++CarrierScreen NEBNext NEBNext++Direct KAPA++HyperPlus KAPA++HyperCap =TruSight+Oncology =TruSight+Oncology+500 TSO500 =TruSight+Tumor TruSight+Tumor+170 =TruSight+Hereditary +TruSight+Cardio TruSight+RNA Personalis Personalis++ImmunoID ImmunoID NeXT++Personal Tempus++xT Tempus++xR Tempus++Onco Caris++MI Caris++MI++Profile MI++Tumor++Seek MGIEasy++Onco MGI++Exome Salus++NGS+Onco
```

### 6.4. `MDX_04_NIPT_PGT_HLA` — НИПТ, ПГТ, HLA, биочипы

```text
=НИПТ =NIPT неинвазивн++пренатальн неинвазивн++пренатальн++тест неинвазивн++пренатальн++скрининг пренатальн++секвенирован prenatal++screening prenatal++test cfDNA++prenatal внеклеточн++ДНК++плод =cffDNA fetal++fraction фетальн++фракц анеуплоид анеуплоидии трисом трисомия++21 трисомия++18 трисомия++13 =Veriseq =VeriSeq =Harmony =Panorama =Vanadis =BambniTest =MaterniT21 =ПГТ =PGT =PGT-A =PGTA =ПГТ-А =ПГТА =PGT-M =PGTM =ПГТ-М =ПГТМ =ПГТ-СР =PGS =PGD преимплантационн++генетическ преимплантационн++генетическ++тест преимплантационн++генетическ++диагност преимплантационн++генетическ++скрининг преимплантац++диагност анеуплоид++эмбрион моногенн++заболеван эмбрион++секвенирован =EmbryoMap =Igenomix =HLA HLA++типирован HLA-типирован HLA++генотипирован HLA-генотипирован =HLA+typing гистосовместим лейкоцитарн++антиген =HLA-A =HLA-B =HLA-C =HLA-DRB1 =HLA-DQB1 =HLA-DPB1 =KIR трансплантац++типирован иммуногенетическ++типирован =LinkSeq =AllType =NGSGo =Olerup =GenDx биочип биочипы биочип-ИМБ микрочип++ДНК ДНК++микрочип ДНК-чип DNA++microarray microarray++scanner микрочипов++анализ микроматричн++анализ хромосомн++микроматричн хромосомн++микроматричн++анализ array++scanner =microarray =SNP-array SNP-чип =CGH сравнительн++геномн++гибридизац array++CGH iScan BeadArray =BeadChip =Infinium =CytoSNP =OncoArray =MethylationEPIC EPIC++array Global++Screening++Array =GSA =Affymetrix =CytoScan =OncoScan =Axiom
```

### 6.6. `MDX_06_Sequencing_Services` — услуги секвенирования (CES/WES/WGS, биоинформатика) *(новый, рекомендуется к включению)*

Отдельный кластер: тендеры на **услугу** «выполнение секвенирования образцов» (а не покупка прибора/реагентов). НИИ, больницы, медицинские центры часто закупают такие услуги вместо капитальных инвестиций. ОКПД2 обычно 71.20 (научно-технические услуги) или 86.10 (медицинские услуги).

```text
услуг++секвенирован услуг++секвенир оказан++услуг++секвенир выполнен++секвенирован выполнен++секвенир секвенирован++образц секвенирование++образц провести++секвенир аутсорс++секвенир секвенирован++на++аутсорс sequencing++service sequencing++as++service NGS-сервис NGS-аутсорс секвенирован++клиническ клиническ++секвенирован клиническ-молекулярн полногеномн++секвенирован полногеномн++секвенир WGS-услуг whole++genome++sequencing полногеномн++анализ полногеномн++исследован экзомн++секвенирован полноэкзомн++секвенирован полноэкзомн++секвенир WES-услуг whole++exome++sequencing экзомн++анализ экзомн++исследован клиническ++экзом =CES =WES =WGS =sWGS =scWGS shallow++WGS таргетн++секвенир таргетн++секвенирован таргетированн++секвенирован панельн++секвенирован targeted++sequencing++service РНК-секвенирован транскриптомн++секвенир =RNA-Seq RNA-Seq++услуг secret-Seq Сэнгер-секвенирован Сэнгер-секвенир Сенгер++услуг Sanger++sequencing++service Sanger-услуг ChIP-Seq ATAC-Seq метил-секвенирован метилирован++секвенир bisulfite++sequencing methylation++sequencing 16S-секвенирован 16S-rRNA метагеномн++секвенир метагеномик метагеномн++анализ shotgun++metagenomics клиническ++биоинформатик биоинформатическ++анализ биоинф++интерпретац вариант-каллинг интерпретац++варианнт интерпретац++генетическ++вариант clinical++variant++interpretation вариант++интерпретац ACMG-классификац +ACMG+classification +variant+annotation NGS-анализ NGS++данных++анализ pipeline++биоинформ +bioinformatics+pipeline +variant+calling++NGS provider++генетическ++услуг лабораторн++услуг++NGS услуг++лаборатор++NGS контракт++на++секвенир аутсорсинг++NGS NGS-CRO Genomics-CRO Genomics++as++a++Service GaaS аутосекр Sequencing-aaS provider++secrecy genomics-CRO ImmunoID NeoTYPE +Caris+MI+Profile Tempus++xT++услуг Foundation++Medicine++услуг F1CDx-услуг Foundation++One++услуг Personalis++услуг Genoscan-услуг Genoscan++Aurora-услуг Russian-NGS-CRO Atlas++Biomed Geno++Lab GeneTechnology Acumed Хеликон-Лаб БиоФьюжн-Лаб Парсек-Лаб BioFusion-Lab OncoAtlas-услуг Test-Gen-услуг ТестГен-услуг ImmunoExpert NextOncology NeoGenomics Novogene-аутсорс Novogene++services Novogene++для++клиент CD++Genomics Macrogen Macrogen++услуг Macrogen-EuropeFul++Genomics BGI-Tech-Solutions BGI-CRO MGI-Tech-CRO Hellobio-CRO LC-Sciences LC-Sciences-услуг CD++Genomics-услуг VariantPlex-услуг Иркутская-Лаб Иркутск++НГС Гены-Лаб Гены-Лаб++услуг Хеликон-CRO Genotek Геноаналитика Геноанализ Атлас++Биомед DNAFLAB Атлас++Biomed Парсек-EVO ОнкоАтлас-CRO услуг++полноэкзомн услуг++полногеномн услуг++подготовк++библиотек подготовка++библиотек++на++заказ услуг++NGS-библиотек услуг++пробоподготовк++NGS пробоподготовк++NGS++услуг
```

> Этот автопоиск пересекается с MDX_02/03 на тендерах «прибор + реагенты + услуга интерпретации». Дедупликация по `tender_id` в CLI отсечёт повторы.

### 6.5. `MDX_05_Service` — сервис только Illumina/MGI/ABI 3500 *(опц.)*

```text
техническ++обслуживан техобслуживан сервисн++обслуживан сервис++секвенатор обслуживание++секвенатор обслуживан++секвенатор ремонт++секвенатор диагностика++секвенатор сервис++генетическ++анализатор обслуживан++генетическ++анализатор ремонт++генетическ++анализатор профилактическ++обслуживан регламентн++обслуживан планов++обслуживан планов++техническ++обслуживан++секвенатор регулярн++техническ++обслуживан++секвенатор сервисн++контракт сервисн++поддержк техническ++поддержк восстановлен++работоспособн калибровк++секвенатор квалификац++оборудован валидац++секвенатор IQ OQ PQ =IQ-OQ =OQ-PQ =IQ/OQ/PQ Q-аттестац инсталляционн++квалификац операционн++квалификац эксплуатационн++квалификац запасн++част запчаст++секвенатор Illumina Иллюмина MiSeq MiSeqDx NextSeq NextSeq++550 NextSeq++550Dx NextSeq++1000 NextSeq++2000 NovaSeq NovaSeq++6000 NovaSeq++X iSeq MiniSeq HiSeq iScan MGI MGI++Tech BGI DNBSEQ MGISEQ DNBSEQ-G50 DNBSEQ-G99 DNBSEQ-G400 MGISEQ-200 MGISEQ-2000 HELICON++G50 HELICON++G400 Хеликон++G50 Хеликон++G400 Applied++Biosystems =ABI ABI++3500 ABI++3500xL =3500xl =3500XL 3500++Genetic++Analyzer 3500xL++Genetic++Analyzer Applied++Biosystems++3500 Applied++Biosystems++3500xL Thermo++Fisher Life++Technologies SeqStudio
```

---

## 7. EXCLUDE-строки

### 7.1. Базовый EXCLUDE (применяется ко всем 5 автопоискам)

База — Excel, осмысленно адаптированная под молекулярку. **Намеренно убраны** (по сравнению с EXCLUDE для аналитики): `антител`, `пробир`, `набор+лаборатор+диагност`, `проведение+лаб+исследований`, `родовспомож`, `крысы`, `животн` — могут отсечь релевантные молекулярные тендеры (например НИПТ связан с акушерством, а наборы для выделения ДНК могут содержать пробирки в комплекте).

```text
ноутбук фоторадар транспорт транспорт+средств автомобил автомобиль обществ+мнен охот посуд лабор+посуд массаж арматур фильтроэлемент фрезер фотоник электроплит масс+отдых криптограф криптограф+оборуд вычисл+техника фонтан крипто парков+простран электрон+очеред судостроен слепоч+масс поток+посетит вентиляц пищеблок конференц+связь =гирь =гиря =гель навигац дошкольн барометр налогов =ИКТ научн+чтен пылесос искусств+вентиляц+легк пьезоэлектрич проектор кондиционер сантех дым подстил+грызун подстил поставк+имуществ контейнер уборк+помещен тестомес автомойк водител вакуумн+уборочн+машин поставк+продукт+питан чищен+картофел проведен+гигиенич+подготовк перчатки+химич+стойк погрузк+грузов+вагон клининг+услуг огнезащитн+обработк расчетн+графич+станц комплексн+уборк+помещен вакуум+убороч+шасси газет полуфабр овощ ноутбук компьютер сервер принтер картридж++принтер бумага мебель халат маск респиратор дезинфицир моющ++средств клининг
```

### 7.2. Дополнительный EXCLUDE: ПЦР / ИФА / single-cell (применяется ко всем 5)

**Критично**: эти ключи отсекают ПЦР-only рынок, который не наш фокус. Ставить **в дополнение** к 7.1 в одно поле «Исключать» через пробел.

```text
ПЦР ПЦР-РВ ПЦР++РВ РТ-ПЦР ОТ-ПЦР =rt-PCR =RT-PCR =qPCR real-time++PCR real++time++PCR ПЦР++реальном++времени полимеразн++цепн++реакц амплификатор термоциклер Rotor-Gene RotorGene CFX96 QuantStudio LightCycler ДТпрайм Дтпрайм Cobas++4800 cobas++z480 PCR++panel PCR++kit ИФА =ELISA иммуноферментн экспресс-тест тест-полос микробиологическ++посев питательн++среда бактериологическ++посев COVID SARS-CoV-2 коронавирус грипп ОРВИ ВИЧ сифилис гепатит туберкулез++ПЦР single-cell single++cell singlecell одноклеточн 10x++Genomics Chromium++Controller Chromium++Next++GEM spatial++transcriptomics пространственн++транскриптом Visium Xenium
```

> **Не применяется к `MDX_05_Service`** — для сервиса блок про single-cell можно убрать (если кто-то заказывает сервис на 10x Chromium — не наш скоуп, но вреда не будет). ПЦР-блок в сервисе тоже неактуален: автопоиск по сервису и так ограничен моделями Illumina/MGI/ABI 3500.
>
> **Для `MDX_06_Sequencing_Services`:** EXCLUDE 7.2 применять **с осторожностью** — в описаниях услуг секвенирования часто упоминаются ПЦР-этапы как часть pipeline (амплификация библиотек, qPCR-нормализация). Если на первом прогоне MDX_06 «обнуляется» из-за EXCLUDE — снять `ПЦР ПЦР-РВ ПЦР++РВ` и оставить только узкие маркеры PCR-only продуктов: `cobas Rotor-Gene LightCycler ДТпрайм CFX96 QuantStudio амплификатор`.

### 7.3. Опциональный жёсткий EXCLUDE для `MDX_01_Sequencers` (только приборы)

Применять **только** если нужно строго отсекать тендеры на расходники без приборов. **По умолчанию НЕ применять** — пропускает тендеры «прибор + первый комплект расходников», которые бывают.

```text
расходн++материал картридж++секвенатор картридж++секвенирован проточн++ячейк ячейк++секвенатор ячейк++NGS реагент++секвенатор реагент++секвенирован набор++реагент++секвенир набор++реагент++NGS подготовк++библиотек библиотек++секвенирован адаптер++NGS индекс++NGS баркод++NGS буфер фермент полимераза магнитн++частиц калибратор контрольн++образец стандартн++образец
```

### 7.4. Опциональный жёсткий EXCLUDE для `MDX_02/03/04` (только реагенты/панели/тесты)

Применять **только** если нужно строго отсекать капитальные закупки приборов. **По умолчанию НЕ применять** — пропускает интересные тендеры на «прибор + панель» и «прибор + сервис».

```text
поставк++секвенатор приобретен++секвенатор закупк++секвенатор секвенатор++нуклеинов++кислот генетическ++анализатор анализатор++генетическ прибор++секвенирован аппарат++секвенирован система++секвенирован техническ++обслуживан ремонт сервисн++обслуживан
```

---

## 8. КТРУ/ОКПД2 коды (опционально)

Если в Tenderland UI доступен фильтр КТРУ/ОКПД2 (`tree_list`) — добавить в каждый автопоиск как **дополнительный** фильтр (AND-логика, сужает результаты). Если такого фильтра в твоём кабинете нет — добавить эту строку в текстовый INCLUDE по позициям лота / документации.

| Код                          | Описание                                                    | К какому автопоиску                       |
|------------------------------|--------------------------------------------------------------|-------------------------------------------|
| `26.60.12.119-00000983`     | Секвенатор нуклеиновых кислот ИВД, NGS                      | MDX_01                                     |
| `26.60.12.119-00000984`     | Секвенатор нуклеиновых кислот ИВД, NGS (другая разновидность) | MDX_01                                   |
| `26.60.12.119`               | Секвенатор НК ИВД (общий)                                   | MDX_01                                     |
| `26.51.53.141-00000043`     | Секвенатор НК ИВД, секвенирование по Сэнгеру (ABI 3500/3500xL) | MDX_01                                  |
| `26.51.53.141`               | Анализаторы НК (общий)                                      | MDX_01                                     |
| `26.51.53.130`               | Приборы и аппараты для физико-химического анализа           | MDX_01 *(осторожно — пересекается с хроматографией)* |
| `26.51.66.190`               | Приборы для измерений (прочие)                              | MDX_01 *(широкий)*                        |
| `32.50.13.190`               | Инструменты медицинские прочие                              | MDX_01                                     |
| `32.50.50.190`               | Изделия медицинские прочие                                  | MDX_01, MDX_02                             |
| `28.99.39.190`               | Оборудование специального назначения прочее                 | MDX_01                                     |
| `21.20.23.111`               | Реактивы и наборы реагентов диагностические in vitro        | MDX_02, MDX_03, MDX_04                     |
| `21.20.23.110`               | Реактивы для диагностики in vitro (общий)                   | MDX_02, MDX_03, MDX_04 *(может включать иммуноанализ)* |
| `21.20.23.110-00010218`     | EGFR, секвенирование НК                                     | MDX_03                                     |
| `21.20.23.110-00005091`     | KRAS, анализ НК                                             | MDX_03                                     |
| `21.20.23.110-00010217`     | NRAS, анализ НК                                             | MDX_03                                     |
| `20.59.52.195-00000703..707`| BRAF V600 анализ НК                                         | MDX_03 *(часто PCR-only — оставлять только если рядом NGS-ключи)* |
| `21.20.21.121`               | Наборы реагентов медицинского назначения                    | MDX_04 *(часто НИПТ/ПГТ/HLA)*             |
| `33.13.11.000`               | Услуги по ремонту и техническому обслуживанию               | MDX_05                                     |

**Текстовая форма** (для INCLUDE в текстовом фильтре, если КТРУ/ОКПД2 нет как отдельного фильтра в UI):

```text
26.60.12.119-00000983 26.60.12.119-00000984 26.60.12.119 26.51.53.141-00000043 26.51.53.141 21.20.23.111 21.20.23.110 21.20.21.121 21.20.23.110-00010218 21.20.23.110-00005091 21.20.23.110-00010217 20.59.52.195-00000703 20.59.52.195-00000704 20.59.52.195-00000705 20.59.52.195-00000706 20.59.52.195-00000707 32.50.13.190 32.50.50.190 28.99.39.190 33.13.11.000
```

---

## 9. Чеклист после первого прогона (через 1 неделю работы)

| № | Что проверить                                                                                                  | Действие при найденной проблеме                                          |
|---|-----------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| 1 | Не пролезают ли ПЦР-only тендеры через MDX_01-04                                                                | Добавить в EXCLUDE 7.2 конкретные модели амплификаторов (DTLite, ARIES, Streck, Gentier, БиоРад T100) |
| 2 | Не отсекает ли EXCLUDE 7.1 релевантные молекулярные лоты (особо: «гель» — для электрофореза, «контейнер» — для биообразцов) | Снять конкретный термин                                                  |
| 3 | Покрытие на дооснащении / расширении лабораторий — ловятся ли «расширение функциональности секвенатора», «дооснащение лаборатории NGS-оборудованием» | Добавить в INCLUDE: `модернизац дооснащен расширен++функциональн дополнительн++комплект` |
| 4 | Дублирование между MDX_01 (приборы) и MDX_02 (реагенты) на тендерах «прибор + первый комплект»                  | Это **нормально**. CLI дедуплицирует на уровне общего отчёта по `tender_id` |
| 5 | Сколько единиц лимита уходит на скачивание архивов                                                              | Если близко к 300/день — включить дедуп БД (`processed_tenders`) или `--active-only` фильтр |
| 6 | НИПТ автопоиск не «забит» лотами роддомов на расходники (шприцы, биксы)                                         | Добавить в EXCLUDE 7.1: `шприц медицинск++расходн родильн родильн++дом` (но **аккуратно** — могут зацепить НИПТ)|
| 7 | Все ли отечественные реагентщики покрыты — Биолабмикс, Синтол, Алкор-Био, ИнтерЛабСервис, ДНК-Технология       | Они в основном ПЦР, но если есть NGS-линейки — добавить в MDX_02         |
| 8 | Покрытие зарубежных «новых» NGS-платформ: Element AVITI24, Singular G4, Ultima UG-100, Roche Sequencing by Expansion | Уже включены в MDX_01. Проверить через 2-3 месяца — какие реально появляются в РФ-тендерах |

---

## 10. Связь с CLI `tenderland_bot`

После того как 5 (или 4) автопоисков созданы и есть их `id`:

1. Дополнить `tenderland_bot/config/autosearches.toml`:
   ```toml
   # Аналитическое оборудование (8 автопоисков из keywords_config.md)
   [[autosearch]]
   id = ...
   topic = "01_LC_LCMS_GPC_Prep"
   domain = "analytical"

   # Молекулярная диагностика (4-5 автопоисков из keywords_config_molecular_diagnostics.md)
   [[autosearch]]
   id = ...
   topic = "MDX_01_Sequencers"
   domain = "molecular_diagnostics"

   [[autosearch]]
   id = ...
   topic = "MDX_02_Reagents_Libraries"
   domain = "molecular_diagnostics"

   [[autosearch]]
   id = ...
   topic = "MDX_03_Oncology_Panels"
   domain = "molecular_diagnostics"

   [[autosearch]]
   id = ...
   topic = "MDX_04_NIPT_PGT_HLA"
   domain = "molecular_diagnostics"

   # опционально:
   # [[autosearch]]
   # id = ...
   # topic = "MDX_05_Service"
   # domain = "molecular_diagnostics"

   # новый, рекомендуется к включению:
   [[autosearch]]
   id = ...
   topic = "MDX_06_Sequencing_Services"
   domain = "molecular_diagnostics"
   ```

2. Команда `python -m tenderland_bot export-all` пройдётся по всем автопоискам всех доменов и разложит результаты:
   ```
   Z:\tenders\
   ├── 01_LC_LCMS_GPC_Prep\<DDMMYY>.{xlsx,md}
   ├── ...
   ├── MDX_01_Sequencers\<DDMMYY>.{xlsx,md}
   ├── MDX_01_Sequencers\DDMMYY\*.zip
   ├── MDX_02_Reagents_Libraries\<DDMMYY>.{xlsx,md}
   └── ...
   ```

3. Дедупликация по `tender_id` через локальную SQLite-таблицу `processed_tenders` (Этап 3 разработки) — не качаем zip-архивы для уже виденных тендеров.

4. В будущем — фильтрация по `domain` (`export-all --domain molecular_diagnostics`) для отдельной рассылки по молекулярному менеджеру.

---

## 11. Источники для верификации

- **Illumina** (iSeq, MiSeq/MiSeqDx/MiSeq i100, MiniSeq, NextSeq, NovaSeq X/X+, iScan): https://www.illumina.com/systems.html
- **MGI/DNBSEQ** (T20/T10/T7/T1/G400/G50/G99/E25): https://en.mgi-tech.com/products/
- **GeneMind** (GenoLab M, FASTASeq, SURFSeq): https://en.genemind.com/product/genolab-m
- **Oxford Nanopore** (MinION/GridION/PromethION/Flongle): https://nanoporetech.com/products
- **Thermo Fisher / Applied Biosystems** (SeqStudio, 3500/3500xL): https://www.thermofisher.com/us/en/home/life-science/sequencing/sanger-sequencing/genetic-analyzers/models/seqstudio.html
- **PacBio** (Sequel/Revio/Vega): https://www.pacb.com/sequencing-systems/
- **Element Biosciences** (AVITI/AVITI24): https://www.elementbiosciences.com/
- **Salus / Биофьюжн** (Salus Evo, Salus Pro, Р-Ген 2000): https://salus-bio.ru/
- **Хеликон / MGI** (HELICON G400/G50): https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/ngs/
- **AmoyDx NGS** (Essential, Comprehensive, HANDLE Classic, HRD/BRCA): https://www.amoydiagnostics.com/products
- **Pillar Biosciences** (ONCO/Reveal, Heredity, oncoReveal, stemSCREEN): https://www.pillar-biosciences.com/products
- **Burning Rock Dx** (OncoScreen Plus, LungPlasma, LungCore, HRR): https://www.brbiotech.com/en/Product/list-2.html
- **Novogene** (WES/WGS/targeted sequencing services + NGS reagents): https://en.novogene.com/services/
- **Parseq** (NGS панели, Prep&Seq, OncoScope): https://parseq.pro/oncology
- **OncoAtlas** (NGS diagnostics): https://oncoatlas.com/
- **Personalis** (ImmunoID NeoTYPE, NeXT Personal): https://www.personalis.com/
- **Tempus** (xT, xR, Tempus Onco): https://www.tempus.com/oncology/
- **Caris Life Sciences** (MI Profile, MI Tumor Seek): https://www.carislifesciences.com/
- **Foundation Medicine** (F1CDx, F1 Liquid, F1 Heme): https://www.foundationmedicine.com/
- **КТРУ NGS-секвенаторов**: `26.60.12.119-00000983/984`
- **КТРУ Сэнгер**: `26.51.53.141-00000043`
- **КТРУ онкомутаций**: EGFR `21.20.23.110-00010218`, KRAS `21.20.23.110-00005091`, NRAS `21.20.23.110-00010217`, BRAF V600 `20.59.52.195-00000703..707`
