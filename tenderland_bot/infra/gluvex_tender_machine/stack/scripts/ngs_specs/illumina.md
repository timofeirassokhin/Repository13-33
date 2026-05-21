# Illumina NGS Sequencers — Specification Matrix

> Reference matrix for the Gluvex product configurator. All figures are from official
> illumina.com specification / reagent-kit pages and illumina.com Knowledge catalog-number
> articles unless otherwise noted. Values marked **(?)** are uncertain or conflicting between
> sources and must be re-verified before quoting in a tender.
>
> Conventions:
> - **Reads (M)** = clusters/reads passing filter, in millions. For paired-end (PE) modes Illumina
>   counts read *pairs*; e.g. "8M PE" on iSeq = 8M pairs = 16M total single reads. Unless noted, the
>   number is **read pairs** for PE modes and **single reads** for SE (1×) modes.
> - **Output Gb** = typical–max range per run (single flow cell).
> - **%Q30** = Illumina spec, % of bases ≥ Q30 (≥ or > as stated by Illumina).
> - Run times are approximate, on-instrument sequencing time only.
>
> Last researched: 2026-05-20.

---

## iSeq 100

- **Class:** benchtop / lowest-throughput (CMOS, 1 flow cell)
- **Chemistry:** SBS, one-channel; single integrated cartridge + flow cell
- **Flow cells / slots:** 1 flow cell per run
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/iseq/specifications.html
  - https://knowledge.illumina.com/instrumentation/iseq-100/instrumentation-iseq-100-reference_material-list/000002119
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/iseq-reagents.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| iSeq 100 | i1 Reagent v2, 300-cyc (20031371; 4-pk 20031374; 8-pk 20040760) | 1×36 | 36 | 4 (SE) | 0.144 Gb | >85% | 9.5 hr | Small panels, QC, sample ID |
| iSeq 100 | i1 Reagent v2 (same kit) | 1×50 | 50 | 4 (SE) | 0.2 Gb | >85% | 10 hr | 16S, small targeted |
| iSeq 100 | i1 Reagent v2 (same kit) | 1×75 | 75 | 4 (SE) | 0.3 Gb | >80% | 11 hr | Targeted seq |
| iSeq 100 | i1 Reagent v2 (same kit) | 2×75 | 150 | 4 (PE pairs) | 0.6 Gb | >80% | 14 hr | Small genomes, amplicon |
| iSeq 100 | i1 Reagent v2 (same kit) | 2×150 | 300 | 4 (PE pairs) | 1.2 Gb | >80% | 19 hr | Small genome / amplicon |

> Note: the single i1 v2 300-cycle cartridge runs all read modes above (cycles are user-configured).
> ~8M reads PF total = ~4M pairs in PE modes. Cluster density 174–200 k/mm².

---

## MiniSeq

- **Class:** benchtop / low-throughput (1 flow cell)
- **Chemistry:** SBS, two-channel; integrated reagent cartridge + flow cell
- **Flow cells / slots:** 1 flow cell per run
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/miniseq/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/miniseq-reagent-kit.html
  - https://support.illumina.com/sequencing/sequencing_instruments/miniseq/kit_contents.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| MiniSeq Mid Output | Mid Output Kit 300-cyc (FC-420-1004) | 2×150 | 300 | 14–16 (PE pairs) | 2.1–2.4 Gb | >80% | ~17 hr | Targeted DNA/RNA, small panels |
| MiniSeq High Output | High Output Kit 75-cyc (FC-420-1001) | 1×75 | 75 | 22–25 (SE) | 1.65–1.875 Gb | >85% | 7 hr | Gene expression, small RNA, counting |
| MiniSeq High Output | High Output Kit 150-cyc (FC-420-1002) | 2×75 | 150 | 44–50 (PE pairs) | 3.3–3.75 Gb | >85% | 13 hr | Targeted, amplicon |
| MiniSeq High Output | High Output Kit 300-cyc (FC-420-1003) | 2×150 | 300 | 44–50 (PE pairs) | 6.6–7.5 Gb | >80% | ~24 hr | Small genome, exome subset |

---

## MiSeq (classic)

- **Class:** benchtop / long-read amplicon specialist (1 flow cell)
- **Chemistry:** SBS, four-channel; reagent cartridge + flow cell + PR2 buffer
- **Flow cells / slots:** 1 flow cell per run
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/miseq/specifications.html
  - https://knowledge.illumina.com/instrumentation/miseq/instrumentation-miseq-reference_material-list/000005842
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/miseq-reagent-kit-v2.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/miseq-reagent-kit-v3.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| MiSeq v2 | Reagent Kit v2 300-cyc (MS-102-2002) | 2×150 | 300 | 12–15 (PE pairs) | 4.5–5.1 Gb | >80% | ~24 hr | Amplicon, small genome, targeted |
| MiSeq v2 | Reagent Kit v2 500-cyc (MS-102-2003) | 2×250 | 500 | 12–15 (PE pairs) | 7.5–8.5 Gb | >75% | ~39 hr | 16S, amplicon, small genome |
| MiSeq v2 | Reagent Kit v2 (MS-102-2002) | 2×25 | 50 | 12–15 (PE pairs) | 0.75–0.85 Gb | >90% | ~5.5 hr | Counting, QC |
| MiSeq v2 | Reagent Kit v2 (MS-102-2002) | 1×36 | 36 | 12–15 (SE) | 0.54–0.61 Gb | (?) | (?) | QC / small counting |
| MiSeq v2 Micro | Reagent Micro Kit v2 300-cyc (MS-103-1002) | 2×150 | 300 | 8 (PE pairs) | 1.2 Gb | (?) | ~19 hr | Small amplicon, validation |
| MiSeq v2 Nano | Reagent Nano Kit v2 300-cyc (MS-103-1001) | 2×150 | 300 | 2 (PE pairs) | 0.3 Gb | (?) | ~17 hr | Library QC, very small panels |
| MiSeq v2 Nano | Reagent Nano Kit v2 500-cyc (MS-103-1003) | 2×250 | 500 | 2 (PE pairs) | 0.5 Gb | (?) | ~28 hr | 16S pilot, library QC |
| MiSeq v3 | Reagent Kit v3 150-cyc (MS-102-3001) | 2×75 | 150 | 22–25 (PE pairs) | 3.3–3.8 Gb | >85% | ~21 hr | Targeted, amplicon, counting |
| MiSeq v3 | Reagent Kit v3 600-cyc (MS-102-3003) | 2×300 | 600 | 22–25 (PE pairs) | 13.2–15 Gb | >70% | ~56 hr | Long amplicon (16S/ITS), metagenomics |

---

## MiSeq i100 / MiSeq i100 Plus  (2024/2025 generation)

- **Class:** benchtop / next-gen MiSeq replacement (1 flow cell)
- **Chemistry:** XLEAP-SBS; room-temperature-stable reagents; integrated cartridge + flow cell
- **Flow cells / slots:** 1 flow cell per run. 5M & 25M run on **both** i100 and i100 Plus; **50M & 100M = i100 Plus only** (require i100 Series Software v1.1.0+)
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/miseq-i100/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/miseq-i100-series-reagent-kits.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| 5M | i100 5M 300-cyc (20126565) | 2×150 | 300 | 10 (PE pairs) | 1.5 Gb | ≥90% | ~7 hr | Amplicon, targeted, small panel |
| 5M | i100 5M 600-cyc (20126566) | 2×300 | 600 | 10 (PE pairs) | 3 Gb | ≥85% | ~15 hr | Long amplicon, 16S/ITS |
| 25M | i100 25M 100-cyc (20126567) | 1×100 | 100 | 25 (SE) | 2.5 Gb | ≥90% | ~4 hr | Counting, gene expression |
| 25M | i100 25M 300-cyc (20126568) | 2×150 | 300 | 50 (PE pairs) | 7.5 Gb | ≥90% | ~7 hr | Targeted, small genome, exome subset |
| 25M | i100 25M 600-cyc (20115696) | 2×300 | 600 | 50 (PE pairs) | 15 Gb | ≥85% | ~15 hr | Long amplicon, metagenomics |
| 25M | i100 25M 1000-cyc (20148254) | 2×500 | 1000 | 50 (PE pairs) | 25 Gb | ≥85% | ~24 hr | Ultra-long amplicon (?) |
| 50M | i100 50M 100-cyc (20141595) | 1×100 | 100 | 50 (SE) | 5 Gb | ≥90% | ~4.5 hr | Counting, expression (Plus only) |
| 50M | i100 50M 300-cyc (20141596) | 2×150 | 300 | 100 (PE pairs) | 15 Gb | ≥90% | ~7.5 hr | Exome, targeted (Plus only) |
| 50M | i100 50M 600-cyc (20141597) | 2×300 | 600 | 100 (PE pairs) (?) | 30 Gb (?) | ≥85% (?) | (?) | Long amplicon (Plus only) |
| 100M | i100 100M 100-cyc (20141598) | 1×100 | 100 | 100 (SE) (?) | 10 Gb (?) | ≥90% (?) | (?) | Counting (Plus only) |
| 100M | i100 100M 300-cyc (20141599) | 2×150 | 300 | 200 (PE pairs) | 30 Gb | ≥90% | ~8 hr | Exome / small WGS (Plus only) |

> Note: the spec page exposed 5M/25M/50M-150/100M-150 performance directly; 50M-600 and 100M-100
> rows are inferred from cartridge cycle naming and read-count scaling — verify before quoting.

---

## NextSeq 500 / 550

- **Class:** mid-throughput (1 patterned-free flow cell; 550 adds array scanning)
- **Chemistry:** SBS, two-channel; reagent cartridge + buffer cartridge + flow cell (sold as one kit)
- **Flow cells / slots:** 1 flow cell per run
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/nextseq/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/nextseq-series-kits-v2-5.html
  - https://knowledge.illumina.com/instrumentation/nextseq-500-550/instrumentation-nextseq-500-550-reference_material-list/000001975

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| Mid Output v2.5 | Mid Output Kit v2.5 300-cyc (20024905) | 2×75 | 150 | ≤260 (PE pairs) | 16.25–19.5 Gb | >80% | 15 hr | Targeted, exome, RNA-Seq |
| Mid Output v2.5 | Mid Output Kit v2.5 300-cyc (20024905) | 2×150 | 300 | ≤260 (PE pairs) | 32.5–39 Gb | >75% | 26 hr | Exome, transcriptome |
| High Output v2.5 | High Output Kit v2.5 75-cyc (20024906) | 1×75 | 75 | ≤400 (SE) | ~25–30 Gb (?) | >80% (?) | ~11 hr | Counting, expression, small RNA |
| High Output v2.5 | High Output Kit v2.5 150-cyc (20024908) | 2×75 | 150 | ≤800 (PE pairs) | 50–60 Gb | >80% | 18 hr | Exome, RNA-Seq |
| High Output v2.5 | High Output Kit v2.5 300-cyc (20024904) | 2×150 | 300 | ≤800 (PE pairs) | 100–120 Gb | >75% | 29 hr | WGS (human), exome, transcriptome |

> Note: part-number search returned both 20024907 and 20024906 for "High Output 75-cyc" across
> resellers — **20024906** appears on the official v2.5 reseller listing; the 75-cyc output figure
> (~25–30 Gb) is inferred and marked (?). Mid Output max is ~260M PE; High Output max ~800M PE.

---

## NextSeq 1000 / NextSeq 2000

- **Class:** mid-/high-throughput benchtop (1 flow cell)
- **Chemistry:** XLEAP-SBS (current); patterned flow cell
- **Flow cells / slots:** 1 flow cell per run. **P1 & P2** run on both 1000 and 2000; **P3 & P4 = NextSeq 2000 only**
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/nextseq-1000-2000/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/nextseq-1000-2000-reagents.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| P1 (1000/2000) | P1 100-cyc (20100983) | 2×50 | 100 | 200 (PE pairs) | 10 Gb | ≥90% | 8 hr | Targeted, small RNA, 16S |
| P1 | P1 300-cyc (20100982) | 2×150 | 300 | 200 (PE pairs) | 30 Gb | ≥90% | 17 hr | Exome, targeted, transcriptome |
| P1 | P1 600-cyc (20100981) | 2×300 | 600 | 200 (PE pairs) | 60 Gb | ≥85% | 34 hr | Long amplicon, metagenomics |
| P2 (1000/2000) | P2 100-cyc (20100987) | 2×50 | 100 | 800 (PE pairs) | 40 Gb | ≥90% | 12 hr | Counting, targeted |
| P2 | P2 200-cyc (20100986) (?) | 2×100 | 200 | 800 (PE pairs) | 80 Gb | ≥90% | 19 hr | RNA-Seq, exome |
| P2 | P2 300-cyc (20100985) | 2×150 | 300 | 800 (PE pairs) | 120 Gb | ≥90% | 22 hr | WGS, exome, transcriptome |
| P2 | P2 600-cyc (20100984) | 2×300 | 600 | 800 (PE pairs) | 240 Gb | ≥85% | 42 hr | Metagenomics, long amplicon |
| P3 (2000 only) | P3 100-cyc (20100990) | 2×50 | 100 | 2,400 (PE pairs) | 120 Gb | ≥90% | 18 hr | Single-cell, counting |
| P3 | P3 200-cyc (20100989) (?) | 2×100 | 200 | 2,400 (PE pairs) | 240 Gb | ≥90% | 31 hr | RNA-Seq, exome |
| P3 | P3 300-cyc (20100988) | 2×150 | 300 | 2,400 (PE pairs) | 360 Gb | ≥90% | 40 hr | WGS, transcriptome |
| P4 (2000 only) | P4 50-cyc (20100995) | (1×50/2×25) | 50 | 3,600 (PE pairs) | ~90 Gb (?) | ≥90% (?) | (?) | Single-cell, counting |
| P4 | P4 100-cyc (20100994) | 2×50 | 100 | 3,600 (PE pairs) | 180 Gb | ≥90% | 20 hr | High-plex single-cell |
| P4 | P4 200-cyc (20100993) | 2×100 | 200 | 3,600 (PE pairs) | 360 Gb | ≥90% | 34 hr | RNA-Seq at scale |
| P4 | P4 300-cyc (20100992) | 2×150 | 300 | 3,600 (PE pairs) | 540 Gb | ≥90% | 44 hr | WGS, large transcriptome |

> Note: a search result swapped P2-200 (20100986) and P3-200 (20100989); the product page values
> used here are considered authoritative but both rows are flagged (?). P4-50 output/run-time
> inferred. The earlier (pre-XLEAP) "standard SBS" kits had different part numbers and slightly
> lower Q30 — these rows reflect the current XLEAP-SBS line.

---

## NovaSeq 6000

- **Class:** high-throughput production (up to 2 flow cells per run, independent)
- **Chemistry:** SBS, two-channel; v1.5 reagents (patterned flow cells)
- **Flow cells / slots:** 2 flow-cell positions (each FC runs independently)
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/novaseq/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/novaseq-reagent-kits.html
  - https://knowledge.illumina.com/instrumentation/novaseq-6000/instrumentation-novaseq-6000-reference_material-list/000003525

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (M / B) | Output Gb (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| SP | SP Kit v1.5 300-cyc (20028400) | 2×50 | 100 | 1.3–1.6B (PE pairs) | 65–80 Gb | ≥90% | ~13 hr (?) | Counting, single-cell |
| SP | SP Kit v1.5 300-cyc (20028400) | 2×100 | 200 | 1.3–1.6B (PE pairs) | 134–167 Gb | ≥85% | ~19 hr (?) | RNA-Seq, exome |
| SP | SP Kit v1.5 300-cyc (20028400) | 2×150 | 300 | 1.3–1.6B (PE pairs) | 200–250 Gb | ≥85% | ~25 hr | WGS, transcriptome |
| SP | SP Kit v1.5 500-cyc (20028402) | 2×250 | 500 | 1.3–1.6B (PE pairs) | 325–400 Gb | ≥75% | ~38 hr | Long amplicon, metagenomics |
| S1 | S1 Kit v1.5 200-cyc (20028318 (?)) | 2×50 | 100 | 2.6–3.2B (PE pairs) | 134–167 Gb | ≥90% | ~13 hr | Single-cell, counting |
| S1 | S1 Kit v1.5 200-cyc (20028318 (?)) | 2×100 | 200 | 2.6–3.2B (PE pairs) | 266–333 Gb | ≥85% | ~19 hr | RNA-Seq, exome |
| S1 | S1 Kit v1.5 300-cyc (20028317) | 2×150 | 300 | 2.6–3.2B (PE pairs) | 400–500 Gb | ≥85% | ~25 hr | WGS, transcriptome |
| S2 | S2 Kit v1.5 100/200-cyc (20028316 (?)) | 2×50 | 100 | 6.6–8.2B (PE pairs) | 333–417 Gb | ≥90% | ~16 hr | Single-cell at scale |
| S2 | S2 Kit v1.5 200-cyc (20028315 (?)) | 2×100 | 200 | 6.6–8.2B (PE pairs) | 667–833 Gb | ≥85% | ~25 hr | RNA-Seq, exome |
| S2 | S2 Kit v1.5 300-cyc (20028314) | 2×150 | 300 | 6.6–8.2B (PE pairs) | 1000–1250 Gb | ≥85% | ~36 hr | WGS, transcriptome |
| S4 | S4 Kit v1.5 (200-cyc 20028313 (?)) | 2×100 | 200 | 16–20B (PE pairs) | 1600–2000 Gb | ≥85% | ~28 hr | Population WGS |
| S4 | S4 Kit v1.5 300-cyc (20028312) | 2×150 | 300 | 16–20B (PE pairs) | 2400–3000 Gb | ≥85% | ~44 hr | WGS at scale |
| S4 | S4 Kit v1.5 (35-cyc / Xp) | 1×35 | 35 | 8–10B (SE) | 280–350 Gb | ≥90% | ~13 hr (?) | Counting / single-cell |

> Note: only the **300-cycle** part numbers were text-confirmed (SP 20028400, SP-500 20028402,
> S1 20028317, S2 20028314, S4 20028312). The 100/200-cycle kit numbers (20028313–20028318 range)
> are inferred from the catalog sequence and marked (?). The NovaSeq 6000 v1.5 catalog table on
> the Knowledge page is published as an image and was not text-extractable. Reads are read *pairs*
> in billions; run times approximate.

---

## NovaSeq X / NovaSeq X Plus

- **Class:** ultra-high-throughput production. **NovaSeq X = 1 flow cell**; **NovaSeq X Plus = 2 flow cells** (independent dual-FC)
- **Chemistry:** XLEAP-SBS; patterned flow cells; on-board DRAGEN secondary analysis
- **Flow cells / slots:** X = 1 FC slot; X Plus = 2 FC slots
- **Sources:**
  - https://www.illumina.com/systems/sequencing-platforms/novaseq-x-plus/specifications.html
  - https://www.illumina.com/products/by-type/sequencing-kits/cluster-gen-sequencing-reagents/novaseq-x-series-reagent-kits.html

| Flow cell | Reagent kit (part#) | Read mode | Cycles | Reads (B) | Output (typ–max) | %Q30 | Run time | Applications |
|---|---|---|---|---|---|---|---|---|
| 1.5B (2-lane) | 1.5B 100-cyc (20104703) | 2×50 | 100 | 3.2–4.8B (PE pairs) | 165–238 Gb | ≥90% | ~17 hr | Single-cell, counting |
| 1.5B | 1.5B 200-cyc (20104704) | 2×100 | 200 | 3.2–4.8B (PE pairs) | 330–476 Gb | ≥85% | ~20 hr | RNA-Seq, exome |
| 1.5B | 1.5B 300-cyc (20104705) | 2×150 | 300 | 3.2–4.8B (PE pairs) | 500–716 Gb | ≥85% | ~23 hr | WGS, transcriptome |
| 1.5B | 1.5B 600-cyc (20145964) | 2×300 | 600 | 3.2–4.8B (PE pairs) | 1.0–1.4 Tb | ≥75% | ~44 hr | Long amplicon, metagenomics |
| 10B (8-lane) | 10B 100-cyc (20085596) | 2×50 | 100 | 20–26B (PE pairs) | 1.0–1.3 Tb | ≥90% | ~18 hr | Single-cell at scale |
| 10B | 10B 200-cyc (20085595) | 2×100 | 200 | 20–26B (PE pairs) | 2.0–2.7 Tb | ≥85% | ~22 hr | RNA-Seq, exome at scale |
| 10B | 10B 300-cyc (20085594) | 2×150 | 300 | 20–26B (PE pairs) | 3.0–4.0 Tb | ≥85% | ~25 hr | Population WGS |
| 25B (8-lane) | 25B 100-cyc (20125967) | 2×50 | 100 | 52–70B (PE pairs) | 2.6–3.5 Tb | ≥90% | ~25 hr | Mega single-cell |
| 25B | 25B 200-cyc (20125968) | 2×100 | 200 | 52–70B (PE pairs) | 5.3–7.0 Tb | ≥85% | ~38 hr | RNA-Seq at scale |
| 25B | 25B 300-cyc (20104706) | 2×150 | 300 | 52–70B (PE pairs) | 8.0–10.5 Tb | ≥85% | ~48 hr | Population / clinical WGS |

> Note: all flow cells (1.5B / 10B / 25B) and kits run on **both** NovaSeq X and X Plus; X Plus
> can run two flow cells simultaneously (double the per-run totals above). Reads are read *pairs*.
> A 2×300 / 600-cyc kit currently exists for 1.5B; 600-cyc for 10B/25B not confirmed in spec page.

---

## Cross-platform quick reference (max output per single flow cell)

| Platform | Top flow cell | Max output | Max reads/run |
|---|---|---|---|
| iSeq 100 | i1 v2 | 1.2 Gb | ~4M pairs |
| MiniSeq | High Output 300 | 7.5 Gb | ~50M pairs |
| MiSeq (classic) | v3 600-cyc | 15 Gb | ~25M pairs |
| MiSeq i100 Plus | 100M 300-cyc | 30 Gb | 200M pairs |
| NextSeq 500/550 | High Output 300 | 120 Gb | ~800M pairs |
| NextSeq 1000/2000 | P4 300-cyc | 540 Gb | 3.6B pairs |
| NovaSeq 6000 | S4 300-cyc | 3000 Gb (3 Tb) | 16–20B pairs |
| NovaSeq X / X Plus | 25B 300-cyc | 10.5 Tb (×2 on X Plus) | 52–70B pairs |
