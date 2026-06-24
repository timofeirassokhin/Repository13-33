# MGI Tech NGS Sequencers — Specification Matrix

> Reference matrix for the Gluvex product configurator. Figures are from official MGI sources
> (en.mgi-tech.com / global-mgitech.com, mgi-tech.eu, completegenomics.com) plus genohub.com and
> the Russian OEM distributor Хеликон / Helicon (helicon.ru, shop.helicon.ru). Values marked
> **(?)** are uncertain, conflicting between sources, or not directly confirmed on an official spec
> sheet — re-verify before quoting in a tender. **Do not invent numbers.**
>
> ## Chemistry & terminology
> - **DNBSEQ** = MGI's proprietary sequencing chemistry. DNA is circularized and rolling-circle
>   amplified into **DNB**s (DNA NanoBalls), loaded onto a patterned-array flow cell, sequenced by
>   combinatorial probe-anchor synthesis (cPAS). MGI counts throughput in **DNBs / reads** (millions
>   or billions). No PCR-bridge clustering, low duplication, no index hopping.
> - Read modes are written MGI-style: **SE50 / SE100 / SE400** (single-end) and **PE100 / PE150 /
>   PE200 / PE300** (paired-end). "Cycles" column = total sequencing cycles (≈ 2×read for PE).
> - **Flow cells are sold per read-length config**: a flow cell + a matched **sequencing reagent
>   kit / set** for a specific mode (e.g. "DNBSEQ-G400 SE50 set", "PE150 set"). The same physical
>   flow cell type (FCL / FCS) is paired with mode-specific reagent kits.
> - **%Q30 / Q40**: MGI quotes ≥85% bases ≥Q30 for older platforms; newer platforms
>   (G99, T1+, T7+, E25) are marketed as **Q40** (≥90% bases ≥Q40 for PE150 or shorter).
> - Reads/DNBs are "effective reads" from an internal standard library; real output varies with
>   sample and library prep. Run times are on-instrument sequencing time, approximate.
>
> ## Russian OEM mapping (Хеликон / Helicon — helicon.ru)
> Helicon is MGI's Russian distributor and rebrands instruments under the **HELICON®** mark:
> - **HELICON® G400** = DNBSEQ-G400 (formerly MGISEQ-2000). Roszdravnadzor РУ **2023/20825**
>   (issued 2023-08-16). Also catalogued under MGI/BGI part **900-000170-00**.
> - **DNBSEQ-T7** — sold by Helicon under the MGI/DNBSEQ-T7 name (no separate HELICON-brand alias
>   confirmed). Helicon lists T7 and G99 in its NGS catalog.
> - **DNBSEQ-G99** — listed in the Helicon catalog (HELICON-brand alias not confirmed) **(?)**.
> - **CycloneSEQ** (nanopore) — Helicon-specific rebrand name **not confirmed** in searched sources **(?)**.
> - Reagent kits are sold by Helicon per read mode with BGI/MGI part numbers, e.g. SE400
>   **1000013857**, PE200 **1000013858** (DNBSEQ-G400 reagent sets).
>
> Last researched: 2026-05-20.

---

## DNBSEQ-E25 / E25 Flash

- **Class:** portable / lowest-throughput (~15 kg, no workstation/internet needed)
- **Flow cells / slots:** 1 microfluidic CMOS flow cell per run; self-luminescence dye chemistry
- **Chemistry:** DNBSEQ (cPAS), CMOS-based self-luminescent detection
- **Quality:** MGI markets E25/E25 Flash as **Q40** generation (?)
- **Helicon rebrand:** not confirmed (?)
- **Sources:**
  - https://mgi-tech.eu/sequencing-products/dnbseq-e25
  - https://www.completegenomics.com/products/sequencing-platforms/dnbseq-e25/
  - https://genohub.com/ngs-sequencer/22/complete-genomics-dnbseq-e25/
  - https://www.completegenomics.com/dnbseq-t1-plus-e25-flash-at-agbt-2025/

| Flow cell | Read mode | Cycles | Reads/DNBs | Output Gb (typ–max) | %Q30/Q40 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| E25 | SE100 | 100 | ≤25 M | 2.5 Gb | ≥85% Q30 (?) | ~5 hr | Target panels, pathogen ID, HIV-1 genotyping, TB drug-resistance | (?) |
| E25 | PE150 | 300 | ≤25 M | up to 7.5 Gb | ≥85% Q30 (?) | ~20 hr | Small genome / 16-sample panels | (?) |
| E25 Flash | SE50 | 50 | ≤25 M (?) | ~2.5 Gb | Q40 (?) | <2 hr (AI basecalling, ~1 min/cycle) | Rapid ID, field/point-of-care | (?) |

> E25 Flash (AGBT 2025) = AI-optimized upgrade on NVIDIA Jetson edge device; ~1 min/cycle.
> Sample capacity: one small genome or up to 16 samples for a target panel.

---

## DNBSEQ-G50 (formerly MGISEQ-200 family)

- **Class:** benchtop / low-throughput
- **Flow cells / slots:** 1 flow cell per run
- **Chemistry:** DNBSEQ (cPAS)
- **Helicon rebrand:** not confirmed (?)
- **Sources:**
  - https://global-mgitech.com/wp-content/uploads/2025/10/Brochure-EN-DNBSEQ-G50.pdf
  - https://en.mgi-tech.com/ (product index)

| Flow cell | Read mode | Cycles | Reads/DNBs | Output Gb (typ–max) | %Q30/Q40 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| G50 FCS (?) | SE50 | 50 | ~75 M (?) | ~3.75 Gb (?) | ≥85% Q30 (?) | (?) | Small panels, sample ID | (?) |
| G50 FCS (?) | SE100 | 100 | ~75 M (?) | ~7.5 Gb (?) | ≥85% Q30 (?) | (?) | Targeted, microbial | (?) |
| G50 FCS (?) | PE150 | 300 | ~75 M (?) | ~22.5 Gb (?) | ≥85% Q30 (?) | (?) | Small WGS, amplicon | (?) |

> **DATA GAP:** Per-mode G50 (MGISEQ-200 family) reads/output/run-time not confirmed from an
> official spec table in this research pass. The 2025 G50 brochure PDF
> (global-mgitech.com/.../Brochure-EN-DNBSEQ-G50.pdf) should be parsed directly to fill the table.
> Numbers above are placeholder estimates carried from the MGISEQ-200/G50 lineage and are uncertain.

---

## DNBSEQ-G99 (RS / ARS variants)

- **Class:** benchtop / mid-to-low throughput, **ultra-fast** (PE150 in ~11–12 h)
- **Flow cells / slots:** **2 independent flow cells**, each can run any time / any mode
- **Chemistry:** DNBSEQ (cPAS); marketed as **Q40**
- **Variants:** **G99RS** = standard FASTQ output (100–240 V); **G99ARS** = adds onboard
  bioinformatics computing module (advanced/secondary analysis). Same sequencing specs.
- **Helicon rebrand:** listed in Helicon NGS catalog; HELICON-brand alias not confirmed (?)
- **Sources:**
  - https://mgi-tech.eu/sequencing-products/dnbseq-g99
  - https://global-mgitech.com/seqall/dnbseq-g99/
  - https://www.completegenomics.com/products/sequencing-platforms/dnbseq-g99/
  - https://en.mgi-tech.com/Uploads/detail/2022-09-28/6333a3ff80068.pdf (G99 brochure)
  - https://genohub.com/ngs-sequencer/23/complete-genomics-dnbseq-g99/

| Flow cell | Read mode | Cycles | Reads/DNBs | Output Gb (typ–max) | %Q30/Q40 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| G99 (per FC) | PE50 | 100 | ≤400 M | ~8–40 Gb (range) (?) | Q40 | (?) | Targeted, identification | (?) |
| G99 (per FC) | SE100 | 100 | ≤400 M | up to ~40 Gb (?) | Q40 | (?) | Gene expression, metagenomics | (?) |
| G99 (per FC) | PE150 | 300 | ≤400 M | up to ~120 Gb (?) | Q40 | ~11–12 hr | Small WGS, transcriptome, panels | (?) |
| G99 (per FC) | PE300 | 600 | ≤400 M | up to ~240 Gb (whole run, 2 FC) (?) | Q40 (?) | (?) | Amplicon, microbial | (?) |
| G99 (per FC) | SE400 | 400 | ≤400 M | (?) | Q40 (?) | (?) | Long single-end amplicon | (?) |

> Confirmed: throughput **8–240 Gb per run**, **up to 400 M reads**, **PE150 in ~11 h**, 2 flow
> cells, first summary report in ~2.5 h, Q40. Read modes listed by MGI: **PE50, SE100, PE150,
> PE300, SE400, App-D**. **DATA GAP:** exact reads/output/run-time per individual mode not broken
> out on the HTML spec page — verify against the G99 brochure PDF (6333a3ff80068.pdf).

---

## DNBSEQ-G400 (formerly MGISEQ-2000; flow cells FCL & FCS)

- **Class:** benchtop / mid-throughput workhorse — "day-to-day sequencing"
- **Flow cells / slots:** up to **2 flow cells** run independently; types **FCL** (high) & **FCS** (small).
  A "FAST" reagent mode also exists for shorter turnaround.
- **Chemistry:** DNBSEQ (cPAS), ≥85% bases ≥Q30
- **Helicon rebrand:** **HELICON® G400** (= DNBSEQ-G400 / MGISEQ-2000). Roszdravnadzor РУ
  **2023/20825** (2023-08-16); MGI/BGI part **900-000170-00**.
- **Sources:**
  - https://www.completegenomics.com/products/sequencing-platforms/dnbseq-g400/
  - https://en.mgi-tech.com/products/reagents_info/20/ (G400 reagent sets)
  - https://genohub.com/ngs-sequencer/15/complete-genomics-dnbseq-g400/
  - https://shop.helicon.ru/catalog/equipment/science-and-analytics/sequencers/ngs/polnogenomnyy-ngs-sekvenator-helicon-g400/
  - https://www.helicon.ru/catalog/oborudovanie/sekvenirovanie/polnogenomnyy-ngs-sekvenator-mgi-2000/

| Flow cell | Read mode | Cycles | Reads/DNBs (per FC) | Output Gb (typ–max, per FC) | %Q30 | Run time | Applications | Part# (Helicon/BGI) |
|---|---|---|---|---|---|---|---|---|
| FCS | SE50 | 50 | 300–550 M | ~15–27.5 Gb | ≥85% Q30 | ~13 hr | Small RNA, gene expression, ID | reagent set: SE50 (?) |
| FCS | SE100 | 100 | 300–550 M | ~30–55 Gb | ≥85% Q30 | ~17 hr | Targeted, microbial | (?) |
| FCS | PE100 | 200 | 300–550 M | ~60–110 Gb | ≥85% Q30 | (?) | Exome, targeted | 1000013... (?) |
| FCS | PE150 | 300 | 300–550 M | ~90–165 Gb | ≥85% Q30 | up to ~96 hr | Small WGS, RNA-seq | (?) |
| FCS | PE200 | 400 | 300–550 M | ~120–180 Gb | ≥85% Q30 (?) | up to ~96 hr | Amplicon, long-insert | **1000013858** (PE200) |
| FCS | PE300 / SE400 | 600 / 400 | 300–550 M | up to ~180 Gb (FCS max) | ≥85% Q30 (?) | up to ~96 hr | Long amplicon | SE400 set **1000013857** |
| FCL | SE50 | 50 | 1500–1800 M | ~75–90 Gb | ≥85% Q30 | ~14 hr | High-plex small RNA / expression | (?) |
| FCL | SE100 | 100 | 1500–1800 M | ~150–180 Gb | ≥85% Q30 | (?) | High-throughput targeted | (?) |
| FCL | PE100 | 200 | 1500–1800 M | ~300–360 Gb | ≥85% Q30 | (?) | WES, RNA-seq | (?) |
| FCL | PE150 | 300 | 1500–1800 M | ~450–540 Gb | ≥85% (PE150 or shorter) | ~37 hr (full PE150) | WGS (≈4 per FCL), large RNA-seq | (?) |
| FCL | PE200 | 400 | 1500–1800 M | up to ~720 Gb (FCL max) | ≥85% Q30 (?) | up to ~107 hr | Long-insert WGS | **1000013858** (PE200) |

> Confirmed envelope: **whole-run output 55–1440 Gb** (both FC, varies by reagent/read/FC type;
> some sources cite up to 1080–1440 Gb per run). **FCS = 300–550 M reads/FC**, **FCL = 1500–1800 M
> reads/FC**. Per-FC max output: **FCS ≈180 Gb, FCL ≈720 Gb**. PE150 full run ~37 h.
> Read modes: SE35, SE50, SE100, PE50, PE100, PE150, PE200, PE300, SE400. **DATA GAP:** per-mode Gb
> and run-time are interpolated from reads×cycles and the published max values — confirm exact
> per-kit numbers from the MGI G400 reagent page / brochure. Helicon reagent part numbers exist per
> mode (SE50, PE100, PE200=1000013858, SE400=1000013857) — full list to be pulled from shop.helicon.ru.

---

## DNBSEQ-T1 / T1+ (T1 Plus)

- **Class:** benchtop / mid-throughput, all-in-one; PE150 in **24 h**, **Q40**
- **Flow cells / slots:** **2 flow cells** run simultaneously; **three flow cell types FCL / FCM / FCS**
  (independent read lengths/applications per cell)
- **Chemistry:** DNBSEQ (cPAS); ≥90% bases ≥Q40 for PE150 or shorter
- **Regulatory:** CE-marked (DNBSEQ-T1+, 2025)
- **Helicon rebrand:** not confirmed (?)
- **Sources:**
  - https://mgi-tech.eu/sequencing-products/dnbseq-t1
  - https://global-mgitech.com/sequencer-products-seq-all/dnbseq-t1/
  - https://en.mgitech.cn/Home/Products/instruments_info/id/73.html
  - https://genohub.com/ngs-sequencer/41/complete-genomics-dnbseq-t1+/
  - https://www.prnewswire.com/news-releases/mgi-tech-receives-ce-mark-for-dnbseq-t1-sequencer-302486875.html

| Flow cell | Read mode | Cycles | Reads/DNBs (per FC) | Output Gb (typ–max, per FC) | %Q30/Q40 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| FCS | PE150 | 300 | (?) | ~25–? Gb (FCS small) | ≥90% Q40 | ~24 hr | Targeted, panels | (?) |
| FCM | PE150 | 300 | (?) | mid range (?) | ≥90% Q40 | ~24 hr | Exome, RNA-seq | (?) |
| FCL | PE150 | 300 | (?) | up to 600 Gb | ≥90% Q40 | ~24 hr | WGS, large RNA-seq | (?) |

> Confirmed: **per-FC up to 600 Gb → 1.2 Tb whole run (2 FC)**; throughput **25–1200 Gb**; PE150
> workflow in 24 h; **≥90% bases ≥Q40 (PE150 or shorter, all FC types)**. **DATA GAP:** per-FC reads
> and the FCS/FCM intermediate output values, plus other read modes (PE100/SE etc.) and part numbers
> not confirmed in this pass — verify against the T1+ brochure.

---

## DNBSEQ-T7 / T7+ (T7 Plus)

- **Class:** high-throughput production sequencer; up to 4 flow cells
- **Flow cells / slots:** **up to 4 independent flow cells**, each loadable any time, PE100/PE150 selectable per cell
- **Chemistry:** DNBSEQ (cPAS). T7 ≈ ≥85% Q30 era; **T7+** marketed as **Q40**
- **Variants:** **DNBSEQ-T7RS** (Research/standard) and **ARS** (with onboard bioinformatics /
  HotMPS chemistry option) — analogous to G99 RS/ARS naming **(?)**. WH/SZ regional configs exist.
- **Helicon rebrand:** sold by Helicon under DNBSEQ-T7 name (no separate HELICON alias confirmed) (?)
- **Sources:**
  - https://mgi-tech.eu/sequencing-products/dnbseq-t7
  - https://mgi-tech.eu/sequencing-products/dnbseq-t7-plus
  - https://global-mgitech.com/seqall/dnbseq-t7plus/
  - https://www.completegenomics.com/products/sequencing-platforms/dnbseq-t7-plus/
  - https://genohub.com/ngs-sequencer/24/complete-genomics-dnbseq-t7/
  - https://www.witec.ch/products/ngs-sequencer/dnbseq-t7rs-genetic-sequencer-hotmps/ (T7RS / HotMPS)
  - https://www.helicon.ru/catalog/oborudovanie/sekvenirovanie/.../polnogenomnyy-ngs-sekvenator-dnbseq-t7/

### DNBSEQ-T7 (original, 2018)

| Flow cell | Read mode | Cycles | Reads/DNBs (per FC) | Output Gb (typ–max) | %Q30 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| T7 FC (×1–4) | PE100 | 200 | ≤5000 M / FC | ~1000 Gb / FC | ≥85% Q30 | ~20–24 hr | WGS, population | (?) |
| T7 FC (×1–4) | PE150 | 300 | ≤5000 M / FC | ~1500 Gb / FC | ≥85% Q30 | ~24–30 hr | WGS, transcriptome, methylation | (?) |

> Confirmed: **≤5000 M reads/FC**, **up to 24 billion reads/run** (4 FC), **up to 6–7 Tb/24 h**,
> ≈60 WGS/day, up to 20,000×30× WGS/year, PE150 in 24–30 h, 1–4 FC independent.

### DNBSEQ-T7+ (T7 Plus, 2025)

| Flow cell | Read mode | Cycles | Reads/DNBs (per FC) | Output Gb (typ–max) | %Q40 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| T7+ FC (×4) | PE75 | 150 | up to 12,000 M / FC | ~1800 Gb / FC | Q40 | ~24 hr | Counting, gene expression | (?) |
| T7+ FC (×4) | PE100 | 200 | up to 12,000 M / FC | ~2400 Gb / FC | Q40 | ~24 hr | WGS, single-cell | (?) |
| T7+ FC (×4) | PE150 | 300 | up to 12,000 M / FC | ~3600 Gb / FC | Q40 | ~24 hr | WGS, multiomics, population | (?) |

> Confirmed: **>14 Tb/day**, four high-capacity flow cells up to **12,000 M reads each**, PE75/100/150,
> whole-run output **2.4–14.4 Tb**, **Q40**, ~112 WGS / 80 scRNA-seq / 1,920 RNA-seq per run, up to
> 35,000 WGS/year, 7-in-1 modular automation. (Note: mgi-tech.eu listed "48.000 M reads per flow
> cell" on the T7+ page — likely a different metric/typo; the 12,000 M/FC and 24 B/run figures from
> the press materials are used here, marked authoritative.)

---

## DNBSEQ-T20×2 (DNBSEQ-T20)

- **Class:** ultra-high-throughput / factory-scale (population genomics, 100k–1M genomes)
- **Flow cells / slots:** 2 imagers + rotational robotic arm, **6 whole-wafer slides**; fully
  robotic fluidics. ("T20" is marketed as the **T20×2** configuration.)
- **Chemistry:** DNBSEQ (cPAS) on whole-wafer slides
- **Helicon rebrand:** not confirmed (?)
- **Sources:**
  - https://en.mgi-tech.com/products/instruments_info/33/ (→ global-mgitech.com/products/instruments_info/33/)
  - https://www.completegenomics.com/products/sequencing-platforms/dnbseq-t20x2/
  - https://genohub.com/ngs-sequencer/25/complete-genomics-dnbseq-t20x2/
  - https://info.mgiamericas.com/cg-agbt23-sub100 (sub-$100 genome)

| Flow cell | Read mode | Cycles | Reads/DNBs | Output (typ–max) | %Q30 | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|---|
| 6 slides | PE100 | 200 | (?) huge | ~? Tb / run | ≥85% Q30 (?) | (?) | WGS at scale | (?) |
| 6 slides | PE150 | 300 | (?) huge | **up to 72 Tb / run**, **~23 Tb/day effective** | ≥85% Q30 (?) | (?) | WGS, WGBS, WES, RNA-seq, single-cell, Stereo-seq | (?) |

> Confirmed: **72 Tb/run (PE150)**, **23 Tb/day effective**, ~50,000–60,000 ×30× WGS/year, cost as
> low as ~$0.99/Gb / sub-$100 genome. **DATA GAP:** per-slide reads/output and run-time per mode not
> confirmed — verify against the official T20×2 spec page.

---

## CycloneSEQ (MGI nanopore — separate technology, NOT DNBSEQ)

- **Class:** **nanopore** long-read sequencing (launched Sept 2024). *Distinct chemistry from
  DNBSEQ — single-molecule, protein nanopore, no DNB.*
- **Models:** **CycloneSEQ-WT02** (benchtop, dual flow cell) and **CycloneSEQ-WY01** (high-throughput).
- **Flow cell:** up to **4,096 nanopores per flow cell**; WT02 = dual flow cell, independent operation.
- **Read length:** bp → Mbp (true long reads).
- **Accuracy:** single-pass ~**97%**; consensus ~**99.99% (Q40)**.
- **Speed:** ~350–420 nt/s; runs **10 min – 72 h**.
- **Helicon rebrand:** not confirmed (?)
- **Sources:**
  - https://global-mgitech.com/technologies/cycloneseq-technology/
  - https://www.prnewswire.com/news-releases/mgi-launches-new-nanopore-sequencing-products-with-advanced-cycloneseq-technology-302241816.html
  - https://biopharmaapac.com/product-spotlight/66/5236/mgi-introduces-cycloneseq-wt02-and-cycloneseq-wy01-advancing-high-throughput-nanopore-sequencing.html
  - https://rrwick.github.io/2024/12/17/cycloneseq.html (independent data review)

| Flow cell | Read mode | Reads/pores | Output (typ–max) | Accuracy | Run time | Applications | Part# |
|---|---|---|---|---|---|---|---|
| WT02 single FC | long-read | ≤4,096 pores/FC | up to **50 Gb** / FC | 97% single / 99.99% consensus | 10 min–72 h | Long-read WGS, structural variants, full-length transcript | (?) |
| WT02 dual FC | long-read | 2× ≤4,096 pores | up to **100 Gb** (2 FC) | 97% single / 99.99% consensus | 10 min–72 h | Long-read WGS, de novo assembly | (?) |
| WY01 | long-read | (?) | higher (high-throughput) (?) | 97% / 99.99% (?) | (?) | Population long-read | (?) |

> Note: CycloneSEQ uses **read length / Gb**, not DNB/PE conventions. Cite separately from DNBSEQ
> platforms in the configurator. WY01 high-throughput specs not detailed in this pass.

---

## Summary of known data gaps (re-verify before tender quoting)

1. **DNBSEQ-G50 (MGISEQ-200 family):** no confirmed per-mode spec table — parse the 2025 G50
   brochure PDF directly.
2. **DNBSEQ-G99:** read modes confirmed (PE50/SE100/PE150/PE300/SE400) and run envelope (8–240 Gb,
   ≤400 M reads, PE150 ~11 h, Q40) confirmed, but **per-mode Gb/reads/run-time not broken out**.
3. **DNBSEQ-G400:** envelope confirmed (FCS 300–550 M & ≤180 Gb; FCL 1500–1800 M & ≤720 Gb; run
   55–1440 Gb); **per-mode Gb/run-time are interpolated**, and full Helicon reagent part-number list
   needs pulling from shop.helicon.ru.
4. **DNBSEQ-T1+:** per-FC (FCS/FCM/FCL) reads and intermediate outputs not confirmed.
5. **DNBSEQ-T7+:** "12,000 M/FC" vs mgi-tech.eu's "48 M/FC" discrepancy flagged.
6. **DNBSEQ-T20×2:** per-slide reads/output not confirmed.
7. **CycloneSEQ:** WY01 specs and any Helicon rebrand name not confirmed.
8. **Helicon rebrands:** only HELICON® G400 (РУ 2023/20825) is firmly confirmed; T7/G99/CycloneSEQ
   Russian aliases need confirmation on helicon.ru.
