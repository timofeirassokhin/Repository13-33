# `keywords_config_capillary_centrifuges_robotics.md` — аддендум v1.1

**Дата:** 2026-05-14
**Применить к:** `keywords_config_capillary_centrifuges_robotics.md` (v1.0)

Расширение `CER_03_Liquid_Handling_Robotics` — добавлены приборы **MGI Tech / Vazyme / Nanodigm**.

> Этот файл существует отдельно, потому что основной `keywords_config_capillary_centrifuges_robotics.md` был открыт в Word/LibreOffice при патче и заблокирован для записи. Когда основной файл закроется — содержимое нужно мерджить в раздел 6.3 (или, что то же самое, в Tenderland UI копи-пастится строка ниже целиком вместо старой 6.3).

---

## Что добавлено

### MGI Tech — автоматизированные станции пробоподготовки и workflow

| Прибор          | Назначение                                           |
|-----------------|------------------------------------------------------|
| MGISP-100       | Магнитная пробоподготовка, 8-каналов                 |
| MGISP-100RS     | Магнитная пробоподготовка, 8-каналов, для NGS        |
| MGISP-960       | Магнитная пробоподготовка, 96-каналов high-throughput |
| MGISP-960RS     | Магнитная пробоподготовка, 96-каналов, для NGS       |
| MGISP-Smart 8   | Компактная sample prep станция                       |
| MGISP-NE32      | NGS-ориентированная станция                          |
| MGISP-NE384     | High-throughput 384-канальная для NGS                |
| MGISTP-3000     | Sample transfer processor                            |
| MGISTP-7000     | Sample transfer processor high-throughput            |
| MGI Stomatic    | Automated DNA library prep                           |
| DNBelab C4      | Single-cell platform (single-cell library prep)      |
| ZTRON           | Workflow automation / informatics platform           |

### Vazyme — automated NGS library preparation

| Платформа           | Назначение                                       |
|---------------------|--------------------------------------------------|
| VAHTS Smart 8       | Automated 8-sample NGS library preparation       |
| Hieff NGS Smart     | Automated library prep system                    |
| Hieff NGS Auto      | Automated library prep (extended)                |
| Hieff NGS MaxUp     | High-throughput automated library prep           |
| Vazyme MaxUp        | Automated platform                               |
| Vazyme MA-9000      | Automated NGS prep                               |

### Nanodigm — изоляция циркулирующих опухолевых клеток (CTC) + NGS panels

| Прибор                | Назначение                                                       |
|-----------------------|------------------------------------------------------------------|
| Nanodigm IsoFlux      | Isolation of rare cells (CTC) для жидкой биопсии                |
| Nanodigm-1            | Анализатор для CTC                                               |
| Nanodigm-А            | Анализатор для ЦОК (циркулирующих опухолевых клеток)            |
| Nanodigm Анализатор   | Платформа CTC + NGS processor                                    |
| Nanodigm processor    | Образцовый processor для NGS panels                              |

---

## Обновлённая INCLUDE-строка для `CER_03_Liquid_Handling_Robotics` (целиком, для копи-пейста)

> Скопировать ВСЁ что между ```text-блоками — это полная замена раздела 6.3.

```text
автоматическ++пробоподготовк автоматизированн++пробоподготовк автоматическ++пипет автоматическ++дозатор автоматическ++дозирован автоматическ++жидкостн автоматическая++жидкостная++станция автоматизированн++жидкостн жидкостн-обрабатывающ++робот робот++жидкостн++операци станц++жидкостн станц++пробоподготовк жидкостн++робот робот++лабораторн лабораторн++робот робот++пипетирован пипетирующ++робот пипетирующ++станц станц++пипетирован liquid++handling liquid++handling++robot liquid-handling++system liquid-handling++platform pipetting++robot automated++pipetting automated++liquid++handling automated++sample++preparation laboratory++automation lab++automation work++station++пипет workstation++liquid robotic++liquid++handling роботизаци++лаборатор автоматизаци++лаборатор LIMS-интеграц LIMS=integration deck++station микропланшетн++роботизаци automated++microplate++station automated++assay automated++ELISA ELISA-станц hit++picking compound++dispensing acoustic++dispensing acoustic++droplet++dispensing acoustic++liquid++handler nanoliter++dispensing piezoelectric++dispenser inkjet++dispenser pin++tool++dispensing colony++picker colony++picking system++bulk++reagent++dispenser bulk++dispenser microplate++washer microplate++dispenser plate++washer plate++dispenser Tecan Текан =Tecan Freedom++EVO Freedom++EVO+75 Freedom++EVO+100 Freedom++EVO+150 Freedom++EVO+200 EVOlyzer EVOWare Fluent Fluent++480 Fluent++780 Fluent++1080 Fluent++ID Tecan++Fluent Tecan++Cavro Tecan++D300 Tecan++D300e Tecan++Spark Tecan++Sunrise Tecan++Infinite Hamilton Гамильтон Хэмилтон =Hamilton Microlab++STAR Microlab++STARlet Microlab++STAR+IVD Microlab++STARplus Microlab++VENUS Microlab++NIMBUS Microlab++NIMBUS+4 Microlab++Prep Microlab++Vantage Vantage Vantage++Liquid++Handling Hamilton++STAR Hamilton++STARlet NGS++Workstation HAM++STAR Easy++Blot Hamilton++Easy++Blot Hamilton++Easy++Punch Beckman++Coulter Beckman++Biomek Biomek++4000 Biomek++FX Biomek++FXP Biomek++NX Biomek++NXP Biomek++NXP+SPAN Biomek++NXP+MC Biomek++NXP+96 Biomek++NXP+384 Biomek++i5 Biomek++i7 Biomek++3000 Beckman++Echo Echo++525 Echo++550 Echo++650 Echo++MS Echo++Liquid++Handler Echo++Acoustic Echo++Qualifier Beckman++Vi-CELL Beckman++Sterile++Connection Eppendorf++epMotion epMotion epMotion++5070 epMotion++5073 epMotion++5075 epMotion++5075t epMotion++5075m epMotion++5075vac epMotion++5070tmx epMotion++5070tmx-PCR epMotion++96 epMotion++M-Series epMotion++Vac epMotion++TMX Eppendorf++ep++Motion Opentrons Опентронс =Opentrons Opentrons++OT-2 Opentrons++Flex Opentrons++OT-3 Opentrons++OT-One OT-2++Liquid Andrew Эндрю Andrew+ Andrew++Pipetting Andrew++Alliance Andrew++Lyovapor Waters++Andrew Waters++Andrew+ Agilent++Bravo Agilent++VWorks Agilent++Bravo++Automated++Liquid++Handling Agilent++Bravo++NGS Agilent++Vertical++Pipetting Agilent++Bravo++SRT Bravo++NGS Bravo++Verity Agilent++AssayMAP Agilent++AssayMAP+Bravo PerkinElmer Перкин++Элмер ПеркинЭлмер PerkinElmer++JANUS PerkinElmer++JANUS++G3 PerkinElmer++JANUS+G3+Pro PerkinElmer++Sciclone Sciclone++G3 Sciclone++ALH Sciclone++NGSx PerkinElmer++Multiprobe PerkinElmer++Zephyr Zephyr++G3 PerkinElmer++MicroDrop PerkinElmer++FlexDrop Flexdrop Hudson++Robotics Hudson++SOLO SOLO++Liquid Hudson++Pickolo Pickolo Molecular++Devices Molecular++Devices++QPix QPix++400 QPix++460 Formulatrix Mantis Mantis++liquid SAS-VLA SciClone Echo++Liquid Beckman++Vi BIO-LIQ Eve PCR-DAW PCR-DAW++Plate+Washer MGI++Tech MGITech MGI++Tech++Co BGI++MGI ЭмДжиАй++Тех МГИ-Тех =MGISP MGISP-100 MGISP-100RS MGISP-960 MGISP-960RS =MGISP-Smart MGISP-Smart++8 MGISP-Smart8 MGISP-NE32 MGISP-NE384 MGI++sample++preparation MGI++pipetting MGI++automated MGI++Stomatic Stomatic Stomatic-100 Stomatic-NGS DNBelab++C4 DNBelab-C4 single-cell++DNBelab MGISTP MGISTP-3000 MGISTP-7000 MGI++sample++transfer ZTRON =ZTRON ZTRON++Lab ZTRON++MAX MGI++ZTRON MGI++automation++platform MGI++workflow++automation MGISP-100++magnetic MGISP-960++magnetic 96-канальн++пипетирующ++MGI Vazyme Вазайм Вазим =Vazyme Vazyme++VAHTS VAHTS++Smart VAHTS++Smart+8 VAHTS-Smart-8 VAHTS++Automated Vazyme++Hieff Hieff++NGS++Smart Hieff++NGS++Auto Hieff++NGS++MaxUp MaxUp =MaxUp Vazyme++MaxUp Vazyme++automated++library Vazyme++automated++NGS Vazyme++auto++library++prep Vazyme++Smart Vazyme++MA-9000 MA-9000 Nanodigm NanoDigm Нанодигм НаноДигм Нанодайм НаноДайм Nanodigm++IsoFlux IsoFlux Nanodigm-1 Nanodigm-А Nanodigm-Анализатор Nanodigm++Analyzer NanoDigm++Analyzer NanoDigm++processor Nanodigm++platform NanoDigm++CTC ЦОК-анализатор Nanodigm++ЦОК Nanodigm++циркулирующих++клеток циркулирующ++опухолев++клетк CTC-анализатор CTC++isolation IsoFlux++System IsoFlux++Rare++Cell Nanodigm++Genomics Nanodigm++Diagnostics Nanodigm++Group
```

---

## Дополнительные пояснения

### MGI Tech — пересечение скоупа с MDX_02

`MGISP-100` и `MGISP-960` ранее упоминались в `MDX_02_Reagents_Libraries` как **магнитные станции выделения**. Это не противоречие — в MDX_02 они в контексте «магнитные станции для выделения НК», в CER_03 в контексте «универсальная роботизация лабораторных операций». Дедупликация по `tender_id` в CLI отсечёт лоты которые попали в оба автопоиска.

### Vazyme — преимущественно reagent-компания, приборы появились недавно

Vazyme Biotech (Китай, Nanjing) изначально reagent-house для qPCR / NGS-library prep. С ~2022 запустили линейку **automated platforms**:
- `VAHTS Smart 8` — 8-sample automated NGS library prep
- `Hieff NGS Smart/Auto/MaxUp` — серия автоматических library prep систем

Если на российском рынке встречаются их **только реагенты** (VAHTS Universal Plus, Hieff FFPE, etc.) — они уже в `MDX_02` (добавлены в этом же спринте). В `CER_03` идут **только приборы**.

### Nanodigm — российская компания, специфика «жидкая биопсия + NGS»

Nanodigm Group (Москва) — производитель аппаратов для:
- Изоляции циркулирующих опухолевых клеток (**CTC / ЦОК**)
- Подготовки образцов для NGS-панелей онкологических заболеваний (Nanodigm их собственные панели, ранее упоминались в `MDX_03`)

В `CER_03` идут **приборы**:
- `Nanodigm IsoFlux` — главный их продукт для CTC isolation
- `Nanodigm-1 / Nanodigm-А` — модельные ряды анализаторов
- `Nanodigm processor` — общий термин для их NGS-prep оборудования

---

## Применение

### Если есть прямой доступ к `keywords_config_capillary_centrifuges_robotics.md`

1. Закрыть файл в Word / LibreOffice / любом редакторе который его держит
2. Открыть в текстовом редакторе (VS Code, Notepad++)
3. Найти раздел `### 6.3. \`CER_03_Liquid_Handling_Robotics\``
4. Заменить содержимое ```text-блока на строку выше
5. Этот аддендум-файл удалить

### Если настройка идёт в Tenderland UI (главный use case)

INCLUDE-строки нужны для копи-пейста в фильтр «Включать» Tenderland — этот файл уже даёт готовый текст. **Аддендум-файл можно использовать напрямую, не дожидаясь мерджа в основной файл.**

В этом случае:
1. Зайти в Tenderland UI → редактирование автопоиска `CER_03_Liquid_Handling_Robotics` (если уже создан) или создание (если ещё нет)
2. В поле «Включать» вставить строку из этого аддендума целиком (заменив предыдущую если была)
3. EXCLUDE 7.1 + 7.4 — без изменений (брать из `keywords_config_capillary_centrifuges_robotics.md` основного)

---

## TODO для git history

Когда основной файл `keywords_config_capillary_centrifuges_robotics.md` будет доступен для записи:
1. Применить замену 6.3 INCLUDE → как в этом аддендуме
2. Удалить этот аддендум: `git rm tenderland_bot/config/keywords_config_capillary_centrifuges_robotics_v1.1_addendum.md`
3. Закоммитить как `keyword-configs: merge CER_03 v1.1 addendum into main file`
