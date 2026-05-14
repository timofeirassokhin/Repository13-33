# Tenderland — автопоиски по общелабораторному оборудованию

**Дата подготовки:** 2026-05-14
**Версия:** 1.0
**Цель:** покрыть тендеры на общелабораторное оборудование, на которое у Глювекса есть прямые/дистрибьюторские контракты — Memmert, Binder, Buchi, Heidolph, IKA, Lauda, Julabo, Sartorius, Eppendorf, Retsch, и т.д. Это **отдельный кластер тендеров от инструментальной аналитики**: бюджеты меньше, конкуренция выше, нужны быстрая реакция и понимание КТРУ-кодов под медицину/госы.

> Парный файл — `keywords_config.md` (инструментальная аналитика, 8 автопоисков). Глобальные параметры (фильтр id, даты, частота прогона) одинаковые — см. там.

---

## 1. Карта автопоисков

| №  | Имя автопоиска                | Что ищем                                                                                          |
|----|-------------------------------|---------------------------------------------------------------------------------------------------|
| 01 | `LAB_01_Climate`             | CO2-инкубаторы, термостаты (сухие/водяные/циркуляционные/охлаждающие), сушильные шкафы, климатокамеры, муфельные/трубчатые печи |
| 02 | `LAB_02_Sterilization`       | Паровые автоклавы, сухожаровые стерилизаторы, плазменные/газовые стерилизаторы                    |
| 03 | `LAB_03_Evaporation`         | Роторные испарители, концентраторы вакуумные, лиофильные сушилки, ультразвуковые ванны/процессоры |
| 04 | `LAB_04_Mixing_Homogenization` | Магнитные/верхнеприводные мешалки, шейкеры, вортексы, гомогенизаторы, диспергаторы, мельницы лабораторные |
| 05 | `LAB_05_Reactors`            | Биореакторы / ферментёры (steel и одноразовые), химические реакторы, параллельные синтезаторы, микроволновые синтезаторы |
| —  | `LAB_06_Weighing_Water_pH` *(опц.)* | Аналитические/прецизионные весы, системы очистки воды (Milli-Q), pH/EC/O2-метры                |

**Опциональный LAB_06** — включать, когда решим системно охотиться за «малыми тендерами» на весовое и измерительное оборудование (там много шума от ОФД/торговых весов, нужна жёсткая EXCLUDE-доводка).

---

## 2. Скоуп — что включено / что нет

| Категория                                       | Решение | Комментарий                                                                              |
|-------------------------------------------------|---------|------------------------------------------------------------------------------------------|
| CO2-инкубаторы, лабораторные инкубаторы         | ✅      | Memmert ICO/IN/IF, Thermo Heracell/Heratherm, Binder, Esco                                |
| Термостаты водяные/циркуляционные/сухие         | ✅      | Lauda/Julabo/Huber/Polyscience/Eppendorf/Memmert UFB/Binder                              |
| Сушильные шкафы                                 | ✅      | Memmert UN/UF, Binder ED/FD, ШС, СНОЛ                                                     |
| Климатические камеры, влагокамеры              | ✅      | Memmert HCP/HPP, Binder KMF/MKF, Espec, Esco Isotherm                                     |
| Муфельные и трубчатые печи                      | ✅      | Nabertherm, Carbolite, СНОЛ, Накал, ПЗАН                                                  |
| Паровые автоклавы, сухожаровые                  | ✅      | Tuttnauer, Systec, ВК-30/75, ГК-100, ГП-560, ШСС, Memmert SF                              |
| Роторные испарители, концентраторы              | ✅      | Buchi Rotavapor, Heidolph Hei-VAP, IKA RV, GeneVac, Christ                                |
| Лиофильные сушилки (freeze dryers)              | ✅      | Christ Alpha/Epsilon, Labconco FreeZone, Telstar                                          |
| Ультразвуковые ванны и процессоры              | ✅      | Elma, Bandelin, Hielscher, Branson, Сапфир                                                |
| Магнитные мешалки, шейкеры, вортексы           | ✅      | IKA, Heidolph, Velp, Stuart, Eppendorf, Корвет, BioSan                                    |
| Верхнеприводные мешалки, гомогенизаторы        | ✅      | IKA Eurostar / Ultra-Turrax, Heidolph Hei-TORQUE / SilentCrusher, Polytron (Kinematica)   |
| Лабораторные мельницы                          | ✅      | Retsch, IKA A11/M20, Fritsch Pulverisette, Foss Cyclotec                                  |
| Биореакторы / ферментёры                       | ✅      | Sartorius BIOSTAT, Eppendorf BioFlo, INFORS HT, Applikon, Cytiva Xuri/XCellerex          |
| Химические реакторы / параллельные синтезаторы | ✅      | Buchi miniclave/midiclave, Asynt ReactoMate, Radleys, Mettler-Toledo OptiMax             |
| Микроволновые синтезаторы                      | ✅      | Anton Paar Monowave, CEM Discover/Liberty Blue, Milestone STARTSynth                      |
| Гидротермальные/Parr-реакторы                  | ✅      | Parr 4848/4566, Berghof BR-25/100                                                          |
| Аналитические/прецизионные весы                | ⚪ опц. | Mettler-Toledo, Sartorius, Ohaus, Kern, AND — только в LAB_06                             |
| Системы очистки воды (Milli-Q)                 | ⚪ опц. | Millipore Milli-Q, Sartorius arium, Adrona, Veolia, Эви-Дист, Аквилон, ДВС-М              |
| pH-/EC-/O2-метры                               | ⚪ опц. | Mettler-Toledo SevenExcellence, Hanna HI, WTW, Эксперт-pH                                 |
| **Хроматографы, масс-спектрометры**            | ❌      | См. `keywords_config.md` — другой кластер                                                  |
| **Секвенаторы, ПЦР, ИФА**                      | ❌      | См. `keywords_config_molecular_diagnostics.md`                                             |
| Бытовые холодильники/морозильники              | ❌      | EXCLUDE — слишком много шума с поставками для пищеблоков                                  |
| Медицинские диагностические аппараты (УЗИ, ЭКГ) | ❌      | EXCLUDE                                                                                    |
| Промышленные печи / индустриальные автоклавы    | ❌      | EXCLUDE — другой класс, не лабораторное                                                   |

---

## 3. Алгоритм настройки в Tenderland UI

Тот же, что и в `keywords_config.md` (раздел 2). Повторить **5 раз** (6 с опциональным LAB_06).

| Шаг | Действие                                                                                       |
|-----|------------------------------------------------------------------------------------------------|
| 1   | Создать новый автопоиск с именем из таблицы 1 (например `LAB_01_Climate`).                    |
| 2   | Добавить **один** фильтр «Поиск по ключевым словам». INCLUDE — из раздела 6. EXCLUDE — раздел 7. |
| 3   | Дата публикации (range): `от = СЕГОДНЯ−7`, `до = пусто`.                                       |
| 4   | Дата окончания подачи (range): `от = СЕГОДНЯ`, `до = пусто`.                                   |
| 5   | *(опц.)* КТРУ/ОКПД2 фильтр (`tree_list`) — коды из раздела 8.                                   |
| 6   | Сохранить → `id` → внести в `config/autosearches.toml`.                                        |

---

## 4. Глобальные параметры

Те же что в `keywords_config.md` (раздел 3). Фильтр include id 136, exclude id 137, сортировка `tender_sysPublishDate.desc`, дедуп по `tender_id`. Не повторяю — единый стандарт для всех 13+ автопоисков.

---

## 5. Синтаксис ключевых слов

См. `keywords_config.md` раздел 4: `пробел`=OR, `++`=AND-стемминг, `+`=точная фраза, `=`=точное совпадение без морфологии.

---

## 6. INCLUDE-строки

> Для копи-пэйст: каждая строка ниже — **одной строкой**, без переносов.

### 6.1. `LAB_01_Climate` — инкубаторы / термостаты / сушильные шкафы / климатокамеры / печи

```text
инкубатор СО2-инкубатор СО2++инкубатор CO2-инкубатор CO2++инкубатор углекислотн++инкубатор инкубатор++углекислотн инкубатор++клеточн++культур инкубатор++ткань CO2++incubator CO2-incubator =CelCulture клеточн++инкубатор бактериологическ++инкубатор биологическ++термостат микробиологическ++инкубатор инкубатор++лабораторн лабораторн++инкубатор воздушн++инкубатор инкубатор++конвекционн инкубатор++принудительн циркуляц++воздух термостат термостат++лабораторн лабораторн++термостат термостат++суховоздушн суховоздушн++термостат термостат++суховоздушный термостат++водян водян++термостат водяная++бан водяная++баня лабораторн++водян++бан термостат++циркуляционн циркуляционн++термостат термостат++охлажда охлажда++термостат криостат криотерм холодильн++термостат термостат++нагрева нагрева++термостат термостат++жидкостн нагрев-охлажда++термостат термостат++пельтье =Peltier термостат++сухоблочн сухоблочн++термостат термошейкер термоблок термостатир++блок термостат++суховоздушный++ТСО шкаф++суши шкаф++сушильн сушильн++шкаф сушильн++шкафы лабораторн++сушильн++шкаф сушильн++стерилизационн вакуумн++сушильн++шкаф шкаф++лабораторн++сушильн++ШС =ШС-80 =ШС-40 =ШС-65 =ШСС =СНОЛ камера++климатическ климатическ++камер климатокамер влажностн++камер климат-камер климатическ++испытан камера++постоянн++услови constant++climate test++chamber камер++стабильн камер++стабильности термокамер термостатн++камер термостатн++комнат термошкаф постоянство++температур печь++муфельн муфельн++печь высокотемпературн++печь печь++трубчатая трубчат++печь лабораторн++печь печь++лабораторн прокалочн++печь печь++прокалочн обжиговая++печь печь++лабораторн++до++1200 печь++лабораторн++до++1100 печь++лабораторн++до++1500 печь++лабораторн++до++1700 высокотемпературн++электрическ++печь электропеч муфел tube++furnace muffle++furnace термошкаф++ванны Memmert Меммерт Мемерт =Memmert =UN30 =UN55 =UN75 =UN110 =UN160 =UN260 =UN450 =UN750 =UF30 =UF55 =UF75 =UF110 =UF160 =UF260 =UF450 =UF750 =UFP400 =UFP500 =UFP700 =UFP800 =UFE500 =UFE600 =UFE700 =UFB400 =UFB500 =UFB700 =SF55 =SF75 =SF110 =SF160 =SF260 =SF450 =SF750 =SFE500 =SFE600 =SFP500 =SFP800 IN30 IN55 IN75 IN110 IN160 IN260 IN450 IN750 INplus INplus30 INplus55 INplus110 IFplus IFplus30 IFplus55 IFplus110 IFplus160 IFplus260 IFplus450 IFplus750 =IPP30 =IPP55 =IPP110 =IPP260 =IPP410 =IPP500 =IPP750 ICO50 ICO105 ICO150 ICO240 =ICOmed150 =ICOmed240 HCP50 HCP105 HCP150 HCP240 HPP110 HPP260 HPP410 HPP750 WB7 WB14 WB22 WB29 WPE45 WBU45 WTB22 WBE22 WNB10 WNB14 WNB22 WNB29 SN30 SN55 SN75 SN110 SN160 SN260 SN450 SN750 SE110 SE260 SE450 SE750 Binder Биндер Биндер =Binder =KB23 =KB53 =KB115 =KB240 =KB400 =KB720 =CB53 =CB60 =CB100 =CB150 =CB160 =CB210 =CB220 =CB260 =BF53 =BF115 =BF240 =BF400 =BF720 =BD23 =BD56 =BD115 =BD240 =BD400 =BD720 =ED23 =ED53 =ED115 =ED240 =ED400 =ED720 =FD23 =FD53 =FD115 =FD240 =FD400 =FD720 =FED23 =FED53 =FED115 =FED240 =FED400 =FED720 =FP23 =FP53 =FP115 =FP240 =FP400 =FP720 =KBF =MKF =MKFT =KMF =VD23 =VD53 =VD115 =VD240 =VD400 Thermo++Heracell Heracell++150 Heracell++240 Heracell++150i Heracell++240i Heracell++VIOS Heracell++Vios Thermo++Heratherm Heratherm++IGS Heratherm++OGS Heratherm++OMS Heratherm++OMH Forma++Series Forma++3110 Forma++3120 Sanyo++MCO MCO-15AC MCO-18AIC MCO-19AIC MCO-20AIC MCO-5AC Panasonic++MCO Eppendorf++Galaxy Galaxy++14S Galaxy++48S Galaxy++48R Galaxy++170R Galaxy++170S CelCulture++CCL Esco++CelCulture Esco++Isotherm Esco++MCO Pol-Eko Pol-Eko-Aparatura CLN CHL CLW SLN Lauda Лауда Лаудер =Lauda Lauda++ECO =Lauda++Alpha =Lauda++Proline =Lauda++Integral =Lauda++Variocool =Lauda++Microcool =Lauda++Hydro =Lauda++Aqualine Julabo Юлабо Жулабо =Julabo Julabo++CORIO Julabo++MX Julabo++FP Julabo++F25 Julabo++FPW Julabo++MA Julabo++Magnio Julabo++Highlight Julabo++Dyneo Huber Хубер =Huber Huber++CC Huber++Unistat Huber++Compatible++Control Huber++Ministat Huber++Polystat Huber++MPC Polyscience Полисайнс =Polyscience Polyscience++WhisperCool ThermoFlex GFL =GFL ОПП-2-78 ТСЛ ТСЛ-1 ТСЛ-2 БУГ ВТ-20 ВТ-25 ВТ-50 БСВ Эппендорф ThermoMixer ThermoStat ThermoMixer++C ThermoMixer++F ThermoMixer++FP ThermoStat++C BioSan TS-100 TS-100C TS-100D TS-100E TS-100M PSC-20 Korvet Корвет Lab++Companion DRY-LINE Жидкая++баня жидк++баня =Memmert++WB Memmert++WB7 Memmert++WB14 СНОЛ-1 СНОЛ-2 СНОЛ-3 СНОЛ-7 СНОЛ-12 СНОЛ-50 СНОЛ-3,5 ЭКПС Накал =ПЗАН Nabertherm Наберхтерм Набертерм =Nabertherm L3 L5 L9 L15 LE6 LE14 LH15 LH30 LH60 LH120 LHT04 LHT08 LHT4 LHT8 LHT15 LHT16 LT5 LT9 LT15 LT24 LT40 LT80 N7 N11 N17 N31 NA5 NA7 NA15 NA17 NA40 P330 RHTH NRA17 LBR05 RT50-250 RT04 R7 R30 R50 R80 R120 RT-150 Carbolite Карболайт =Carbolite =CWF =RWF =CTF =STF =TZF =MTF =HRF =HZS Carbolite++Gero Lindberg++Blue++M Thermolyne =Thermolyne =Vulcan Vulcan++3-130 Vulcan++3-550 Vulcan++3-1750 Mufflestar TFS NF Espec Эспек =Espec Espec++PR Espec++PL Espec++SH Espec++ARS climatic++chamber temperature++humidity++chamber stability++chamber =ICH-климат ICH++stability =ВКА =ВЕКА Каскад ВЛИ Витязь ШС-80-01 ШС-80-СПУ ШС-200-2 САМ-50 ЭКПС ЭКПС-10 ЭКПС-50 ЭКПС-30
```

### 6.2. `LAB_02_Sterilization` — автоклавы и стерилизаторы

```text
автоклав автоклав++лабораторн автоклав++паровой паров++автоклав автоклав++медицинск медицинск++автоклав автоклав++стерилизац стерилизационн++автоклав вертикальн++автоклав горизонтальн++автоклав настольн++автоклав стерилизатор стерилизатор++паровой паровой++стерилизатор паров++стерилизатор стерилизатор++горизонтальн стерилизатор++вертикальн стерилизатор++лабораторн лабораторн++стерилизатор стерилизатор++медицинск медицинск++стерилизатор steam++sterilizer steam++autoclave laboratory++autoclave стерилизац++пар стерилизация++паром стерилизация++сухим++жар сухожаровой++стерилизатор стерилизатор++сухожаровой воздушн++стерилизатор стерилизатор++воздушн стерилизатор++сухой++жар стерилизатор++суховоздушн суховоздушн++стерилизатор hot++air++sterilizer dry++heat++sterilizer плазменн++стерилизатор стерилизатор++плазменн H2O2++стерилизатор перекисн++стерилизатор низкотемпературн++стерилизатор низкотемпературн++стерилизац газов++стерилизатор стерилизатор++газов EO-стерилизатор ETO-стерилизатор этиленоксидн++стерилизатор формальдегидн++стерилизатор стерилизатор++форвакуумн форвакуумн++стерилизатор вакуумн++стерилизатор предвакуумн++стерилизатор форвакуум++цикл стерилизац++цикл цикл++стерилизац B-класс B++класс предвакуумн++стерилизатор циркуляц++стерилизатор бикс бикс++стерилизац бикс++медицинск бикс++упаковочн камера++автоклав камера++стерилизатор Tuttnauer Туттнауэр Тутнауер =Tuttnauer Tuttnauer++2540 Tuttnauer++3870 Tuttnauer++3850 Tuttnauer++5075 Tuttnauer++5596 Tuttnauer++23 Tuttnauer++T-Edge T-Edge T-Lab T-Max T-Smart T-Care Systec Систек =Systec Systec++V Systec++D Systec++H Systec++DE-23 Systec++DX-30 Systec++DX-45 Systec++DX-65 Systec++DX-90 Systec++DX-150 Systec++DX-200 Systec++VX-65 Systec++VX-95 Systec++VX-150 Systec++VX-200 Steris =Steris Steris++Amsco Amsco++Lab Getinge =Getinge Getinge++LSB Getinge++HS66 Mocom =Mocom Mocom++Millennium Mocom++Exacta Cisa =Cisa Astell =Astell Liarre =Liarre PHCBI PHCBI++autoclave Memmert++SF Memmert++SF55 Memmert++SF75 Memmert++SF110 Memmert++SF160 Memmert++SF260 Memmert++SF450 Memmert++SF750 Memmert++SFE Memmert++SFP Memmert++Heating++Cooling++Incubators ВК-30 ВК-30-01 ВК-30-Я-ФП ВК-75 ВК-75-Я-ФП ВКа-75 ВКу-50 ВКу-75 ГК-100 ГК-100-3 ГП-560 ГПа-560 ГП-560-2 ГПД-280 ГПД-460 ГПД-560 ШСС ШСС-80 ШСС-200 ШС-80 ШСС-80П ВВ-30 СтериСан ВЛКМ ШСвЛ Тюменьмедико ТЗМОИ ВОС-200 АВОТ Astell++Hybrid Astell++Compact Getinge++Quadro Sterrad =Sterrad Sterrad++100NX Sterrad++NX Sterrad++100S V-Pro V-PRO++Steris ASP Anprolene Andersen++Anprolene 3M++Steri-Vac Bionet Renosem
```

### 6.3. `LAB_03_Evaporation` — испарители, концентраторы, лиофильные сушки, ультразвук

```text
ротор++испарител роторн++испарител испаритель++роторн ротационн++испарител испарительн++колб роторно-пленочн++испарител плёночн++испарител пленочн++испарител rotary++evaporator =Rotavapor rotavapor испарительн++установк дистилл++установк лабораторн++дистиллятор Buchi Бюхи Бухи Буши =Buchi =Büchi =Rotavapor =R-100 =R-200 =R-210 =R-220 =R-300 =R-3 =R-114 =R-205 =R-215 Rotavapor++R-100 Rotavapor++R-200 Rotavapor++R-220 Rotavapor++R-300 Buchi++R-100 Buchi++R-300 Buchi++Syncore Buchi++Multivapor Buchi++Sublimator Heidolph Хайдольф Хейдольф =Heidolph =Hei-VAP =Hei-VAP+Core =Hei-VAP+Value =Hei-VAP+Advantage =Hei-VAP+Industrial =Hei-Vap+Expert =Hei-Vap+Precision =Hei-Vap+Pro =Hei-VAP+Ultimate =Laborota Laborota++4000 Laborota++4001 Laborota++4002 Laborota++4003 Laborota++4010 Laborota++4011 Laborota++20 Hei-VAC Heidolph++Distimatic IKA ИКА =IKA =RV =RV3 =RV5 =RV8 =RV10 =RV10-V =RV10-VC =RV10-VC-S =RV+10 =RV+8 RV++basic RV++digital =RV+10+digital RC++basic Stuart RE300 RE301 RE401 Witeg =Witeg-Lab WEV-1001L WEV-1001S WEV-1001V ZP++rotary KNF=Laboport KNF-Rotavac LK Yamato RE201 RE211 RE301 RE801 RE-501 Eyela N-1100 N-1100V N-1200B N-1300 SB-1300 Lab++Companion RE-100 RE-200 концентратор вакуумн++концентратор центрифуж++концентратор speed++vac =SpeedVac CentriVap GeneVac EZ-2 EZ-2++Elite EZ-2++Series HT-4 HT-4X HT-12 HT-24 EZ-2++Personal Christ Кристель =Christ =Alpha =Alpha+1-2 =Alpha+2-4 Alpha++1-2++LD Alpha++2-4++LD Alpha++3-4 Beta++1-8 Epsilon++2-4 Epsilon++2-6 Epsilon++2-10 Epsilon++2-25 RVC++2-18 RVC++2-25 RVC++2-33 Gamma Labconco =Labconco FreeZone FreeZone++Plus FreeZone++Triad FreeZone++1L FreeZone++2.5L FreeZone++4.5L FreeZone++6L FreeZone++12L FreeZone++18L FreeZone++Console FreeZone++Stoppering CentriVap CentriVap++Benchtop CentriVap++DNA лиофильн++сушк лиофильн++сушилк лиофильная++сушилка сушилка++лиофильн установк++лиофильн freeze-dryer freeze++dryer lyophilizer лиофилизатор сублимац++сушк сублимац++установк ИУ-2 ИУ-3 ЛС-3 ЛС-1000 ЛС-500 ВТ-25 ВТ-60 Telstar Тельстар =Telstar Telstar++LyoQuest Telstar++LyoBeta Telstar++LyoAlfa SP++Scientific SP++VirTis VirTis VirTis++AdVantage VirTis++Genesis VirTis++Wizard Pirani GEA AdVantage Millrock Cuddon Бамо МиниСушка =SureLyo Frozone Mfg Frozen Centrifugal vacuum evaporator =Concentrator+5301 =Concentrator+5305 =Eppendorf+5301 =Eppendorf+5305 =Vacufuge Vacufuge++plus Eppendorf++Concentrator++Plus ультразвуков++ванн ультразвук++ванн ванн++ультразвуков ванн++ультразвук++очистк ультразвуков++очистк ультразвуков++процессор ультразвуков++диспергатор ultrasonic++bath ultrasonic++processor ultrasonic++homogenizer ultrasonic++cleaner sonic++bath sonotrode зонд++ультразвук Elma Эльма =Elma Elma++E Elma++S Elma++P Elma++X-tra Elmasonic Elmasonic++S Elmasonic++P Elmasonic++X-tra Elmasonic++Easy Elmasonic++One Bandelin Банделин =Bandelin Sonorex Sonorex++Digitec Sonorex++Super Sonorex++Bandelin Sonorex++DT Sonorex++TK SonoPuls Bandelin++SonoPuls Bandelin++SonoTrode Bandelin++HD Hielscher Хильшер =Hielscher =UP200H =UP200S =UP400S =UIP500hd =UIP1000hd UP++50H UP++100H Branson Брансон Бренсон =Branson Branson++2510 Branson++2800 Branson++3510 Branson++3800 Branson++5510 Branson++5800 Branson++8510 Branson++Sonifier Sonifier++450 Sonifier++550 Сапфир Сапфир-ТТЦ ULTRAclean PSB-9 ПСБ Stegler СитиУльтра Misonix Q-Sonica
```

### 6.4. `LAB_04_Mixing_Homogenization` — мешалки / шейкеры / вортексы / гомогенизаторы / мельницы

```text
магнитн++мешалк мешалк++магнитн магнитная++мешалка магнитная++мешалка++с++подогревом верхнеприводн++мешалк мешалк++верхнеприводн пропеллерн++мешалк лопастн++мешалк якорн++мешалк мешалк++лабораторн лабораторн++мешалк mechanical++stirrer overhead++stirrer magnetic++stirrer hotplate++stirrer лабораторн++перемешиватель перемешиватель++лабораторн встряхиватель встряхиватель++лабораторн лабораторн++встряхиватель shaker++лабораторн шейкер++лабораторн лабораторн++шейкер шейкер шейкер++орбитальн орбитальн++шейкер шейкер++линейн линейный++шейкер качающ++шейкер 3D-шейкер шейкер-инкубатор шейкер++для++пробирок шейкер++планшетн пластинчат++шейкер микропланшетн++шейкер микроплашетн++встряхиватель orbital++shaker linear++shaker rocker++shaker rocker rotator вортекс мини-вортекс лабораторн++вортекс вортекс-миксер vortex++mixer vortex++shaker shaker++vortex микровстряхиватель гомогенизатор лабораторн++гомогенизатор гомогенизатор++лабораторн ножев++гомогенизатор стержнев++гомогенизатор пробоподготовительн++гомогенизатор bead++mill bead++beater диспергатор лабораторн++диспергатор Ultra-Turrax Ultra++Turrax homogenizer disperser high++shear++mixer мельниц лабораторн++мельниц мельниц++лабораторн планетарн++мельниц шаров++мельниц шаровая++мельница вибрационн++мельниц ножев++мельниц mill++laboratory ball++mill planetary++mill cutting++mill mortar++grinder Mixer++Mill rotor++mill IKA ИКА =IKA =RCT =RCT-Basic =RH =RH-Basic RH++digital RCT++Basic RCT++digital RCT++Standard C-MAG++HS C-MAG++MS C-MAG++HP =RET =RET+Basic =RET+control =RET+B C-MAG++HS7 C-MAG++HS10 RH++basic+2 RH++digital+2 =Eurostar =Eurostar+20 =Eurostar+40 =Eurostar+60 =Eurostar+100 =Eurostar+200 =Eurostar+Power Eurostar++control RW20 RW25 RW28 RW++digital Microstar Lab++Egg =MS+1+Minishaker MS++1 =MS+3 =MS+3+digital VG-3 KS++130 KS++260 KS++3000 KS-15 KS-501 HS++260 HS++501 ROCKER MR++3+basic MR++Hei +Standard MR++Hei-End =T10 =T18 =T25 =T50 T10++basic T18++basic T18++digital T25++digital T50++digital A11 A11++basic =A10 =A20 M20 MF10 MF10++basic MultiDrive Yellow++line MagicLab Heidolph Хейдольф Хайдольф =Heidolph Hei-Mix Hei-Plate Hei-Plate++Tec Hei-Plate++Value Hei-Plate++Standard Hei-Mix+S Hei-Tec Hei-TORQUE Hei-TORQUE++Core Hei-TORQUE++Value Hei-TORQUE++Expert Hei-TORQUE++Ultimate RZR++2020 RZR++2102 RZR++50 RZR++100 RZR++200 SilentCrusher SilentCrusher++M SilentCrusher++S Diax++900 Diax++600 Reax Reax++Top Reax++2000 Reax++2050 Reax++Control Unimax Unimax++1010 Unimax++2010 Polymax Polymax++1040 Polymax++2040 Promax Inkubator Inkubator++1000 Inkubator++1010 Vibramax Titramax Rotamax Velp Велп =Velp F20 F25 F60 F100 F40 F202 F203 F204 F205 ARE AREX AREC AREX-6 MultiHS Multi-Stirrer SF1 SF40 OS20 OS40 OS80 SK-300 SK-O330-Pro VTF Vortex++F202A2 OV5 Stuart Стюарт =Stuart SB161 SB162 SB163 SD162 SD161 UC152 SS3 SS40 SSC1 SSC3 SSL3 SSL4 SSL5 SSM1 SA8 SA7 SR2 SR5 RT5 SB300 SHM2 SHO5D SI500 SI505 SI550 OS5 OS10 Eppendorf Эппендорф =Eppendorf Innova Innova++S44i Innova++S40i Innova++44 Innova++44R Multitron Multitron++Cell Multitron++Pro Multitron++Standard Multitron++Eco INFORS++HT Infors++HT New++Brunswick New++Brunswick++I26 Edmund++Bühler =Edmund+Bühler PA-25 KS-15 KS-15++Control KM-2 KL-2 SM-30 TH-30 BC-30 KS++4000 BioSan Биосан =BioSan Multi-Spin MR-1 MR-12 Bio++RS-24 Bio++RS Multi+Bio+RS-24 OS-10 OS-20 PSU-10i PSU-20i Combi-Spin RotoBot SkyLine TS-100 TS-100C MSV-3500 SkyLine++Shaker BioShake++iQ Wiggens Witeg WSC-1503 WSO-100 WSO-200 WSO-100T WSC-1501-N WSB-30 OS-2000 OS-3000 Daihan WiseMix WiseStir WiseShake Wisd MS20 MSH-20D-Set MS-20 ESL-160 Lab++Companion AS-1 IS-971R IS-971RF IS-971RFS BFR-50CD SHO-2D SHO-1D SO-160 Корвет Korvet PHMT-PSC18 PHMT-PSC24 Polytron Политрон Polytron+PT Polytron++PT-1200 Polytron++PT-2500 Polytron++PT-3100 Polytron++MR3100 Kinematica Polytron++Aggregate Polytron++PT-D Bio-Gen Bio-Gen-PRO PRO-Scientific Multi-Gen Bertin++Precellys Precellys++24 Precellys++Evolution Mixer++Mill MM200 MM301 MM400 MM500 MM++500++nano MM200++Cryomill Retsch Ретч =Retsch Retsch++PM PM100 PM200 PM400 Retsch++GM200 GM300 GM301 SM100 SM200 SM300 RM200 RM200++Mortar++Grinder GM++200 GM++300 RM++200 ZM200 ZM300 RS200 TM300 Cyclotec Cyclotec++1093 Cyclotec++CT++410 Foss FossDecanter Cyclotec Hammertec Cyclotec++3010 Pulverisette Pulverisette++0 Pulverisette++1 Pulverisette++2 Pulverisette++3 Pulverisette++5 Pulverisette++6 Pulverisette++7 Pulverisette++11 Pulverisette++14 Pulverisette++15 Pulverisette++16 Fritsch =Fritsch =Glen+Mills =SPEX +Geno/Grinder SPEX++8000 SPEX++8000D Geno/Grinder BeadBug BeadBug++D1030 D1030 Omni Omni-Bead++Ruptor Beadbeater Mini-Beadbeater BioSpec MiniBeadbeater SC-30 Cole-Parmer Mortar Стержневая Цеолитов
```

### 6.5. `LAB_05_Reactors` — биореакторы / химические реакторы / синтезаторы

```text
биореактор биореактор++лабораторн лабораторн++биореактор ферментер ферментёр ферментер++лабораторн лабораторн++ферментер биореактор++миниатюрн пилотн++биореактор пилотн++ферментер биореактор++настольн биореактор++перемешива биореактор++аэрационн биореактор++ферментац ферментац++сосуд ферментац++реактор fermenter bioreactor laboratory++bioreactor pilot++bioreactor stirred-tank++bioreactor stainless++steel++bioreactor одноразов++биореактор одноразов++ферментер single-use++bioreactor single-use++fermenter SUB рокинг++биореактор wave-биореактор wave++bioreactor биореактор++клеточн++культур cell++culture++bioreactor микробиологическ++биореактор бак++реакц бак++ферментац химическ++реактор реактор++лабораторн лабораторн++реактор лабораторн++реакторная++система реакц++сосуд реакц++колб реакторная++система реакторная++установка калориметрическ++реактор лабораторн++синтез автоклавн++реактор давлен++реактор реактор++высок++давлен высок-давлен++реактор reaction++calorimeter laboratory++reactor jacketed++reactor pressure++reactor parallel++synthesis++station параллельн++синтез параллельн++реактор синтезатор лабораторн++синтезатор пептидн++синтезатор автоматическ++синтезатор олигонуклеотидн++синтезатор +пептид+синтез +олигосинтез микроволнов++синтезатор microwave++synthesizer microwave++reactor microwave++digestion микроволнов++минерализ микроволнов++разложен гидротермальн++реактор гидротермальн++синтез Sartorius Сарториус Сартериус =Sartorius BIOSTAT BIOSTAT++A BIOSTAT++B BIOSTAT++B-DCU BIOSTAT++Q BIOSTAT++Cplus BIOSTAT++Bplus BIOSTAT++STR BIOSTAT++RM BIOSTAT++MD ambr++15 ambr++250 ambr ambr++bioreactor BIOSTAT++D-DCU =Flexsafe Cubitainer Eppendorf =BioFlo BioFlo++110 BioFlo++115 BioFlo++120 BioFlo++320 BioFlo++410 BioFlo++415 BioFlo++510 BioFlo++520 BioFlo++610 BioFlo++710 BioFlo++720 New++Brunswick CelliGen CelliGen++Plus CelliGen++BLU DASGIP DASGIP++Parallel DASGIP++Bioreactor DASbox INFORS++HT Infors++HT =Multifors =Multifors+2 =Labfors =Labfors+5 =Techfors =Techfors-S Minifors Minifors+2 Multitron++Cell Applikon Аппликон =Applikon ez-Control my-Control bio++Console ezControl Mini-Bioreactor =miniBio =MicroBioreactor mini-Bio Cytiva Цитива GE++Healthcare GE++Wave XCellerex XCellerex++XDR Xuri Xuri++Cell++Expansion WAVE++Bioreactor WAVE++Bioreactor++System ReadyToProcess Allegro Allegro++STR Allegro++MR Pall Cytiva++HyClone HyClone++S.U.B. HyClone++S.U.M. HyPerforma HyPerforma++S.U.B. HyPerforma++S.U.F. HyPerforma++HyClone +Mobius Mobius++iFlex Mobius++100L Mobius++200L Mobius++50L Mobius++Bioreactor SciLog Solaris BIOSEP Bionet BBI++Bioreactor++System Distek =BIOne BIOne++1250 BIOne++1500 BIOne++3000 BlueSens BlueInOne BlueLab Diversis +Lambda+Minifor Lambda+Minifor LAMBDA++Minifor MagicBlu Heinkel Buchi midiclave Buchi++miniclave Buchi++midiclave Buchi++Polyclave Buchi++Encapsulator Buchi++Mini++Spray++Dryer pilote++clave +Glas-Col chemglass +Asynt =Asynt ReactoMate ReactoMate++ATLAS ReactoMate++CONTROLLER DrySyn DrySyn++MULTI DrySyn++ULTRA Radleys Радлис =Radleys Reactor-Ready Reactor-Ready++Duo Reactor-Ready++Pilot StarFish Carousel Carousel++6 Carousel++12 Carousel++ASD Mettler-Toledo OptiMax OptiMax++1001 OptiMax++Pro EasyMax EasyMax++102 EasyMax++202 EasyMax++402 EasyMax++HFCal MultiMax MiniBlock MiniBlock++Compact MiniBlock++XT XTAL HEL HEL++ChemSCAN HEL++Polyblock Anton++Paar =Anton+Paar =Monowave Monowave++200 Monowave++300 Monowave++400 Monowave++450 Multiwave Multiwave++Go Multiwave++5000 Multiwave++7000 Multiwave++PRO Multiwave++3000 Multiwave++ECO MAS-100 CEM CEM++Discover Discover++SP Discover++LabMate Discover++Bio Discover++2.0 Discover++S Class Mars++6 Mars++Xpress Mars++2 +Liberty +Liberty+Blue Liberty++Lite Liberty++HT12 Liberty++Prime Milestone Милестоун =Milestone Milestone++Ethos Milestone++START Milestone++MicroSYNTH STARTSynth EthosUP Ethos++X EthosUP++MAX RotoSynth UltraWAVE UltraCLAVE ETHOS Sineo MWS-7 MicroPREP-A=Parr =Parr+4848 =Parr+4566 =Parr+4564 4848 4566 4564 4520 4560 4570 5500 Berghof Бергхоф =Berghof BR-25 BR-50 BR-100 BR-300 BR-500 BR-1000 Berghof++DAB =DAB-2 Berghof++DAB-2 +Anton+Paar+HighPressure
```

### 6.6. `LAB_06_Weighing_Water_pH` — весы / системы воды / pH-метры *(опционально)*

```text
весы++аналитическ аналитическ++весы прецизионн++весы лабораторн++весы весы++лабораторн микровесы semi-microbalance ultra-microbalance моментн++весы влагомер влаговесы термогравиметрическ++анализатор моментно-весов Mettler-Toledo Метлер Меттлер-Толедо =Mettler =Mettler+Toledo XPR XPR2U XSE XS ML MS XS104 XS204 XS205 XSR ME Quantos Sartorius Сарториус Cubis Cubis++II Cubis++MCA Practum Entris BCE Secura Quintix Practum Practum124 Practum224 OHAUS Охаус =OHAUS Pioneer Adventurer Explorer Discovery PA64 Pioneer++PX Pioneer++PR Adventurer++AX Explorer++EX AND Эй++энд++Ди A&D GR HR HM HR-150A HR-250A FX-i FZ-i GF Kern =Kern ABT ABS ALJ ALS Радвал WLC Радвал=ВЛР =ВЛР-1М =ВЛР-200 =ВЛТ ВЛТ-150 ВЛТ-510 ВЛТ-510С =ВЛТЭ ВЛТЭ-150 Adam =Adam Equipment Acculab ACOM Cas =Cas Cas++MWP MW-II MW-150 МАССА-К ВК-150 ВК-300 ВК-600 ВК-1500 Sartogosm система++очистк++вод деионизованн++вод деионизованная++вода ультрачист++вод водоочистител водоподготовка++лаборатор лабораторн++водоочиститель сверхчист++вод Type+I Type+II Milli-Q MilliQ Millipore Милли-Кью Milli-Q++Reference Milli-Q++IQ7000 Milli-Q++IQ7003 Milli-Q++IQ7005 Milli-Q++IQ7010 Milli-Q++Direct Milli-Q++Advantage Milli-Q++Integral Milli-Q++Synergy Milli-Q++Ultrapure Synergy Synergy++UV Elix Elix++3 Elix++5 Elix++10 Elix++20 Elix++Essential Sartorius++arium arium++pro arium++mini arium++comfort arium++advance Adrona =Adrona Crystal++E Crystal++EX Crystal++HQ Crystal++Bio Veolia Veolia++ELGA =ELGA =PureLab PureLab++Flex PureLab++Quest PureLab++Ultra Эви-Дист =Эви-Дист Аквилон =Аквилон Аквалаб ДВС-М ДВС-А ДЭ-4 ДЭ-25 АЭ-4 АЭ-25 ДГВС pH-метр кондуктометр оксиметр иономер ОВП-метр анализатор++ионов мультипараметрическ++анализатор Mettler++SevenExcellence Mettler++SevenCompact Mettler++FiveEasy Mettler++FiveGo Hanna++HI =Hanna HI++2002 HI++2020 HI++2210 HI++2211 HI++2215 HI++2300 HI++4221 HI++5221 Edge++HI HQD WTW =WTW inoLab Multi inoLab++pH7110 inoLab++Multi+9420 inoLab++Cond Multi++3410 Эксперт-pH =Эксперт-pH Эксперт-001 Эксперт-002 Адилаб АНИОН-410 АНИОН-7050 АНИОН-7000 Импульс ИПЛ-101 +H'pHANIA +Sartorius +PB pHysica pH++WTW pH-meter pH+meter pH-150 pH-150МИ pH-150И pH-410 pH-410МИ pH-211 pH-301 pH-303 pH-410 pH-420 pH-501 pH-501-50
```

---

## 7. EXCLUDE-строки

### 7.1. Базовый EXCLUDE (применяется ко всем 5+1 автопоискам общелаба)

Стартовая точка — EXCLUDE из `keywords_config.md` (аналитика) минус «гель», «пробир», «лабораторная посуда» (часто фигурирует в комплектации общелаба). Добавлено: бытовые холодильники, медицинские диагностические, промышленные индустриальные.

```text
ноутбук компьютер сервер принтер картридж++принтер бумага мебель халат маск респиратор дезинфицир моющ++средств клининг уборк ноутбук фоторадар транспорт автомобил автомобиль обществ+мнен охот массаж арматур фильтроэлемент фрезер фотоник электроплит масс+отдых криптограф криптограф+оборуд вычисл+техника фонтан крипто парков+простран электрон+очеред судостроен слепоч+масс поток+посетит конференц+связь дошкольн навигац барометр налогов =ИКТ научн+чтен пылесос пьезоэлектрич проектор кондиционер сантех дым подстил+грызун подстил поставк+имуществ контейнер уборк+помещен тестомес автомойк водител вакуумн+уборочн+машин поставк+продукт+питан чищен+картофел проведен+гигиенич+подготовк перчатки+химич+стойк погрузк+грузов+вагон клининг+услуг огнезащитн+обработк расчетн+графич+станц комплексн+уборк+помещен вакуум+убороч+шасси газет полуфабр овощ родовспомож холодильник++бытов морозильник++бытов холодильник++пищевой холодильник++торгов холодильник++минимаркет холодильн+ларь холодильн+витрина бытовая++техника промышленн++печь промышленн++реактор промышленн++стерилиз индустриальн++автоклав индустриальн++биореактор УЗИ-аппарат =ЭКГ электрокардиограф эндоскоп рентген++аппарат томограф маммограф флюорограф КТ-аппарат МРТ-аппарат стоматологическ++установк гинекологическ++кресл операционн++стол наркозн++аппарат аппарат++искусствен++вентиляц++легк
```

### 7.2. Дополнительный EXCLUDE — отсечь инструментальную аналитику и молекулярку

```text
хроматограф масс-спектрометр спектрометр секвенатор амплификатор ВЭЖХ HPLC =GC =LC-MS =GC-MS =ICP-MS =ICP-OES =AAS =FTIR =UV-Vis =NGS ПЦР =qPCR =qRT-PCR Illumina NovaSeq MGI DNBSEQ ABI++3500 ANALYZER++DNA генетическ++анализатор анализатор++генетическ
```

> Этот блок ставить ВМЕСТЕ с 7.1 в поле «Исключать». Чтобы не цеплять тендеры на хроматограф/масс-спектрометр/секвенатор — они в других автопоисках.

---

## 8. КТРУ/ОКПД2 коды (опционально)

| Код                          | Описание                                                              | К какому автопоиску                       |
|------------------------------|------------------------------------------------------------------------|-------------------------------------------|
| `32.50.50.190-00000839`     | Термостат лабораторный                                                | LAB_01                                     |
| `32.50.50.190-00000840..844`| Инкубатор лабораторный (разные подкатегории)                          | LAB_01                                     |
| `26.51.66.190-00000226..230`| Стерилизатор лабораторный, паровой / суховоздушный / газовый          | LAB_02                                     |
| `26.51.66.190-00000128`     | Стерилизатор паровой медицинский                                      | LAB_02 *(пересекается с медицинским)*     |
| `28.93.17.190`              | Оборудование для нагрева, охлаждения и вентиляции — лабораторное      | LAB_01, LAB_03                             |
| `27.51.21.190`              | Печи и камеры электрические лабораторные                              | LAB_01                                     |
| `26.51.66.140`              | Микроскопы (не в скоупе, но рядом)                                    | —                                          |
| `28.99.39.190`              | Оборудование специального назначения прочее                           | LAB_02..05                                 |
| `26.51.53.100..130`         | Приборы для физико-химического анализа                                | LAB_03..05 *(осторожно — пересекается с аналитикой, см. 7.2)* |
| `28.29.60.190`              | Машины и оборудование для обработки материалов прочие — мельницы, прессы | LAB_04                                  |
| `28.29.41.110`              | Центрифуги лабораторные                                                | См. `keywords_config_capillary_centrifuges_robotics.md` |

**Текстовая форма** (если КТРУ-фильтр недоступен в UI):

```text
32.50.50.190-00000839 32.50.50.190-00000840 32.50.50.190-00000841 32.50.50.190-00000842 32.50.50.190-00000843 32.50.50.190-00000844 26.51.66.190-00000226 26.51.66.190-00000227 26.51.66.190-00000228 26.51.66.190-00000229 26.51.66.190-00000230 26.51.66.190-00000128 28.93.17.190 27.51.21.190 28.99.39.190 28.29.60.190
```

---

## 9. Чеклист после первого прогона (через 1 неделю работы)

| № | Что проверить                                                                                  | Действие при найденной проблеме                                    |
|---|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|
| 1 | Не пролезают ли тендеры на бытовые холодильники / промышленные печи через LAB_01            | Добавить в EXCLUDE 7.1 конкретные бренды бытовых (Атлант, Стинол, Pozis, Indesit, Liebherr+Pharma — НЕ исключать Liebherr-Pharma!) |
| 2 | Не отсекает ли EXCLUDE 7.2 тендеры на КОМПЛЕКТНОЕ оснащение лаборатории (термостат + хроматограф)? | Перенести такой кросс-категорийный лот вручную в более релевантный автопоиск. Это редкие случаи. |
| 3 | LAB_02 — не «забивается» ли роддомами и стоматологиями? Они часто закупают автоклавы          | Добавить в EXCLUDE 7.1: `родильн родильн++дом стоматолог стоматологическ++кабинет` (но **аккуратно** — могут зацепить мед.-лабораторные центры) |
| 4 | LAB_04 — не цепляются ли тендеры на промышленные смесители (для пищевой/строительной)?       | Добавить: `пищев++смесител промышленн++смесител бетоносмесител растворосмесител` |
| 5 | LAB_05 — нет ли пересечения с большой нефтехимией?                                            | EXCLUDE: `промышленн++реактор реактор++установк++нефтехим` (но **аккуратно** — пилотные реакторы Berghof часто фигурируют в катализе)|
| 6 | Покрытие отечественных производителей термошкафов (Касимов, ВЛКМ, Тюменьмедико)               | Добавить если выпали — есть отдельный российский рынок              |
| 7 | LAB_06 (если включён) — насколько шумно от тендеров на торговые/бытовые весы                  | Добавить EXCLUDE: `торгов++весы пищев++весы скласк++весы=РРЦ` или вынести в отдельную тему |

---

## 10. Связь с CLI `tenderland_bot`

После того как 5 (или 6) автопоисков созданы и есть их `id` — добавить в `tenderland_bot/config/autosearches.toml`:

```toml
# Общелабораторное оборудование (5-6 автопоисков из keywords_config_general_lab.md)
[[autosearch]]
id = ...
topic = "LAB_01_Climate"
domain = "general_lab"

[[autosearch]]
id = ...
topic = "LAB_02_Sterilization"
domain = "general_lab"

[[autosearch]]
id = ...
topic = "LAB_03_Evaporation"
domain = "general_lab"

[[autosearch]]
id = ...
topic = "LAB_04_Mixing_Homogenization"
domain = "general_lab"

[[autosearch]]
id = ...
topic = "LAB_05_Reactors"
domain = "general_lab"

# опционально:
# [[autosearch]]
# id = ...
# topic = "LAB_06_Weighing_Water_pH"
# domain = "general_lab"
```

---

## 11. Источники для верификации модельных линеек

- **Memmert** (UN/UF/IN/IFplus/IPP/ICO/HCP/HPP/SF/SFE/SFP/WB/WBU/WTB/SNB): https://www.memmert.com/products/
- **Binder** (KB/CB/BF/ED/FD/FED/FP/KBF/MKF/KMF): https://www.binder-world.com/en
- **Thermo Heracell / Heratherm / Forma**: https://www.thermofisher.com/ru/ru/home/life-science/cell-culture/biological-safety-cabinets-co2-incubators/co2-incubators.html
- **Lauda / Julabo / Huber / Polyscience**: https://www.lauda.de / https://www.julabo.com / https://www.huber-online.com / https://www.polyscience.com
- **Nabertherm / Carbolite Gero**: https://nabertherm.com / https://www.carbolite-gero.com
- **Buchi** (Rotavapor, Syncore, Sublimator, Mini Spray Dryer): https://www.buchi.com/en/products/
- **Heidolph** (Hei-VAP, Laborota, Hei-TORQUE, SilentCrusher, Reax, Unimax, Polymax, Promax): https://heidolph-instruments.com/
- **IKA** (RV, Eurostar, Ultra-Turrax, RCT, KS, MS, HS, A11/M20/MF10): https://www.ika.com/en/
- **Christ / Labconco / SP VirTis / Telstar** (freeze drying): https://www.martinchrist.de / https://www.labconco.com / https://www.spscientific.com / https://www.telstar.com
- **Eppendorf** (Innova, Multitron, ThermoMixer, Concentrator/Vacufuge, BioFlo, DASGIP): https://www.eppendorf.com
- **Sartorius BIOSTAT / Cubis / arium**: https://www.sartorius.com
- **Cytiva Xuri / XCellerex / WAVE**: https://www.cytivalifesciences.com
- **Retsch / Fritsch** (mills): https://www.retsch.com / https://www.fritsch-international.com
- **Tuttnauer / Systec / Steris** (autoclaves): https://tuttnauer.com / https://www.systec-lab.com / https://www.steris.com
- **Anton Paar / CEM / Milestone** (microwave synthesizers): https://www.anton-paar.com / https://cem.com / https://www.milestonesrl.com
- **Parr / Berghof / Asynt / Radleys / Mettler-Toledo OptiMax/EasyMax** (lab reactors): https://www.parrinst.com / https://www.berghof-instruments.com / https://www.asynt.com / https://www.radleys.com / https://www.mt.com/lab-reactors
- **Российские**: Касимовприбор (СНОЛ), ПЗ Лабтех, ПЗАН, Накал, ВЛКМ, Тюменьмедико, Корвет, БиоСан (Латвия), Стегор, Сапфир, Электроприбор, СтериСан
