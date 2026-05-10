# Молекулярная диагностика: справочник моделей, расходников и признаков для анализа ТЗ v2

Дата обновления: 2026-05-06

Назначение: справочник для второго этапа анализа закупочной документации. Таблицы ниже помогают агенту сопоставлять ТЗ с конкретными платформами, OEM-ребрендингами, типами flow cell/картриджей, наборами реагентов и числом образцов на запуск.

Главные изменения v2:

- Исправлено: `Геноскан 4000 = GenoLab M / GeneMind`, а не неопределенная SURFSeq-платформа.
- Добавлены подробные таблицы Sesana по `Геноскан 4000`: FCM/FCH, NIPT/PGT-A/WES/RNA-seq/панели/mNGS и количество образцов.
- Добавлен `Р-Ген 100`.
- Расширены MGI: `DNBSEQ-G50`, `G99`, `G400`, `T7`, `T7+`, `T1/T1+`.
- Добавлены Illumina: `MiSeq`, `MiSeqDx`, `MiSeq i100`, `MiSeq i100 Plus`, `NextSeq 550Dx`, `NextSeq 1000`, `NextSeq 2000`, `NovaSeq X`, `NovaSeq X Plus`, плюс названия reagent kits / flow cells.

## 1. Сводная таблица приборов

| Поставщик / сайт | Рыночное название | OEM / платформа | Регистрация / статус | Ключевые характеристики | Расходники / картриджи / ячейки | Термины для матчинга в ТЗ | Источник | Уверенность |
|---|---|---|---|---|---|---|---|---|
| Хеликон | HELICON G50 | MGI DNBSEQ-G50 / MGISEQ-200 | РЗН 2023/20825 | NGS DNBSEQ; 1 flow cell; FCS 100M, FCL 500M; до 10-150 Gb/run; PE150 FCL около 40 ч | DNBSEQ-G50RS sets; FCS/FCL; SE50/SE100/PE50/PE100/PE150 | `HELICON G50`, `DNBSEQ-G50`, `MGISEQ-200`, `FCS`, `FCL`, `500M`, `150 Gb`, `РЗН 2023/20825` | https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/ngs/polnogenomnyy-ngs-sekvenator-dnbseq-g50-mgiseq-200/ ; https://en.mgi-tech.com/Home/Products/instruments_info/id/6.html | Высокая |
| Хеликон | HELICON G400 | MGI DNBSEQ-G400 / MGISEQ-2000 | РЗН 2023/20825 | NGS DNBSEQ; 2 flow cells; FCS 300/550M, FCL 1500-1800M per cell; до 55-1440 Gb/run; SE50/SE100/SE400/PE100/PE150/PE200 | DNBSEQ-G400 sequencing sets; FCS/FCL | `HELICON G400`, `DNBSEQ-G400`, `MGISEQ-2000`, `FCS`, `FCL`, `1800M`, `1440 Gb`, `SE400` | https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/ngs/polnogenomnyy-ngs-sekvenator-mgi-2000/ ; https://global-mgitech.com/sequencer-products-seq-all/dnbseq-g400/ | Высокая |
| Sesana | Геноскан 3700 | FASTASeq 300 / GeneMind-семейство | Секвенатор «Геноскан» модель I, производство ООО Сесана | 1 flow cell; до 250M reads/run; до 75 Gb/run; 4 независимые дорожки; SE50, SE75, PE75, SE150, PE150; до 24 ч | Проточные ячейки линейки Геноскан/Raissol | `Геноскан 3700`, `FASTASeq 300`, `250M`, `75 Gb`, `4 дорожки`, `SE50`, `PE150` | https://sesana.ru/genoscan3700 ; https://sesana.ru/genoscan4000 | Средняя-высокая |
| Sesana | Геноскан 4000 | GenoLab M / GeneMind | РЗН 2025/24616 | 2 flow cells; FCM 250M/cell, FCH 500M/cell; 500M on FCM x2, 1000M on FCH x2; 25-150 Gb FCM run, 50-300 Gb FCH run; SE75/SE150/PE75/PE100/PE150; 12-48 ч; Q30 >=80%, accuracy >=99% | FCM/FCH flow cells; две независимые ячейки; библиотеки, совместимые с Illumina | `Геноскан 4000`, `GenoLab M`, `GeneMind`, `РЗН 2025/24616`, `FCM`, `FCH`, `250M`, `500M`, `1000M`, `Q30`, `SURF-seq` | https://sesana.ru/genoscan4000 ; https://sesana.ru/genolabm | Высокая |
| Sesana | Геноскан 5000 | SURFSeq 5000 | Секвенатор «Геноскан» модель III | 2 независимые проточные ячейки; до 7200M reads/run на 2 FCP; до 1200 Gb за 48 ч; 8 геномов человека за запуск; ручная/автоматическая загрузка библиотек; автопромывка; совместим с TruSeq/Nextera | Проточные ячейки FCP; Raissol/совместимые библиотеки | `Геноскан 5000`, `SURFSeq 5000`, `7200M`, `1200 Gb`, `48 часов`, `8 геномов`, `TruSeq`, `Nextera` | https://sesana.ru/genoscan5000 ; https://sesana.ru/surfseq | Высокая |
| Sesana | Геноскан 6000 | SURFSeq Q | Секвенатор «Геноскан» модель IV | 2 независимые flow cells; FCM 11700M, FCH 23300M reads/cell; до 14 Tb/run на FCH x2 PE150 менее 2 дней; Q40 >=90%; 8 дорожек на ячейку; индивидуальная загрузка дорожек | FCM/FCH высокопроизводительные ячейки | `Геноскан 6000`, `SURFSeq Q`, `11700M`, `23300M`, `14 Tb`, `Q40`, `8 дорожек`, `FCH x2 PE150` | https://sesana.ru/surfseqq | Высокая |
| Sesana | ГТЗ G08/G16/G24 | Капиллярный Sanger-анализатор | Страница позиционирует как генетические анализаторы с РУ | 8/16/24 капилляра; до 48 образцов/час для G24; лазер 505 nm; до 6 каналов; .fsa/.abi | Полимер POP, буферы, капиллярные массивы | `ГТЗ`, `G08`, `G16`, `G24`, `24 капилляра`, `.fsa`, `.abi`, `505 нм` | https://sesana.ru/sanger | Средняя-высокая |
| Biofusion / Р-Ген | Р-Ген 100 | Salus BioMed / младшая SBS-платформа | НИР; РУ не найдено в открытом фрагменте | 1 compact NGS; 20M/25M/60M ячейки; SE50-SE400, PE150/PE300; запуск 3.4-28 ч; index hopping <=0.0004%; Q30 80-90% | Наборы запуска/промывки; ячейки 20M, 25M, 60M | `Р-Ген 100`, `R-Gen 100`, `20M`, `25M`, `60M`, `SE400`, `PE300`, `index hopping`, `3.4 ч` | https://rgen.pro/sequencers/100/ | Высокая |
| Biofusion / Р-Ген | Р-Ген 2000 / Salus Pro / Salus Pro RS | Salus BioMed SBS platform | Salus Pro RS проходил испытания в РФ; номер РУ в открытом фрагменте не найден | 2 независимые ячейки; 80-500M reads/cell, исполнение 1000M; до 300 Gb/run, опция 600 Gb; SE75-PE300; 8-44 ч для PE150; совместимость с библиотеками Illumina/NextSeq 550 workflow | Salus kits SRM/PRM: SE75, PE100, PE150, PE300 на 80M/150M/300M/500M/1000M | `Р-Ген 2000`, `Salus Pro`, `Salus Pro RS`, `SRM-SE75`, `PRM-PE150`, `1000M`, `NextSeq 550`, `PE300` | https://rgen.pro/sequencers/2000/ ; https://salus-bio.ru/sequencers/saluspro/ | Высокая |
| Biofusion / Salus | Salus Evo | Salus BioMed high-throughput SBS | РУ не найдено в открытом фрагменте | 2 независимые ячейки; 1500M/2500M reads/cell; до 1.5 Tb/run; SE50-PE150; 8-32 ч; Q30 85-90% | Salus Evo 1500M/2500M sequencing reagent sets | `Salus Evo`, `1500M`, `2500M`, `1.5 Tb`, `SE50`, `PE150`, `Q30`, `две независимые ячейки` | https://salus-bio.ru/sequencers/salusevo/ | Высокая |
| MGI | DNBSEQ-G50 | MGI DNBSEQ | RUO / CE-IVD зависит от рынка | Benchtop; FCS 100M/FCL 500M; 10-150 Gb/run; SE50/SE100/PE50/PE100/PE150; PE150 FCL около 40 ч | DNBSEQ-G50RS sets; FCS/FCL | `DNBSEQ-G50`, `G50`, `FCS`, `FCL`, `100M`, `500M`, `SE50-FCL`, `PE150-FCL`, `940-002456-00` | https://en.mgi-tech.com/Home/Products/instruments_info/id/6.html ; https://en.mgi-tech.com/products/reagents_info/24/ | Высокая |
| MGI | DNBSEQ-G99 | MGI DNBSEQ / StandardMPS 2.0 | CE-IVD / RUO зависит от рынка | Dual flow cell; FCS 40M, FCL 80M, FCU 200M reads/cell; up to 200M reads/run; 8-240 Gb/run; PE150 около 11-12 ч; SE100/PE50/PE150/PE300/SE400/App-D | FCS/FCL/FCU sequencing sets | `DNBSEQ-G99`, `G99`, `FCS`, `FCL`, `FCU`, `40M`, `80M`, `200M`, `PE150 12 h`, `Q40` | https://global-mgitech.com/sequencer-products-seq-all/dnbseq-g99/ ; https://mgi-tech.eu/sequencing-products/dnbseq-g99 | Высокая |
| MGI | DNBSEQ-G400 | MGI DNBSEQ / StandardMPS 2.0 | RUO / CE-IVD зависит от рынка | 2 flow cells; FCS 2 lanes 300/550M reads/cell; FCL 4 lanes 1500-1800M reads/cell; до 55-1440 Gb/run; SE50/SE100/SE400/PE100/PE150/PE200 | FCS/FCL sequencing sets | `DNBSEQ-G400`, `G400`, `FCS`, `FCL`, `550M`, `1800M`, `SE400`, `PE200`, `1440 Gb` | https://global-mgitech.com/sequencer-products-seq-all/dnbseq-g400/ | Высокая |
| MGI | DNBSEQ-T7 | MGI DNBSEQ ultra-high throughput | T7 HotMPS discontinued on MGI page; T7RS recommended | 4 flow cells/run; up to 24B reads/run; up to 6 Tb/day on EU page; HotMPS page: 1-4 Tb/day; PE100/PE150/App-A; up to 60 human WGS/day | T7RS / high-throughput sequencing sets | `DNBSEQ-T7`, `T7`, `T7RS`, `24 billion reads`, `60 genomes/day`, `PE150`, `4 flow cells` | https://mgi-tech.eu/sequencing-products/dnbseq-t7 ; https://en.mgi-tech.com/products/instruments_info/22/ | Высокая |
| MGI | DNBSEQ-T7+ | Complete Genomics / MGI T7+ | RUO | Higher-throughput T7-series; use as alias for newest T7+ references; exact reagent/cat-number matching should use product page/brochure | T7+ flow cell/reagent sets | `DNBSEQ-T7+`, `T7+`, `T7 Plus`, `Complete Genomics`, `ultra-high throughput` | https://www.completegenomics.com/products/sequencing-platforms/dnbseq-t7-plus/ | Средняя-высокая |
| MGI | DNBSEQ-T1 / T1+ | MGI DNBSEQ T-level benchtop | RUO | 2 flow cells; FCL 4 lanes 2000M reads/cell; FCM 2 lanes 1000M; FCS 2 lanes 500M; до 1.2 Tb/run за ~24 ч на FCL PE150; Q30 >93%, Q40 >90%; integrated DNB Make & Load | DNBSEQ-T1+RS sets: FCL PE150, FCL SE100, FCS PE150, FCS SE100; cat. examples 940-003007-00, 940-003008-00, 940-003023-00, 940-003024-00 | `DNBSEQ-T1`, `DNBSEQ-T1+`, `T1+`, `FCL PE150`, `1.2 Tb`, `600 Gb per flow cell`, `DNB Make`, `940-003007-00` | https://en.mgi-tech.com/Home/Products/instruments_info/id/73.html ; https://www.completegenomics.com/products/sequencing-platforms/dnbseq-t1-plus/ | Высокая |
| Illumina | MiSeq / MiSeq 2 / MiSeq v2/v3 | Illumina SBS | RUO; MiSeqDx отдельно IVD | 1 flow cell; Nano v2 1M single reads/0.3-0.5 Gb; Micro v2 4M/1.2 Gb; v2 12-15M/до 8.5 Gb; v3 22-25M/до 15 Gb; read lengths до 2x300 | MiSeq Reagent Nano Kit v2; MiSeq Reagent Micro Kit v2; MiSeq Reagent Kit v2; MiSeq Reagent Kit v3; prefilled cartridge + flow cell + PR2 | `MiSeq`, `MiSeq 2`, `MiSeq v2`, `MiSeq v3`, `Nano Kit v2`, `Micro Kit v2`, `MS-102-3003`, `2x300`, `15 Gb` | https://www.illumina.com/systems/sequencing-platforms/miseq/specifications.html ; https://support.illumina.com/sequencing/sequencing_instruments/miseq/kit_contents.html | Высокая |
| Illumina | MiSeqDx | Illumina MiSeqDx | IVD; FDA/CE-marked on Illumina page | Diagnostic/research modes; MiSeqDx Reagent Kit v3: 2x150 bp, >15M reads PF, >5 Gb, >=80% bases Q30; MiSeqDx Reagent Kit v3 Micro for lower throughput Dx mode | MiSeqDx Reagent Kit v3, cat. 20037124; MiSeqDx Reagent Kit v3 Micro | `MiSeqDx`, `MiSeq Dx`, `MiSeqDx Reagent Kit v3`, `20037124`, `2x150`, `>15 million reads`, `IVD` | https://www.illumina.com/products/by-type/ivd-products/miseqdx-reagents.html | Высокая |
| Illumina | MiSeq i100 | Illumina XLEAP-SBS | RUO | 5M/25M flow cells; 1.5-15 Gb typical; 5M/25M single reads; paired reads 10M/50M; max 2x500 on 25M; run time about 4-24 h; index-first, room-temp reagents | MiSeq i100 Series 5M/25M Reagent Kits; dry cartridge + wet cartridge + RSB + KLD | `MiSeq i100`, `5M Reagent Kit`, `25M Reagent Kit`, `Dry Cartridge`, `Wet Cartridge`, `KLD`, `RSB`, `2x500` | https://www.illumina.com/systems/sequencing-platforms/miseq-i100/specifications.html ; https://knowledge.illumina.com/instrumentation/miseq-i100-series/instrumentation-miseq-i100-series-reference_material-list/000009216 | Высокая |
| Illumina | MiSeq i100 Plus | Illumina XLEAP-SBS | RUO | Adds 50M/100M flow cells; output up to 30 Gb at 2x150 on 100M; 100M flow cell gives 100M single/200M paired reads; 50M/100M only for Plus | MiSeq i100 Plus 50M and 100M Reagent Kits; dry/wet cartridges; 100/300/600/1000 cycle depending kit | `MiSeq i100 Plus`, `50M`, `100M`, `100M Reagent Kit`, `200M paired-end reads`, `Dry Cartridge`, `Wet Cartridge` | https://www.illumina.com/systems/sequencing-platforms/miseq-i100/specifications.html | Высокая |
| Illumina | NextSeq 550Dx | Illumina NextSeq 550Dx | IVD / RUO modes | Mid/high output NextSeq Dx platform; use for service/installed base search; reagent names often `NextSeq 550Dx High Output Reagent Kit`, `Mid Output Reagent Kit` | NextSeq 550Dx High Output / Mid Output reagent kits, flow cell + cartridge | `NextSeq 550Dx`, `NextSeq550Dx`, `High Output Reagent Kit`, `Mid Output Reagent Kit`, `Dx Mode` | https://www.illumina.com/systems/sequencing-platforms/nextseq-550dx.html | Средняя-высокая |
| Illumina | NextSeq 1000 | Illumina XLEAP-SBS | RUO | Compatible with P1/P2; P1 100M single reads, P2 400M; output 10-120 Gb depending read length/flow cell; P1/P2 reagent kits include cartridge, flow cell, RSB with Tween 20 | NextSeq 1000/2000 P1 Reagents Kit; P2 Reagents Kit | `NextSeq 1000`, `P1 Reagents`, `P2 Reagents`, `100M`, `400M`, `cartridge`, `flow cell`, `RSB with Tween` | https://support.illumina.com/sequencing/sequencing_instruments/nextseq-1000-2000/reagent-kits.html ; https://www.illumina.com/systems/sequencing-platforms/nextseq-1000-2000/specifications.html | Высокая |
| Illumina | NextSeq 2000 | Illumina XLEAP-SBS | RUO | Compatible with P1/P2/P3/P4; P1 100M, P2 400M, P3 1.2B, P4 1.8B single reads; output 10-540 Gb depending read length; P3/P4 for NextSeq 2000 only | P1/P2/P3/P4 reagent kits; P1 100/300/600 cycles, P2 100/200/300/600, P3 50/100/200/300, P4 flow cell on newer spec pages | `NextSeq 2000`, `P3 Reagents`, `P4 Reagents`, `1.2B`, `1.8B`, `540 Gb`, `XLEAP-SBS` | https://www.illumina.com/systems/sequencing-platforms/nextseq-1000-2000/specifications.html ; https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/nextseq-1000-2000-reagents.html | Высокая |
| Illumina | NovaSeq X | Illumina XLEAP-SBS high-throughput | RUO | Single flow cell system; flow cells 1.5B/10B/25B; 2x150 output about 500-716 Gb, 3-4 Tb, 8-10.5 Tb per flow cell | NovaSeq X Series 1.5B, 10B, 25B Reagent Kits; 100/200/300 cycle; cartridge lyo insert, library tube strip, patterned single-lane flow cell, pre-load buffer, buffer cartridge | `NovaSeq X`, `1.5B Reagent Kit`, `10B Reagent Kit`, `25B Reagent Kit`, `lyo insert`, `pre-load buffer`, `single-lane flow cell` | https://www.illumina.com/systems/sequencing-platforms/novaseq-x-plus/specifications.html ; https://support.illumina.com/sequencing/sequencing_instruments/novaseq-x-novaseq-x-plus/reagent-kits.html | Высокая |
| Illumina | NovaSeq X Plus | Illumina XLEAP-SBS high-throughput | RUO | Dual flow cell capable; delivers twice the per-flow-cell output of NovaSeq X; up to about 16-21 Tb at 25B x2 2x150 depending spec range | Same NovaSeq X Series 1.5B/10B/25B Reagent Kits | `NovaSeq X Plus`, `dual flow cell`, `25B x2`, `20 Tb`, `NovaSeq X Series Reagent Kit` | https://www.illumina.com/systems/sequencing-platforms/novaseq-x-plus/specifications.html | Высокая |

## 2. Sesana: Геноскан 4000 детальная матрица образцов

Источник: https://sesana.ru/genoscan4000

| Тип исследования | Длина чтения | Требование на образец | FCM x1 250M | FCM x2 или FCH x1 500M | FCM x1 + FCH x1 750M | FCH x2 1000M | Термины для ТЗ |
|---|---|---|---:|---:|---:|---:|---|
| NIPT стандарт | SE75 | >7M reads/sample | 32 | 64 | 96 | 128 | `NIPT`, `НИПТ`, `SE75`, `7 млн ридов`, `128 образцов` |
| PGT-A | SE75 | >5M reads/sample | 48 | 96 | 144 | 192 | `PGT-A`, `ПГТ-А`, `5 млн ридов`, `192 образца` |
| WES | PE150 | 7 Gb/sample; WES >200x, panel 40 Mb | 10 | 20 | 30 | 40 | `WES`, `полный экзом`, `PE150`, `7 Гб`, `40 образцов` |
| RNA-seq | SE50 | >10M reads/sample | 24 | 48 | 72 | 96 | `RNA-seq`, `SE50`, `10 млн ридов` |
| Панельное секвенирование | SE75 | 5 Gb/sample; >95% target at >200x, panel 2 Mb | 12 | 24 | 36 | 48 | `панельное секвенирование`, `5 Гб`, `2 Мб`, `200x` |
| mNGS | SE75 | >20M reads/sample | 12 | 24 | 36 | 48 | `mNGS`, `метагеном`, `20 млн ридов` |

## 3. Sesana: Геноскан 4000 flow cell / режимы

| Прибор | Кол-во ячеек | Тип ячейки | Дорожки | Reads/cell | Режимы | Output/cell | Q30 | Время |
|---|---:|---|---:|---:|---|---|---|---|
| Геноскан 4000 | 2 | FCM | 2 | 250M | SE75, SE150, PE75, PE100, PE150 | 18-20 Gb, 35-40 Gb, 35-40 Gb, 45-50 Gb, 70-75 Gb | 85% | 12-48 ч |
| Геноскан 4000 | 2 | FCH | 2 | 500M | SE75, SE150, PE75, PE100, PE150 | 35-40 Gb, 70-80 Gb, 70-80 Gb, 90-100 Gb, 140-150 Gb | 85% | 12-48 ч |

## 4. Biofusion / Р-Ген: ячейки и тесты

### Р-Ген 100

Источник: https://rgen.pro/sequencers/100/

| Тип ячейки | Длина чтения | Выход | Длительность | Q30 | Термины для ТЗ |
|---|---|---|---|---|---|
| 20M | SE400 | 8 Gb | 20 ч | >=80% | `20M`, `SE400`, `8 Гб`, `Р-Ген 100` |
| 20M | PE300 | 12 Gb | 28 ч | >=80% | `20M`, `PE300`, `12 Гб` |
| 25M | SE50 | 1.25 Gb | 3.4 ч | >=90% | `25M`, `SE50`, `1.25 Гб`, `3.4 ч` |
| 25M | SE75 | 1.875 Gb | 4.1 ч | >=90% | `25M`, `SE75`, `1.875 Гб` |
| 25M | SE100 | 2.5 Gb | 4.7 ч | >=85% | `25M`, `SE100`, `2.5 Гб` |
| 25M | PE150 | 7.5 Gb | 10.9 ч | >=85% | `25M`, `PE150`, `7.5 Гб` |
| 60M | SE50 | 3 Gb | 3.8 ч | >=90% | `60M`, `SE50`, `3 Гб` |
| 60M | SE75 | 4.5 Gb | 4.6 ч | >=90% | `60M`, `SE75`, `4.5 Гб` |
| 60M | SE100 | 6 Gb | 5.4 ч | >=85% | `60M`, `SE100`, `6 Гб` |
| 60M | PE150 | 18 Gb | 12 ч | >=85% | `60M`, `PE150`, `18 Гб` |

| Исследование | Требование | 20M | 25M | 60M |
|---|---|---:|---:|---:|
| NIPT | 5M reads | - | 5 | 12 |
| Малая панель | 1 Gb | - | 7 | 18 |
| Средняя панель | 3-5 Gb | - | 1-2 | 3-6 |
| 16S | 0.5M reads | 40 | - | - |
| Малые геномы | 1 Gb | - | 7 | 18 |
| Онкологический скрининг | 4 Gb | - | 2 | 4 |

### Р-Ген 2000 / Salus Pro

Источник: https://rgen.pro/sequencers/2000/

| Группа наборов | Каталожные паттерны | Емкости | Режимы | Термины для ТЗ |
|---|---|---|---|---|
| SRM-SE75 | `SRM-SE75-80M`, `150M`, `300M`, `500M`, `1000M` | 80M-1000M | SE75 | `SRM-SE75-500M`, `SRM-SE75-1000M` |
| PRM-PE100 | `PRM-PE100-80M`, `150M`, `300M`, `500M`, `1000M` | 80M-1000M | PE100 | `PRM-PE100-1000M` |
| PRM-PE150 | `PRM-PE150-80M`, `150M`, `300M`, `500M`, `1000M` | 80M-1000M | PE150 | `PRM-PE150-500M` |
| PRM-PE300 | `PRM-PE300-80M`, `150M`, `300M` | 80M-300M | PE300 | `PRM-PE300-300M` |

## 5. MGI / DNBSEQ: flow cell и reagent-set признаки

| Платформа | Типы ячеек | Reads/cell | Режимы | Output / run | Картриджи / reagent names | Термины для ТЗ |
|---|---|---|---|---|---|---|
| DNBSEQ-G50 | FCS, FCL | FCS 100M; FCL 500M | FCS: SE100/PE100/PE150; FCL: SE50/PE50/SE100/PE100/PE150 | 10-150 Gb | `DNBSEQ-G50RS High-throughput Sequencing Set`; FCL SE50/SE100/PE50/PE100/PE150; FCS SE100/PE100/PE150 | `G50RS`, `FCS`, `FCL`, `500M`, `SE50-FCL`, `PE150-FCL` |
| DNBSEQ-G99 | FCS, FCL, FCU | 40M, 80M, 200M | PE50, SE100, PE150, PE300, SE400, App-D | 8-240 Gb | `DNBSEQ-G99RS High-throughput Sequencing Set`; StandardMPS 2.0 | `G99`, `FCU`, `Q40`, `PE150 12h`, `SE400`, `App-D` |
| DNBSEQ-G400 | FCS, FCL | FCS 300/550M; FCL 1500-1800M | SE50/SE100/SE400/PE100/PE150/PE200 | 55-1440 Gb | `DNBSEQ-G400RS sequencing set`; FCS/FCL | `G400`, `FCL`, `1800M`, `SE400`, `PE200`, `1440 Gb` |
| DNBSEQ-T7 / T7RS | 4 flow cells | up to 5000M/cell on older T7 info; up to 24B reads/run | PE100, PE150, App-A | up to 6 Tb/day; up to 60 WGS/day | T7RS high-throughput sequencing sets | `T7`, `T7RS`, `24 billion reads`, `60 genomes`, `4 flow cells` |
| DNBSEQ-T1+ | FCS, FCM, FCL | 500M, 1000M, 2000M | SE50/SE100/PE150/PE300 depending cell | up to 1.2 Tb/run on FCL PE150 x2 | `DNBSEQ-T1+RS High-throughput Sequencing Reagent Set (FCL PE150) 940-003007-00`; `FCL SE100 940-003008-00`; `FCS PE150 940-003023-00`; `FCS SE100 940-003024-00` | `T1+`, `FCL PE150`, `940-003007-00`, `DNB Make`, `Q40 >90%`, `1.2 Tb` |

## 6. Illumina: приборы и картриджи/flow cell

| Платформа | Flow cell / kit names | Reads / output | Cycles / read lengths | Компоненты набора | Термины для ТЗ |
|---|---|---|---|---|---|
| MiSeq | `MiSeq Reagent Nano Kit v2`, `MiSeq Reagent Micro Kit v2`, `MiSeq Reagent Kit v2`, `MiSeq Reagent Kit v3` | Nano v2: 1M single / 2M paired, 300-500 Mb; Micro v2: 4M / 8M, 1.2 Gb; v2: 12-15M / 24-30M, max 8.5 Gb; v3: 22-25M / 44-50M, max 15 Gb | v2 50/300/500 cycles; v3 150/600 cycles; up to 2x300 | Prefilled reagent cartridge, flow cell, PR2, HT1 | `MiSeq Reagent Kit v2`, `MiSeq Reagent Kit v3`, `Nano`, `Micro`, `MS-102-3003`, `600-cycle`, `PR2`, `HT1` |
| MiSeqDx | `MiSeqDx Reagent Kit v3`; `MiSeqDx Reagent Kit v3 Micro` | v3: >15M reads PF, >5 Gb | 2x150 | Flow cell + prefilled cartridge; IVD kit | `MiSeqDx`, `20037124`, `MiSeqDx Reagent Kit v3`, `MiSeqDx v3 Micro`, `IVD`, `2x150` |
| MiSeq i100 | `MiSeq i100 Series 5M Reagent Kit`; `25M Reagent Kit` | 5M: 5M single / 10M paired; 25M: 25M / 50M paired; output 1.5-25 Gb depending read length | 100/300/600/1000 cycles depending kit; 2x150, 2x300, 2x500 on 25M | Dry Cartridge: flow cell + lyophilized reagents; Wet Cartridge/Backpack; RSB; KLD | `MiSeq i100`, `5M`, `25M`, `Dry Cartridge`, `Wet Cartridge`, `Backpack`, `KLD`, `2x500` |
| MiSeq i100 Plus | `MiSeq i100 Plus 50M Reagent Kit`; `100M Reagent Kit` | 50M: 50M single / 100M paired; 100M: 100M / 200M paired; output up to 30 Gb at 2x150 | 100/300/600/1000 cycles depending kit | Same dry/wet cartridge architecture | `MiSeq i100 Plus`, `50M`, `100M`, `200M paired-end reads`, `100M Dry Cartridge` |
| NextSeq 550Dx | `NextSeq 550Dx High Output Reagent Kit`; `Mid Output Reagent Kit` | installed-base Dx/RUO platform; match service/reagent requests by exact kit names | Dx/RUO modes | Flow cell + cartridge | `NextSeq 550Dx`, `High Output Reagent Kit`, `Mid Output Reagent Kit`, `Dx Mode` |
| NextSeq 1000 | `NextSeq 1000/2000 P1 Reagents Kit`; `P2 Reagents Kit` | P1 100M single / 200M paired; P2 400M / 800M; output 10-120 Gb on P1/P2 common modes | P1 100/300/600 cycles; P2 100/200/300/600 cycles | cartridge, flow cell, RSB with Tween 20 | `NextSeq 1000`, `P1 Reagents`, `P2 Reagents`, `RSB with Tween 20`, `100M`, `400M` |
| NextSeq 2000 | P1/P2/P3/P4 reagent kits | P3 1.2B single / 2.4B paired; P4 1.8B / 3.6B paired; output up to 540 Gb on P4 2x150 | P3 50/100/200/300 cycles; P4 per XLEAP support/specs | cartridge, flow cell, RSB with Tween 20 | `NextSeq 2000`, `P3 Reagents`, `P4 Reagents`, `1.2B`, `1.8B`, `540 Gb`, `XLEAP-SBS` |
| NovaSeq X | `NovaSeq X Series 1.5B Reagent Kit`; `10B`; `25B` | per flow cell 2x150: 1.5B about 500-716 Gb; 10B about 3-4 Tb; 25B about 8-10.5 Tb | 100/200/300 cycle kits | reagent cartridge, lyo insert, library tube strip, patterned single-lane flow cell, pre-load buffer, buffer cartridge | `NovaSeq X`, `1.5B`, `10B`, `25B`, `lyo insert`, `library tube strip`, `single-lane flow cell` |
| NovaSeq X Plus | same `NovaSeq X Series` kits | dual flow cell capable, twice per-flow-cell output | 100/200/300 cycle kits | same | `NovaSeq X Plus`, `dual flow cell`, `25B x2`, `NovaSeq X Series Reagent Kit` |

## 7. Панели и библиотеки, уже привязанные к поставщикам РФ

| Поставщик | Название | Платформа | Регистрация / статус | Гены / назначение | Термины для ТЗ | Источник |
|---|---|---|---|---|---|---|
| Хеликон / ОнкоАтлас | HELICON ABC Плюс C-А / C-Б | HELICON G50/G400 | РЗН 2024/22811 | BRCA1, BRCA2, ATM, CHEK2, PALB2, PIK3CA; FFPE, плазма, цельная кровь; 48 образцов | `HELICON ABC Плюс`, `BRCA1`, `BRCA2`, `ATM`, `CHEK2`, `PALB2`, `PIK3CA`, `48 образцов`, `РЗН 2024/22811` | https://shop.helicon.ru/catalog/reagents/reagents-and-kits/sequencing-kits/ngs-kits/helicon-abc-plyus-s/ |
| Хеликон / ОнкоАтлас | HELICON Атлас Плюс Солид C-А / C-Б | HELICON G50/G400 | РЗН 2024/22803 | BRAF, EGFR, ERBB2/HER2, IDH1/2, KIT, TP53, KRAS, NRAS, HRAS, ALK, PDGFRA, PIK3CA, MET; MSI | `HELICON Атлас Плюс`, `MSI`, `EGFR`, `KRAS`, `NRAS`, `BRAF`, `ALK`, `MET`, `PIK3CA`, `РЗН 2024/22803` | https://helicon.ru/brands/onkoatlas/ |
| Sesana / Raissol | Raissol SG GM / SG GM Plus / SG GM Ampli | Illumina + GeneMind compatible | RU не найдено | WGS libraries, amplicon libraries 70-600 bp, up to 192 UDI, 96 samples | `Raissol SG GM`, `SG GM Plus`, `SG GM Ampli`, `96 образцов`, `192 индекса`, `Illumina`, `GeneMind` | https://sesana.ru/raissol |

## 8. OEM / ребрендинг для агента

| Рыночное название | OEM / исходная платформа | Уверенность | Комментарий |
|---|---|---|---|
| HELICON G50 | MGI DNBSEQ-G50 / MGISEQ-200 | Высокая | Хеликон указывает Wuhan MGI Tech и РУ HELICON G50/G400. |
| HELICON G400 | MGI DNBSEQ-G400 / MGISEQ-2000 | Высокая | Хеликон указывает Wuhan MGI Tech и РУ HELICON G50/G400. |
| Геноскан 3700 | FASTASeq 300 / GeneMind | Средняя-высокая | Страница Sesana `genoscan3700`, прежняя `fastaseq300`; приоритетно матчить по 250M/75Gb/4 lanes. |
| Геноскан 4000 | GenoLab M / GeneMind | Высокая | Прямо подтверждено страницей Sesana и внешними карточками. |
| Геноскан 5000 | SURFSeq 5000 | Высокая | Прямо фигурирует на странице Sesana. |
| Геноскан 6000 | SURFSeq Q | Высокая | Прямо фигурирует на странице Sesana. |
| Р-Ген 100 | Salus/Biofusion compact SBS | Высокая по продукту, средняя по OEM | Матчить по 20M/25M/60M, SE400/PE300, index hopping <=0.0004%. |
| Р-Ген 2000 | Salus Pro / Salus Pro RS | Высокая | Страница Р-Ген прямо упоминает Salus Pro. |
| Salus Evo | Salus BioMed high-throughput | Высокая | Матчить по 1500M/2500M и до 1.5Tb. |

## 9. Инструкции для агента анализа ТЗ

1. Сначала ищи прямые совпадения: модель, РУ, каталожный номер, reagent kit name.
2. Если прямого совпадения нет, матчь по триаде `тип ячейки + reads/output + read length`.
3. Для Sesana/Genoscan 4000 сильные признаки: `GenoLab M`, `FCM/FCH`, `250M/500M`, `NIPT 32/64/96/128`, `PGT-A 48/96/144/192`.
4. Для Р-Ген 100 сильные признаки: `20M/25M/60M`, `SE400`, `PE300`, `index hopping <=0.0004%`, `NIPT 5/12 samples`.
5. Для Р-Ген 2000 сильные признаки: `SRM-SE75-*`, `PRM-PE*`, `80M/150M/300M/500M/1000M`, `совместим с библиотеками Illumina`, `NextSeq 550 workflow`.
6. Для MGI сильные признаки: `DNB`, `DNBSEQ`, `cPAS`, `DNA nanoball`, `FCS/FCL/FCU`, `DNB Make`, `StandardMPS 2.0`.
7. Для Illumina сильные признаки: `P1/P2/P3/P4`, `1.5B/10B/25B`, `MiSeq Reagent Kit v2/v3`, `Dry Cartridge`, `Wet Cartridge`, `lyo insert`, `pre-load buffer`.
8. Не классифицировать как ПЦР-only, если в ТЗ есть `SBS`, `flow cell`, `sequencing cartridge`, `library prep`, `DNBSEQ`, `MiSeq/NextSeq/NovaSeq`.
