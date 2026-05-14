# Tenderland — автопоиски по капиллярному электрофорезу, центрифугам и роботизации

**Дата подготовки:** 2026-05-14
**Версия:** 1.0
**Цель:** покрыть отдельный кластер тендеров на капиллярный электрофорез (НЕ для Sanger-секвенирования), лабораторные центрифуги и системы автоматизации/роботизации жидкостных операций.

> Парные файлы:
> - `keywords_config.md` — инструментальная аналитика (8 поисков)
> - `keywords_config_molecular_diagnostics.md` — молекулярная диагностика и секвенирование (4-5 поисков)
> - `keywords_config_general_lab.md` — общелабораторное (5-6 поисков)
>
> Капиллярный электрофорез *для секвенирования* (ABI 3500/3500xL, SeqStudio) — в `keywords_config_molecular_diagnostics.md` (MDX_01). Здесь — **CE для фармы, биохимии, фрагментного анализа белков**.
>
> Магнитные пробоподготовительные станции (KingFisher, MGISP, QIAcube) — в `keywords_config_molecular_diagnostics.md` (MDX_02), а **универсальные liquid-handling роботы** (Tecan, Hamilton, Beckman Biomek, Opentrons, Eppendorf epMotion, Andrew) — здесь.

---

## 1. Карта автопоисков

| №  | Имя автопоиска                | Что ищем                                                                                       |
|----|-------------------------------|------------------------------------------------------------------------------------------------|
| 01 | `CER_01_Capillary_Electrophoresis` | Капиллярный электрофорез **НЕ для секвенирования**: PA800/P-ACE/BioPhase, Agilent 7100 CE, Bio-Rad, Lumex Капель — фарма / биохимия / контроль чистоты пептидов |
| 02 | `CER_02_Centrifuges`         | Лабораторные центрифуги (настольные, низко-/среднескоростные, рефрижераторные, ультрацентрифуги, минифуги, для микропробирок) |
| 03 | `CER_03_Liquid_Handling_Robotics` | Системы автоматизации жидкостных операций — Tecan Freedom EVO / Fluent, Hamilton STAR / Vantage, Beckman Biomek, Eppendorf epMotion, Opentrons, Agilent Bravo |

---

## 2. Скоуп — что включено / что нет

| Категория                                       | Решение | Комментарий                                                                              |
|-------------------------------------------------|---------|------------------------------------------------------------------------------------------|
| Капиллярный электрофорез (CE) для фарма/биохим/протеомика | ✅      | Beckman Coulter PA800, Sciex BioPhase 8800, Agilent 7100 CE, Lumex Капель                |
| CGE (capillary gel electrophoresis)             | ✅      | Для контроля чистоты белков, антител, ДНК-фрагментов (НЕ Sanger)                          |
| CZE/MEKC/CIEF/cIEF                              | ✅      | Зонный электрофорез, мицеллярная электрокинетическая хроматография, изоэлектрофокусирование |
| Капиллярный CE-MS                               | ✅      | CE c МС-детекцией — редкий, но включаем                                                   |
| Капиллярный электрофорез для Sanger-секвенирования (ABI 3500/3500xL/SeqStudio) | ❌      | В `keywords_config_molecular_diagnostics.md` MDX_01                                       |
| Лабораторные центрифуги (все классы)            | ✅      | Eppendorf, Hettich, Sigma, Thermo Sorvall, Beckman Avanti/Optima, Hermle, Kubota, Heraeus, Liston, ОПН |
| Минифуги, мини-центрифуги, плашечные центрифуги | ✅      |                                                                                            |
| Ультрацентрифуги                                | ✅      | Beckman Optima, Sorvall WX/MX, Hitachi CP                                                  |
| Промышленные / производственные центрифуги     | ❌      | EXCLUDE — другой класс (декантеры, сепараторы для нефтехимии, молочки, фарм-производства) |
| Медицинские центрифуги для крови                | ⚠️      | Полу-исключены — на стыке мед.-лабораторного. См. EXCLUDE 7.3                              |
| Liquid handling robots (универсальные)          | ✅      | Tecan, Hamilton, Beckman Biomek, Eppendorf epMotion, Opentrons, Andrew, Agilent Bravo     |
| Echo acoustic dispensers                        | ✅      | Beckman Echo 525/650 — для compound dispensing                                            |
| Cherry Biotech, Formulatrix Mantis              | ✅      | Малообъёмные dispensers                                                                    |
| Magnetic bead extraction stations (KingFisher, QIAcube, MGISP) | ❌ | В MDX_02 (molecular_diagnostics)                                                          |
| Робоманипуляторы общего назначения (KUKA, ABB)  | ❌      | Не лабораторные, через EXCLUDE                                                            |
| Колонии-пикеры                                  | ⚪      | Опционально — на стыке роботизации и микробиологии (Hudson Robotics, Molecular Devices QPix)|

---

## 3. Алгоритм настройки в Tenderland UI

Те же 6 шагов, что в `keywords_config.md` (раздел 2). Повторить **3 раза**.

---

## 4. Глобальные параметры

См. `keywords_config.md` раздел 3 — единый стандарт.

---

## 5. Синтаксис ключевых слов

См. `keywords_config.md` раздел 4 (`пробел`=OR, `++`=AND-стемминг, `+`=точная фраза, `=`=точное совпадение).

---

## 6. INCLUDE-строки

> Каждая строка ниже — **одной строкой** для копи-пэйст.

### 6.1. `CER_01_Capillary_Electrophoresis` — капиллярный электрофорез (НЕ Sanger)

```text
капиллярн++электрофорез электрофорез++капиллярн система++капиллярн++электрофорез прибор++капиллярн++электрофорез капиллярн-электрофоретическ электрофоретическ++капиллярн capillary++electrophoresis =CE-system =CE-MS capillary++electrophoresis-mass++spectrometry CE++MS капиллярн++электрофорез++масс-спектр капиллярн++электрофорез++УФ капиллярн++электрофорез++детектор зонн++электрофорез капиллярн++зонн++электрофорез =CZE =MEKC мицеллярн++электрокинетическ++хроматограф мицеллярн++электрокинетическ капиллярн++изоэлектрофокусирован =CIEF изоэлектрофокусирован capillary++gel++electrophoresis =CGE capillary++isoelectric++focusing =cIEF imaged++capillary++isoelectric++focusing =icIEF капиллярн++изотахофорез =CITP =ITP капиллярн++изотахофорез капиллярн++гель++электрофорез гель-электрофорез контроль++чистот++пептид контроль++чистот++белок размер++пептид размер++белок фрагментн++анализ++белк glycoanalysis гликаны N-гликаны O-гликаны гликопрофилирован charge++heterogeneity charge++variant++analysis IEF-CE Quant-iT++Capillary capillary++sieving++electrophoresis CSE capillary++electrochromatography Beckman++Coulter Бекман-Каултер Beckman++Coulter++CE PA800 =PA+800 PA++800 =PA800+plus PA800++plus PA800++System PA800++Pharmaceutical PA++800 P/ACE++MDQ P/ACE++MDQ+Plus P/ACE++System P/ACE++MDQ++plus++pharmaceutical ProteomeLab++PA+800 ProteomeLab++PF+2D Sciex Сайекс Скаекс =SCIEX SCIEX++BioPhase BioPhase++8800 SCIEX++PA+800 SCIEX++PA+800+Plus SCIEX++CE BioPhase++System Agilent Аджилент =Agilent +Agilent+7100+CE Agilent++7100++CE Agilent++G1600 G7100A 3DCE 3D-CE HPCE Bio-Rad Биорад Био-Рад =Bio-Rad BioFocus BioFocus++3000 BioFocus++2000 BioFocus++3000++CE Lumex Люмекс =Lumex Капель Капель-105 Капель-105М Капель-105М/Т Капель-204 Капель-205 Капель-205-2 Капель-104 Капель-104Т Капель-104М ВЭГА ВЭГА-1М ВЭГА-2М =VEGA Mol++Devices SpectraMax++Capillary CESI++8000 CESI8000 CESI-8000 SCIEX++CESI Beckman++ProteomeLab PostNova =PostNova PostNova++Sciex Lumex++Капель Lumex++Kapel Albagen +Иос +ИЭФ-1 +ИЭФ-1-2 капель-105
```

### 6.2. `CER_02_Centrifuges` — лабораторные центрифуги

```text
центрифуг центрифуг++лабораторн лабораторн++центрифуг центрифуг++настольн настольн++центрифуг минифуга мини-центрифуг мини++центрифуг центрифуг++для++микропробирок центрифуг++планшетн микропланшетн++центрифуг лабораторн++центрифуг++рефрижератор рефрижераторн++центрифуг охлажда++центрифуг центрифуг++охлажда центрифуг++высокоскоростн центрифуг++универсальн универсальн++центрифуг низкоскоростн++центрифуг среднескоростн++центрифуг ультрацентрифуг ультра-центрифуг центрифуг++ультра препаративн++центрифуг аналитическ++центрифуг скоростн++центрифуг центрифуж++роторы ротор++центрифуг бак-ротор бакет-ротор fixed-angle++rotor swing-out++rotor swing++bucket++rotor laboratory++centrifuge benchtop++centrifuge refrigerated++centrifuge microcentrifuge minicentrifuge ultracentrifuge spin++column tabletop++centrifuge floor-standing++centrifuge high-speed++centrifuge преаналитическ++центрифуг центрифуг++ИКМ Eppendorf Эппендорф =Eppendorf Eppendorf++5418 Eppendorf++5425 Eppendorf++5424 Eppendorf++5424R Eppendorf++5430 Eppendorf++5430R Eppendorf++5427 Eppendorf++5427R Eppendorf++5418R Eppendorf++5702 Eppendorf++5702R Eppendorf++5810 Eppendorf++5810R Eppendorf++5910 Eppendorf++5910R Eppendorf++5910Ri Eppendorf++5920 Eppendorf++5920R Eppendorf++Centrifuge++MiniSpin MiniSpin MiniSpin++plus FastGene Eppendorf++Concentrator++Plus =Vacufuge Hettich Хеттих =Hettich Hettich++Universal++320 Hettich++Universal++320R Hettich++EBA Hettich++EBA+200S Hettich++EBA+280 EBA++21 EBA++200 EBA++280 EBA++270 Mikro++120 Mikro++185 Mikro++200 Mikro++200R Mikro++22 Mikro++220 Mikro++220R Universal++32 Universal++32R Universal++320 Universal++320R Universal++3500 Universal++3000 Rotanta++460 Rotanta++460R Rotanta++460RC Rotina++380 Rotina++380R Rotina++420 Rotina++420R Rotina++35 Rotina++35R Rotofix++32 Rotofix++32A Rotixa++500 Rotixa++50RS Rotixa++50S Roto++Silenta Hettich++Centrifuge++ROTO Sigma Сигма =Sigma Sigma++1-7 Sigma++2-6 Sigma++2-7 Sigma++2-8 Sigma++3-30 Sigma++3-30K Sigma++3-30KS Sigma++3-18K Sigma++3-30KH Sigma++4-15 Sigma++4-16K Sigma++4-16KS Sigma++4-5L Sigma++6-16KS Sigma++6K10 Sigma++6K15 Sigma++6KS Sigma++8-7 Sigma++8KS Sigma++10K Sigma++3-K30 1-14 1-14K 1-15K 2-15 2-15P Thermo++Sorvall Sorvall Сорвал =Sorvall Sorvall++Legend Sorvall++Legend+Micro+17 Sorvall++Legend+Micro+21 Sorvall++Legend+Micro+21R Sorvall++Legend+RT+plus Sorvall++Legend+X1 Sorvall++Legend+X1R Sorvall++Legend+X4 Sorvall++Legend+X4R Sorvall++ST Sorvall++ST+8 Sorvall++ST+16 Sorvall++ST+16R Sorvall++ST+40R Sorvall++Espresso Sorvall++LYNX+4000 Sorvall++LYNX+6000 Sorvall++MX+120 Sorvall++MX+150 Sorvall++MX+150+plus Sorvall++WX+80 Sorvall++WX+90 Sorvall++WX+ultra++100 Sorvall++WX+ultra++90 Sorvall++WX+ultra++100+plus Sorvall++RC+5C Sorvall++RC+6 Sorvall++RC+12BP Sorvall++RC+12 Sorvall++Pico Sorvall++Stratos Sorvall++Heraeus++Multifuge Heraeus++Multifuge++X1 Heraeus++Multifuge++X1R Heraeus++Multifuge++X3 Heraeus++Multifuge++X3R Heraeus++Multifuge++X4 Heraeus++Multifuge++X4R Heraeus++Megafuge Heraeus++Megafuge++8 Heraeus++Megafuge++16 Heraeus++Megafuge++16R Heraeus++Megafuge++40 Heraeus++Megafuge++40R Heraeus++Biofuge Heraeus++Biofuge+Pico Heraeus++Biofuge+Primo Heraeus++Biofuge+Stratos Heraeus++Biofuge+Fresco Beckman++Coulter Beckman Бекман =Beckman Beckman++Avanti Beckman++Avanti++J Beckman++Avanti++J-15 Beckman++Avanti++J-25 Beckman++Avanti++JE Beckman++Avanti++J-26 Beckman++Avanti++JXN Beckman++Avanti++J-30 Beckman++Avanti++J-30I Beckman++Avanti++HP-25 Beckman++Avanti++HP-30 Beckman++Optima Beckman++Optima++L Beckman++Optima++L-90 Beckman++Optima++L-100 Beckman++Optima++LE Beckman++Optima++X Beckman++Optima++XPN Beckman++Optima++XL Beckman++Optima++XE Beckman++Optima++TLX Beckman++Optima++MAX Beckman++Optima++Max-XP Beckman++Optima++MAX-TL Beckman++Allegra Beckman++Allegra++X-12 Beckman++Allegra++X-15 Beckman++Allegra++X-15R Beckman++Allegra++X-22 Beckman++Allegra++X-30 Beckman++Allegra++X-30R Beckman++Microfuge Beckman++Microfuge++16 Beckman++Microfuge++20 Beckman++Microfuge++22R Beckman++Microfuge++22R+plus Beckman++Coulter++GS-6 Beckman++Coulter++GS-6R Beckman++GS-15 Beckman++JS-MC Beckman++Coulter++JE-5.0 Hermle Хермле =Hermle Hermle++Z206A Hermle++Z216-A Hermle++Z216-MK Hermle++Z287-A Hermle++Z326 Hermle++Z326K Hermle++Z366 Hermle++Z366K Hermle++Z383 Hermle++Z383K Hermle++Z446K Hermle++Z446-K Hermle++ZK+200 Hermle++Z36HK Hermle++Z180 Hermle++Z200M Kubota Кубота =Kubota Kubota++3700 Kubota++5400 Kubota++5500 Kubota++5910 Kubota++5910i Kubota++5922 Kubota++6500 Kubota++6800 Kubota++6900 Kubota++KR+22000 Kubota++KS+22000 Kubota++Tabletop++Centrifuge Hitachi Хитачи =Hitachi Hitachi++CP-Series Hitachi++CP+80 Hitachi++CP+100 Hitachi++CP+100MX Hitachi++CR21 Hitachi++CR21G Hitachi++CR22N Hitachi++Centrifuge Hitachi++Himac Heraeus++Sepatech Heraeus++Sepatech++17R ОПН-3 ОПН-3-02 ОПН-3-02-Б ОПН-8 ОПН-8-УХЛ ОПН-8-УХЛ4.2 ЦЛК-1 ЦЛК-1УХЛ4.2 Liston Листон Liston++C+2201 Liston++C+2204 Liston++C+2206 Liston++CM+22 Liston++CM+2406 Liston++C+2401 Liston++C+2406 Liston++C+2406+rotor Армед Армед++ОПН-8 Армед++ОПн-8УХЛ ЦЛМН-Р10-01 ЦЛМН-Р10-01-С ЦЛБ ОС-6М ОС-6Ц-6 ОС-6 ОС-6М5 ЛК-2 ЛК-2М ЛК-2МУ Эленф РПЦ-6 РПЦ-3 РПЦ-12 PCR-Plate++Spinner ELMI Elmi Эльми Elmi++CM-50 Elmi++CM-6M Elmi++CM-6MT Elmi++CM-6M.05 Elmi++CM-6M.07 Elmi++CM-6M.10 Skyline++Centrifuge Sky++Line BIOSAN BIOSAN++Microspin BIOSAN++FVL BIOSAN++LMC-3000 BIOSAN++LMC-4200R BIOSAN++LMC-4200R-2 Spectrafuge Labnet Mini-Star Andrew Mini++Star
```

### 6.3. `CER_03_Liquid_Handling_Robotics` — автоматизация / роботизация / dispensers

```text
автоматическ++пробоподготовк автоматизированн++пробоподготовк автоматическ++пипет автоматическ++дозатор автоматическ++дозирован автоматическ++жидкостн автоматическая++жидкостная++станция автоматизированн++жидкостн жидкостн-обрабатывающ++робот робот++жидкостн++операци станц++жидкостн станц++пробоподготовк жидкостн++робот робот++лабораторн лабораторн++робот робот++пипетирован пипетирующ++робот пипетирующ++станц станц++пипетирован liquid++handling liquid++handling++robot liquid-handling++system liquid-handling++platform pipetting++robot automated++pipetting automated++liquid++handling automated++sample++preparation laboratory++automation lab++automation work++station++пипет workstation++liquid robotic++liquid++handling роботизаци++лаборатор автоматизаци++лаборатор LIMS-интеграц LIMS=integration deck++station микропланшетн++роботизаци automated++microplate++station automated++assay automated++ELISA ELISA-станц hit++picking compound++dispensing acoustic++dispensing acoustic++droplet++dispensing acoustic++liquid++handler nanoliter++dispensing piezoelectric++dispenser inkjet++dispenser pin++tool++dispensing colony++picker colony++picking system++bulk++reagent++dispenser bulk++dispenser microplate++washer microplate++dispenser plate++washer plate++dispenser Tecan Текан =Tecan Freedom++EVO Freedom++EVO+75 Freedom++EVO+100 Freedom++EVO+150 Freedom++EVO+200 EVOlyzer EVOWare Fluent Fluent++480 Fluent++780 Fluent++1080 Fluent++ID Tecan++Fluent Tecan++Cavro Tecan++D300 Tecan++D300e Tecan++Spark Tecan++Sunrise Tecan++Infinite Hamilton Гамильтон Хэмилтон =Hamilton Microlab++STAR Microlab++STARlet Microlab++STAR+IVD Microlab++STARplus Microlab++VENUS Microlab++NIMBUS Microlab++NIMBUS+4 Microlab++Prep Microlab++Vantage Vantage Vantage++Liquid++Handling Hamilton++STAR Hamilton++STARlet NGS++Workstation HAM++STAR Easy++Blot Hamilton++Easy++Blot Hamilton++Easy++Punch Beckman++Coulter Beckman++Biomek Biomek++4000 Biomek++FX Biomek++FXP Biomek++NX Biomek++NXP Biomek++NXP+SPAN Biomek++NXP+MC Biomek++NXP+96 Biomek++NXP+384 Biomek++i5 Biomek++i7 Biomek++3000 Beckman++Echo Echo++525 Echo++550 Echo++650 Echo++MS Echo++Liquid++Handler Echo++Acoustic Echo++Qualifier Beckman++Vi-CELL Beckman++Sterile++Connection Eppendorf++epMotion epMotion epMotion++5070 epMotion++5073 epMotion++5075 epMotion++5075t epMotion++5075m epMotion++5075vac epMotion++5070tmx epMotion++5070tmx-PCR epMotion++96 epMotion++M-Series epMotion++Vac epMotion++TMX Eppendorf++ep++Motion Opentrons Опентронс =Opentrons Opentrons++OT-2 Opentrons++Flex Opentrons++OT-3 Opentrons++OT-One OT-2++Liquid Andrew Эндрю Andrew+ Andrew++Pipetting Andrew++Alliance Andrew++Lyovapor Waters++Andrew Waters++Andrew+ Agilent++Bravo Agilent++VWorks Agilent++Bravo++Automated++Liquid++Handling Agilent++Bravo++NGS Agilent++Vertical++Pipetting Agilent++Bravo++SRT Bravo++NGS Bravo++Verity Agilent++AssayMAP Agilent++AssayMAP+Bravo PerkinElmer Перкин++Элмер ПеркинЭлмер PerkinElmer++JANUS PerkinElmer++JANUS++G3 PerkinElmer++JANUS+G3+Pro PerkinElmer++Sciclone Sciclone++G3 Sciclone++ALH Sciclone++NGSx PerkinElmer++Multiprobe PerkinElmer++Zephyr Zephyr++G3 PerkinElmer++MicroDrop PerkinElmer++FlexDrop Flexdrop Hudson++Robotics Hudson++SOLO SOLO++Liquid Hudson++Pickolo Pickolo Molecular++Devices Molecular++Devices++QPix QPix++400 QPix++460 Formulatrix Mantis Mantis++liquid SAS-VLA SciClone Echo++Liquid Beckman++Vi BIO-LIQ Eve PCR-DAW PCR-DAW++Plate+Washer
```

---

## 7. EXCLUDE-строки

### 7.1. Базовый EXCLUDE (применяется ко всем 3 автопоискам)

```text
ноутбук компьютер сервер принтер картридж++принтер бумага мебель халат маск респиратор дезинфицир моющ++средств клининг уборк фоторадар транспорт автомобил автомобиль обществ+мнен охот посуд массаж арматур фильтроэлемент фрезер фотоник электроплит масс+отдых криптограф вычисл+техника фонтан крипто парков+простран электрон+очеред судостроен слепоч+масс поток+посетит вентиляц пищеблок конференц+связь дошкольн навигац барометр налогов =ИКТ научн+чтен пылесос искусств+вентиляц+легк пьезоэлектрич проектор кондиционер сантех дым подстил+грызун подстил поставк+имуществ контейнер уборк+помещен тестомес автомойк водител вакуумн+уборочн+машин поставк+продукт+питан чищен+картофел проведен+гигиенич+подготовк перчатки+химич+стойк погрузк+грузов+вагон клининг+услуг огнезащитн+обработк расчетн+графич+станц комплексн+уборк+помещен газет полуфабр овощ родовспомож
```

### 7.2. Дополнительный EXCLUDE для `CER_01` — отсечь Sanger-секвенирование и плоский электрофорез

Применять вместе с 7.1. **Не** отсекает PA800/BioPhase/7100 — они уже не Sanger.

```text
секвенирован++Сэнгер Sanger Sanger++sequencing ABI++3500 ABI++3500xL =3500xl SeqStudio 3130 3130xl 3730 3730xl genetic++analyzer генетическ++анализатор плоск++электрофорез гель-документац гель-документировани камер++горизонтальн++электрофорез камера++горизонтальн++электрофорез камер++вертикальн++электрофорез камера++вертикальн++электрофорез источник++питан++электрофорез =SDS-PAGE PAGE++gel Bio-Rad++Mini-PROTEAN +Mini-PROTEAN+Tetra Bio-Rad++PowerPac PowerPac =PowerPac Bio-Rad++Sub-Cell GE++Hoefer Hoefer++SE600 Cleaver +OWL+Easy-Cast OWL++Easy-Cast Owl+B Owl++Centipede TGX++Stain-Free SubCellGT Sub-Cell+GT Hoefer++ESC++separator Hoefer++Mini-VE
```

> Этот блок отсекает `Sanger CE-секвенаторы` (ABI 3500/3500xL/SeqStudio — они в MDX_01) и **плоский гель-электрофорез** (агарозный/PAGE — это не наш скоуп, шумный рынок медицинских лабораторий). PA800 / BioPhase / Agilent 7100 / Lumex Капель — остаются.

### 7.3. Дополнительный EXCLUDE для `CER_02` — отсечь промышленные и медицинские для крови

```text
промышленн++центрифуг центрифуг++промышленн декантер сепаратор++центробежн молочн++сепаратор центрифуга++для++нефт центрифуга++масл сливкоотделител +декантер +шнек+декантер +трехфазн+декантер биодекантер центрифуг++медицинск медицинск++центрифуг центрифуг++для++крови центрифуг++для++плазм клиническ++центрифуг центрифуг++для++пробирок++крови центрифуг++пакетный +гемоплазмосепаратор плазмосепарирующ
```

> **Уточнение:** не отсекать **универсальные центрифуги Hettich/Sigma**, которые используются и для крови, и для пробоподготовки. Этот EXCLUDE отсекает чисто-кровные (типа Hettich Haemafuge) и промышленные. Если на первом прогоне будет слишком жёстко — снять `центрифуг++пробирок++крови`.

### 7.4. Дополнительный EXCLUDE для `CER_03` — отсечь индустриальную робототехнику

```text
KUKA ABB++robot Fanuc++robot Universal++Robots сварочн++робот промышленн++робот робот++сборочн робот++паллетирован складск++робот робот++для++производств АРМ++сборщик упаковочн++робот промышленный++манипулятор индустриальн++робот машиностроительн++робот робот++для++покраск +Schunk
```

---

## 8. КТРУ/ОКПД2 коды (опционально)

| Код                          | Описание                                                       | К какому автопоиску    |
|------------------------------|-----------------------------------------------------------------|------------------------|
| `26.51.53.110`              | Приборы для физико-химического анализа                         | CER_01                  |
| `28.29.41.110`              | Центрифуги лабораторные                                         | CER_02                  |
| `28.29.41.190`              | Центрифуги прочие (включая промышленные — осторожно)            | CER_02 *(уточнить EXCLUDE 7.3)* |
| `26.51.53.130`              | Приборы и аппараты для физико-химического анализа (общий)      | CER_01, CER_03          |
| `26.51.66.190`              | Приборы для измерений (прочие)                                  | CER_01..03 *(широкий)* |
| `26.51.43.130`              | Приборы для измерения уровня жидкостей и газов                  | (другой скоуп)          |
| `28.99.39.190`              | Оборудование специального назначения прочее                     | CER_03                  |
| `28.29.39.190`              | Машины и оборудование для пищевой/химической промышленности — прочие | CER_03 *(автоматизация)* |

**Текстовая форма** (для INCLUDE если КТРУ-фильтр недоступен):

```text
26.51.53.110 28.29.41.110 28.29.41.190 26.51.53.130 26.51.66.190 28.99.39.190 28.29.39.190
```

---

## 9. Чеклист после первого прогона

| № | Что проверить                                                                                                | Действие при найденной проблеме                                          |
|---|--------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------|
| 1 | CER_01 — не пролезают ли тендеры на ABI 3500/3500xL или SeqStudio (Sanger CE)                                | Усилить 7.2: добавить конкретные модели если выпали                       |
| 2 | CER_01 — не отсекаются ли тендеры на CE-MS (например Sciex CESI 8000 + ZenoTOF)                              | Это редкий кейс. Если важен — добавить в INCLUDE `CESI++MS CESI8000`     |
| 3 | CER_02 — не цепляются ли промышленные декантеры/сепараторы для молочки/нефти                                 | Усилить 7.3: добавить конкретные бренды промышленных (Alfa Laval, GEA Westfalia, Pieralisi, Flottweg) |
| 4 | CER_02 — не отсекается ли универсальная Hettich/Sigma для медицинских лабораторий                            | Снять `центрифуг++пробирок++крови` из 7.3 если жёстко                    |
| 5 | CER_03 — не пролезает ли индустриальная робототехника (KUKA, ABB, Fanuc)                                     | Усилить 7.4                                                               |
| 6 | CER_03 — все ли отечественные «автоматические станции» покрыты? «БиоВитрум», «Лабика», «РобоЛаб»             | Добавить если выпали (отдельный российский рынок — обычно ниже бюджет)   |
| 7 | Покрытие новых вендоров: Andrew+ (Waters), Mantis (Formulatrix), Opentrons Flex                              | Уже включены. Проверить через 3 месяца — реально ли встречаются          |
| 8 | Сколько единиц лимита уходит на скачивание архивов CER_02 (центрифуг много мелких лотов)                     | Если близко к лимиту — включить дедуп БД (`processed_tenders`)            |

---

## 10. Связь с CLI `tenderland_bot`

```toml
# Капиллярный электрофорез, центрифуги, роботизация (3 автопоиска)
[[autosearch]]
id = ...
topic = "CER_01_Capillary_Electrophoresis"
domain = "capillary_centrifuges_robotics"

[[autosearch]]
id = ...
topic = "CER_02_Centrifuges"
domain = "capillary_centrifuges_robotics"

[[autosearch]]
id = ...
topic = "CER_03_Liquid_Handling_Robotics"
domain = "capillary_centrifuges_robotics"
```

---

## 11. Источники для верификации

- **Beckman Coulter PA 800 Plus / P/ACE / CESI 8000**: https://www.beckman.com/capillary-electrophoresis/pa-800-plus
- **Sciex BioPhase 8800 / CESI**: https://sciex.com/products/capillary-electrophoresis
- **Agilent 7100 Capillary Electrophoresis**: https://www.agilent.com/en/product/capillary-electrophoresis
- **Bio-Rad BioFocus 3000**: https://www.bio-rad.com/en-us/category/capillary-electrophoresis
- **Lumex Капель** (RU): https://www.lumex.ru/catalog/sistemy-kapillyarnogo-elektroforeza/
- **Eppendorf Centrifuges** (5418/5424/5427/5430/5702/5810/5910/5920): https://www.eppendorf.com/centrifuges
- **Hettich** (Universal / EBA / Mikro / Rotanta / Rotina / Rotofix): https://www.hettichlab.com/
- **Sigma Laborzentrifugen** (1-7 / 2-7 / 3-30 / 4-16 / 8KS): https://www.sigma-laborzentrifugen.de/
- **Thermo Sorvall** (Legend / ST / LYNX / MX / WX / RC / Pico / Stratos): https://www.thermofisher.com/centrifuges
- **Beckman Avanti / Optima / Allegra / Microfuge**: https://www.beckman.com/centrifuges
- **Hermle**: https://www.hermle-labortechnik.de/
- **Kubota**: https://www.kubota.co.jp/scientific-instruments/
- **Hitachi Himac / CP-Series**: https://www.hitachi-hightech.com/global/en/products/science/separation/centrifuge/
- **Tecan Freedom EVO / Fluent**: https://www.tecan.com/freedom-evo, https://www.tecan.com/fluent
- **Hamilton Microlab STAR / STARlet / Vantage / NIMBUS**: https://www.hamiltoncompany.com/automated-liquid-handling
- **Beckman Biomek / Echo**: https://www.beckman.com/liquid-handlers
- **Eppendorf epMotion** (5070/5073/5075/96): https://www.eppendorf.com/epmotion
- **Opentrons** (OT-2 / Flex): https://opentrons.com/
- **Andrew Alliance (Waters)**: https://www.waters.com/andrew
- **Agilent Bravo / AssayMAP / VWorks**: https://www.agilent.com/en/product/automated-liquid-handling
- **PerkinElmer JANUS / Sciclone / Zephyr**: https://www.perkinelmer.com/automation
- **Российские**: Liston (Жуковский), Эленф, Армед, Сапфир-Центрифуга, ELMI (Латвия/Россия), БиоВитрум, Лабика
