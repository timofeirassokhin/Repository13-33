-- ============================================================================
-- Phase 3 — FULL NGS sequencer seed (Illumina / MGI Tech / GeneMind / Salus + RU OEM)
-- Source: scripts/ngs_specs/*.md (researched 2026-05-20, official vendor spec sheets).
-- Idempotent: tag metadata->>'seed'='ngs_seed_v2' / notes='ngs_seed_v2'. Safe to re-run.
-- Configs + runtime metrics attach to ORIGINAL manufacturer platforms.
-- RU OEM brands (Геноскан/Helicon/БиоФьюжн) are product rows with oem_of_id -> original.
-- Uncertain values carry source_confidence < 1.0.
-- ============================================================================
\set ON_ERROR_STOP on
\set T '11111111-1111-1111-1111-111111111111'
BEGIN;

-- cleanup previous run -------------------------------------------------------
DELETE FROM sequencer_runtime_metric WHERE notes='ngs_seed_v2';
DELETE FROM product_compatibility   WHERE notes='ngs_seed_v2';
DELETE FROM product_slot            WHERE notes='ngs_seed_v2';
DELETE FROM product_configuration   WHERE metadata->>'seed'='ngs_seed_v2';
-- platforms kept (UPSERT) to preserve any FK; re-tagged below.

-- ============================================================================
-- 1. PLATFORMS (original manufacturers)
-- ============================================================================
INSERT INTO product (tenant_id, brand, model, category, domain, display_name, status, manufacturer_country, base_specs, imported_from, metadata)
VALUES
-- Illumina
(:'T','Illumina','iSeq 100','sequencer_platform','genetics_ngs','Секвенатор Illumina iSeq 100','active','US','{"class":"benchtop","fc_slots":1,"chem":"SBS-1ch"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','MiniSeq','sequencer_platform','genetics_ngs','Секвенатор Illumina MiniSeq','active','US','{"class":"benchtop","fc_slots":1,"chem":"SBS-2ch"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','MiSeq','sequencer_platform','genetics_ngs','Секвенатор Illumina MiSeq','active','US','{"class":"benchtop","fc_slots":1,"chem":"SBS-4ch"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','MiSeq i100','sequencer_platform','genetics_ngs','Секвенатор Illumina MiSeq i100','active','US','{"class":"benchtop","fc_slots":1,"chem":"XLEAP-SBS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','MiSeq i100 Plus','sequencer_platform','genetics_ngs','Секвенатор Illumina MiSeq i100 Plus','active','US','{"class":"benchtop","fc_slots":1,"chem":"XLEAP-SBS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NextSeq 550','sequencer_platform','genetics_ngs','Секвенатор Illumina NextSeq 550','active','US','{"class":"midthroughput","fc_slots":1,"chem":"SBS-2ch","family":"NextSeq 500/550"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NextSeq 1000','sequencer_platform','genetics_ngs','Секвенатор Illumina NextSeq 1000','active','US','{"class":"midthroughput","fc_slots":1,"chem":"XLEAP-SBS","kits":"P1,P2"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NextSeq 2000','sequencer_platform','genetics_ngs','Секвенатор Illumina NextSeq 2000','active','US','{"class":"highthroughput","fc_slots":1,"chem":"XLEAP-SBS","kits":"P1,P2,P3,P4"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NovaSeq 6000','sequencer_platform','genetics_ngs','Секвенатор Illumina NovaSeq 6000','active','US','{"class":"production","fc_slots":2,"chem":"SBS-2ch-v1.5"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NovaSeq X','sequencer_platform','genetics_ngs','Секвенатор Illumina NovaSeq X','active','US','{"class":"ultra","fc_slots":1,"chem":"XLEAP-SBS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Illumina','NovaSeq X Plus','sequencer_platform','genetics_ngs','Секвенатор Illumina NovaSeq X Plus','active','US','{"class":"ultra","fc_slots":2,"chem":"XLEAP-SBS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
-- MGI Tech
(:'T','MGI Tech','DNBSEQ-E25','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-E25','active','CN','{"class":"portable","fc_slots":1,"chem":"DNBSEQ"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-G50','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-G50','active','CN','{"class":"benchtop","fc_slots":1,"chem":"DNBSEQ"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-G99','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-G99','active','CN','{"class":"benchtop","fc_slots":2,"chem":"DNBSEQ","quality":"Q40"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-G400','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-G400','active','CN','{"class":"midthroughput","fc_slots":2,"chem":"DNBSEQ","fc_types":"FCL,FCS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-T1','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-T1+','active','CN','{"class":"midthroughput","fc_slots":2,"chem":"DNBSEQ","quality":"Q40","fc_types":"FCL,FCM,FCS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-T7','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-T7','active','CN','{"class":"production","fc_slots":4,"chem":"DNBSEQ"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-T7+','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-T7+ (T7 Plus)','active','CN','{"class":"production","fc_slots":4,"chem":"DNBSEQ","quality":"Q40"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','DNBSEQ-T20x2','sequencer_platform','genetics_ngs','Секвенатор MGI DNBSEQ-T20×2','active','CN','{"class":"factory","slides":6,"chem":"DNBSEQ"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','MGI Tech','CycloneSEQ-WT02','sequencer_platform','genetics_ngs','Секвенатор MGI CycloneSEQ-WT02 (нанопор)','active','CN','{"class":"nanopore","fc_slots":2,"chem":"nanopore","longread":true}','ngs_seed','{"seed":"ngs_seed_v2"}'),
-- GeneMind
(:'T','GeneMind','FASTASeq 300','sequencer_platform','genetics_ngs','Секвенатор GeneMind FASTASeq 300','active','CN','{"class":"benchtop","chem":"SURF-seq","fc_types":"FCL,FCM,FCH,FCX,FCP","pn":"SQ00020"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','GeneMind','GenoLab M','sequencer_platform','genetics_ngs','Секвенатор GeneMind GenoLab M','active','CN','{"class":"midthroughput","fc_slots":2,"chem":"SURF-seq","fc_types":"FCM,FCH"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','GeneMind','SURFSeq 5000','sequencer_platform','genetics_ngs','Секвенатор GeneMind SURFSeq 5000','active','CN','{"class":"highthroughput","fc_slots":2,"chem":"SURF-seq","fc_types":"FCM,FCH,FCP","pn":"SQ00025"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','GeneMind','SURFSeq Q','sequencer_platform','genetics_ngs','Секвенатор GeneMind SURFSeq Q','active','CN','{"class":"ultra","fc_slots":2,"chem":"SURF-seq","fc_types":"FCM,FCH","quality":"Q40","pn":"SQ00063"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','GeneMind','GenoCare 1600','sequencer_platform','genetics_ngs','Секвенатор GeneMind GenoCare 1600 (одномолекулярный)','active','CN','{"class":"single-molecule","fc_slots":1,"chem":"SURF-seq-SMS"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
-- Salus BioMed
(:'T','Salus BioMed','Salus Pro','sequencer_platform','genetics_ngs','Секвенатор Salus Pro','active','CN','{"class":"midthroughput","fc_slots":2,"chem":"SBS","cert":"CE-IVDR,NMPA"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Salus BioMed','Salus EVO','sequencer_platform','genetics_ngs','Секвенатор Salus EVO','active','CN','{"class":"highthroughput","fc_slots":2,"chem":"SBS","cert":"CE-IVDR"}','ngs_seed','{"seed":"ngs_seed_v2"}'),
(:'T','Salus BioMed','Saluseq Nimbo','sequencer_platform','genetics_ngs','Секвенатор Saluseq Nimbo','active','CN','{"class":"low","chem":"SBS"}','ngs_seed','{"seed":"ngs_seed_v2"}')
ON CONFLICT (tenant_id, brand, model) DO UPDATE
   SET category=EXCLUDED.category, domain=EXCLUDED.domain, display_name=EXCLUDED.display_name,
       base_specs=EXCLUDED.base_specs, manufacturer_country=EXCLUDED.manufacturer_country,
       metadata=product.metadata || '{"seed":"ngs_seed_v2"}', updated_at=now();

-- ============================================================================
-- 1b. RU OEM platforms (oem_of_id -> original)
-- ============================================================================
INSERT INTO product (tenant_id, brand, model, category, domain, display_name, status, manufacturer_country, oem_of_id, base_specs, ru_status, ru_number, ru_valid_from, imported_from, metadata)
SELECT :'T', o.brand, o.model, 'sequencer_platform','genetics_ngs', o.dname, 'active', o.country,
       (SELECT id FROM product WHERE tenant_id=:'T' AND brand=o.obrand AND model=o.omodel),
       '{}'::jsonb, o.ru_status::ru_status_t, o.ru_number,
       o.ru_from::date, 'ngs_seed', '{"seed":"ngs_seed_v2"}'::jsonb
FROM (VALUES
  ('Сесана','Геноскан 3700','Секвенатор Геноскан 3700 (OEM GeneMind FASTASeq 300)','RU','GeneMind','FASTASeq 300','active',NULL,NULL),
  ('Сесана','Геноскан 4000','Секвенатор Геноскан 4000 (OEM GeneMind GenoLab M)','RU','GeneMind','GenoLab M','active','РЗН 2025/24616','2025-01-31'),
  ('Сесана','Геноскан 5000','Секвенатор Геноскан 5000 (OEM GeneMind SURFSeq 5000)','RU','GeneMind','SURFSeq 5000','active',NULL,NULL),
  ('Сесана','Геноскан 6000','Секвенатор Геноскан 6000 (OEM GeneMind SURFSeq Q)','RU','GeneMind','SURFSeq Q','active',NULL,NULL),
  ('Хеликон','Helicon G400','Секвенатор Helicon G400 (OEM MGI DNBSEQ-G400)','RU','MGI Tech','DNBSEQ-G400','active','РЗН 2023/20825','2023-08-16'),
  ('БиоФьюжн','Salus Pro RS','Секвенатор Salus Pro RS (OEM Salus Pro)','RU','Salus BioMed','Salus Pro','pending',NULL,NULL),
  ('БиоФьюжн','Salus Evo RS','Секвенатор Salus Evo RS (OEM Salus EVO)','RU','Salus BioMed','Salus EVO','pending',NULL,NULL)
) AS o(brand, model, dname, country, obrand, omodel, ru_status, ru_number, ru_from)
ON CONFLICT (tenant_id, brand, model) DO UPDATE
   SET oem_of_id=EXCLUDED.oem_of_id, ru_status=EXCLUDED.ru_status, ru_number=EXCLUDED.ru_number,
       ru_valid_from=EXCLUDED.ru_valid_from, metadata=product.metadata || '{"seed":"ngs_seed_v2"}', updated_at=now();

-- ============================================================================
-- 2. KIT/FLOWCELL MATRIX (staging) -> configs + runtime metrics
-- cols: brand, platform, code, name, flowcell, read_mode, cycles, reads_m, gb_typ, gb_max, q30, q40, rt_h, apps, conf
-- reads_m = read pairs (PE) / single reads (SE) in millions. conf = source_confidence.
-- ============================================================================
CREATE TEMP TABLE seed_kit(
  brand text, platform text, code text, name text, flowcell text, read_mode text,
  cycles int, reads_m numeric, gb_typ numeric, gb_max numeric, q30 numeric, q40 numeric,
  rt_h numeric, apps text[], conf numeric);

INSERT INTO seed_kit VALUES
-- ===== Illumina iSeq 100 =====
('Illumina','iSeq 100','20031371','i1 Reagent v2 (1x75)','iSeq 100','1x75',75,4,0.3,0.3,80,NULL,11,'{targeted}',0.9),
('Illumina','iSeq 100','20031371','i1 Reagent v2 (2x150)','iSeq 100','2x150',300,4,1.2,1.2,80,NULL,19,'{amplicon,small genome}',0.95),
-- ===== MiniSeq =====
('Illumina','MiniSeq','FC-420-1004','Mid Output 300cyc','Mid Output','2x150',300,15,2.1,2.4,80,NULL,17,'{targeted,small panel}',0.95),
('Illumina','MiniSeq','FC-420-1001','High Output 75cyc','High Output','1x75',75,24,1.65,1.875,85,NULL,7,'{expression,small RNA}',0.95),
('Illumina','MiniSeq','FC-420-1002','High Output 150cyc','High Output','2x75',150,47,3.3,3.75,85,NULL,13,'{targeted,amplicon}',0.95),
('Illumina','MiniSeq','FC-420-1003','High Output 300cyc','High Output','2x150',300,47,6.6,7.5,80,NULL,24,'{small genome,exome subset}',0.95),
-- ===== MiSeq (classic) =====
('Illumina','MiSeq','MS-102-2002','Reagent Kit v2 300cyc','MiSeq v2','2x150',300,14,4.5,5.1,80,NULL,24,'{amplicon,small genome,targeted}',0.97),
('Illumina','MiSeq','MS-102-2003','Reagent Kit v2 500cyc','MiSeq v2','2x250',500,14,7.5,8.5,75,NULL,39,'{16S,amplicon}',0.97),
('Illumina','MiSeq','MS-103-1002','Reagent Micro Kit v2 300cyc','MiSeq v2 Micro','2x150',300,8,1.2,1.2,NULL,NULL,19,'{small amplicon,validation}',0.85),
('Illumina','MiSeq','MS-103-1001','Reagent Nano Kit v2 300cyc','MiSeq v2 Nano','2x150',300,2,0.3,0.3,NULL,NULL,17,'{library QC}',0.85),
('Illumina','MiSeq','MS-103-1003','Reagent Nano Kit v2 500cyc','MiSeq v2 Nano','2x250',500,2,0.5,0.5,NULL,NULL,28,'{16S pilot,QC}',0.85),
('Illumina','MiSeq','MS-102-3001','Reagent Kit v3 150cyc','MiSeq v3','2x75',150,23,3.3,3.8,85,NULL,21,'{targeted,amplicon,counting}',0.95),
('Illumina','MiSeq','MS-102-3003','Reagent Kit v3 600cyc','MiSeq v3','2x300',600,23,13.2,15,70,NULL,56,'{long amplicon,16S,ITS,metagenomics}',0.97),
-- ===== MiSeq i100 / i100 Plus =====
('Illumina','MiSeq i100','20126565','i100 5M 300cyc','5M','2x150',300,10,1.5,1.5,90,NULL,7,'{amplicon,targeted}',0.92),
('Illumina','MiSeq i100','20126566','i100 5M 600cyc','5M','2x300',600,10,3,3,85,NULL,15,'{long amplicon,16S}',0.92),
('Illumina','MiSeq i100','20126567','i100 25M 100cyc','25M','1x100',100,25,2.5,2.5,90,NULL,4,'{counting,expression}',0.92),
('Illumina','MiSeq i100','20126568','i100 25M 300cyc','25M','2x150',300,50,7.5,7.5,90,NULL,7,'{targeted,small genome,exome subset}',0.92),
('Illumina','MiSeq i100','20115696','i100 25M 600cyc','25M','2x300',600,50,15,15,85,NULL,15,'{long amplicon,metagenomics}',0.92),
('Illumina','MiSeq i100 Plus','20141596','i100 50M 300cyc','50M','2x150',300,100,15,15,90,NULL,7.5,'{exome,targeted}',0.9),
('Illumina','MiSeq i100 Plus','20141599','i100 100M 300cyc','100M','2x150',300,200,30,30,90,NULL,8,'{exome,small WGS}',0.9),
-- ===== NextSeq 500/550 =====
('Illumina','NextSeq 550','20024905','Mid Output v2.5 300cyc (2x75)','Mid Output v2.5','2x75',150,260,16.25,19.5,80,NULL,15,'{targeted,exome,RNA-Seq}',0.9),
('Illumina','NextSeq 550','20024905','Mid Output v2.5 300cyc (2x150)','Mid Output v2.5','2x150',300,260,32.5,39,75,NULL,26,'{exome,transcriptome}',0.9),
('Illumina','NextSeq 550','20024906','High Output v2.5 75cyc','High Output v2.5','1x75',75,400,25,30,80,NULL,11,'{counting,expression,small RNA}',0.8),
('Illumina','NextSeq 550','20024908','High Output v2.5 150cyc','High Output v2.5','2x75',150,800,50,60,80,NULL,18,'{exome,RNA-Seq}',0.95),
('Illumina','NextSeq 550','20024904','High Output v2.5 300cyc','High Output v2.5','2x150',300,800,100,120,75,NULL,29,'{WGS,exome,transcriptome}',0.95),
-- ===== NextSeq 1000/2000 =====
('Illumina','NextSeq 1000','20100983','P1 100cyc','P1','2x50',100,200,10,10,90,NULL,8,'{targeted,small RNA,16S}',0.92),
('Illumina','NextSeq 1000','20100982','P1 300cyc','P1','2x150',300,200,30,30,90,NULL,17,'{exome,targeted,transcriptome}',0.92),
('Illumina','NextSeq 1000','20100981','P1 600cyc','P1','2x300',600,200,60,60,85,NULL,34,'{long amplicon,metagenomics}',0.92),
('Illumina','NextSeq 2000','20100987','P2 100cyc','P2','2x50',100,800,40,40,90,NULL,12,'{counting,targeted}',0.92),
('Illumina','NextSeq 2000','20100986','P2 200cyc','P2','2x100',200,800,80,80,90,NULL,19,'{RNA-Seq,exome}',0.8),
('Illumina','NextSeq 2000','20100985','P2 300cyc','P2','2x150',300,800,120,120,90,NULL,22,'{WGS,exome,transcriptome}',0.92),
('Illumina','NextSeq 2000','20100984','P2 600cyc','P2','2x300',600,800,240,240,85,NULL,42,'{metagenomics,long amplicon}',0.92),
('Illumina','NextSeq 2000','20100988','P3 300cyc','P3','2x150',300,2400,360,360,90,NULL,40,'{WGS,transcriptome}',0.9),
('Illumina','NextSeq 2000','20100992','P4 300cyc','P4','2x150',300,3600,540,540,90,NULL,44,'{WGS,large transcriptome}',0.85),
-- ===== NovaSeq 6000 =====
('Illumina','NovaSeq 6000','20028400','SP v1.5 300cyc','SP','2x150',300,1450,200,250,85,NULL,25,'{WGS,transcriptome}',0.95),
('Illumina','NovaSeq 6000','20028402','SP v1.5 500cyc','SP','2x250',500,1450,325,400,75,NULL,38,'{long amplicon,metagenomics}',0.9),
('Illumina','NovaSeq 6000','20028317','S1 v1.5 300cyc','S1','2x150',300,2900,400,500,85,NULL,25,'{WGS,transcriptome}',0.95),
('Illumina','NovaSeq 6000','20028314','S2 v1.5 300cyc','S2','2x150',300,7400,1000,1250,85,NULL,36,'{WGS,transcriptome}',0.95),
('Illumina','NovaSeq 6000','20028312','S4 v1.5 300cyc','S4','2x150',300,18000,2400,3000,85,NULL,44,'{WGS at scale}',0.97),
-- ===== NovaSeq X / X Plus (kits run on both) =====
('Illumina','NovaSeq X','20104705','1.5B 300cyc','1.5B','2x150',300,4000,500,716,85,NULL,23,'{WGS,transcriptome}',0.92),
('Illumina','NovaSeq X','20145964','1.5B 600cyc','1.5B','2x300',600,4000,1000,1400,75,NULL,44,'{long amplicon,metagenomics}',0.9),
('Illumina','NovaSeq X Plus','20085594','10B 300cyc','10B','2x150',300,23000,3000,4000,85,NULL,25,'{population WGS}',0.95),
('Illumina','NovaSeq X Plus','20104706','25B 300cyc','25B','2x150',300,60000,8000,10500,85,NULL,48,'{population/clinical WGS}',0.92),
-- ===== MGI DNBSEQ-E25 =====
('MGI Tech','DNBSEQ-E25','MGI-E25-SE100','E25 SE100','E25','SE100',100,25,2.5,2.5,85,NULL,5,'{panels,pathogen ID}',0.75),
('MGI Tech','DNBSEQ-E25','MGI-E25-PE150','E25 PE150','E25','PE150',300,25,7.5,7.5,85,NULL,20,'{small genome,panels}',0.75),
-- ===== MGI DNBSEQ-G50 (uncertain) =====
('MGI Tech','DNBSEQ-G50','MGI-G50-PE150','G50 FCS PE150','FCS','PE150',300,75,22.5,22.5,85,NULL,NULL,'{small WGS,amplicon}',0.5),
-- ===== MGI DNBSEQ-G99 (Q40; per-mode interpolated) =====
('MGI Tech','DNBSEQ-G99','MGI-G99-PE150','G99 PE150 (per FC)','G99','PE150',300,400,100,120,NULL,90,11,'{small WGS,transcriptome,panels}',0.7),
('MGI Tech','DNBSEQ-G99','MGI-G99-SE100','G99 SE100 (per FC)','G99','SE100',100,400,40,40,NULL,90,NULL,'{expression,metagenomics}',0.6),
-- ===== MGI DNBSEQ-G400 (FCS/FCL) =====
('MGI Tech','DNBSEQ-G400','1000013858','G400 FCS PE200','FCS','PE200',400,425,120,180,85,NULL,96,'{amplicon,long-insert}',0.7),
('MGI Tech','DNBSEQ-G400','MGI-G400-FCS-PE150','G400 FCS PE150','FCS','PE150',300,425,90,165,85,NULL,96,'{small WGS,RNA-seq}',0.7),
('MGI Tech','DNBSEQ-G400','MGI-G400-FCL-PE150','G400 FCL PE150','FCL','PE150',300,1650,450,540,85,NULL,37,'{WGS,large RNA-seq}',0.8),
('MGI Tech','DNBSEQ-G400','MGI-G400-FCL-PE100','G400 FCL PE100','FCL','PE100',200,1650,300,360,85,NULL,NULL,'{WES,RNA-seq}',0.7),
('MGI Tech','DNBSEQ-G400','1000013857','G400 FCL SE400','FCL','SE400',400,1650,540,720,85,NULL,107,'{long single-end}',0.65),
-- ===== MGI DNBSEQ-T1+ (Q40) =====
('MGI Tech','DNBSEQ-T1','MGI-T1-FCL-PE150','T1+ FCL PE150 (per FC)','FCL','PE150',300,2000,600,600,NULL,90,24,'{WGS,large RNA-seq}',0.7),
-- ===== MGI DNBSEQ-T7 / T7+ =====
('MGI Tech','DNBSEQ-T7','MGI-T7-PE150','T7 PE150 (per FC)','T7 FC','PE150',300,5000,1500,1500,85,NULL,27,'{WGS,population,methylation}',0.8),
('MGI Tech','DNBSEQ-T7','MGI-T7-PE100','T7 PE100 (per FC)','T7 FC','PE100',200,5000,1000,1000,85,NULL,22,'{WGS,population}',0.8),
('MGI Tech','DNBSEQ-T7+','MGI-T7p-PE150','T7+ PE150 (per FC, Q40)','T7+ FC','PE150',300,12000,3600,3600,NULL,90,24,'{WGS,multiomics,population}',0.7),
-- ===== MGI DNBSEQ-T20x2 =====
('MGI Tech','DNBSEQ-T20x2','MGI-T20-PE150','T20×2 PE150 (whole run)','6 slides','PE150',300,NULL,NULL,72000,85,NULL,NULL,'{population WGS}',0.6),
-- ===== MGI CycloneSEQ-WT02 (nanopore) =====
('MGI Tech','CycloneSEQ-WT02','MGI-CYC-WT02','CycloneSEQ-WT02 dual FC long-read','dual FC','long-read',NULL,NULL,NULL,100,NULL,NULL,NULL,'{long-read WGS,SV,de novo}',0.7),
-- ===== GeneMind FASTASeq 300 (= Геноскан 3700) =====
('GeneMind','FASTASeq 300','S000452','FASTASeq 300 FCH PE150','FCH','PE150',300,280,84,84,90,NULL,16,'{tumor panels,tpNGS}',0.9),
('GeneMind','FASTASeq 300','S000451','FASTASeq 300 FCH PE75','FCH','PE75',150,280,42,42,90,NULL,9.5,'{NIPT,CNV-seq,small panel}',0.9),
('GeneMind','FASTASeq 300','S000455','FASTASeq 300 FCP PE150','FCP','PE150',300,500,150,150,90,NULL,24,'{WGS,large panel}',0.9),
('GeneMind','FASTASeq 300','S000277','FASTASeq 300 FCX PE300','FCX','PE300',600,100,60,60,85,NULL,48,'{16S,18S,ITS}',0.9),
('GeneMind','FASTASeq 300','S000406','FASTASeq 300 FCX SE400','FCX','SE400',400,100,40,40,80,NULL,33,'{forensics,long SE}',0.9),
('GeneMind','FASTASeq 300','S000449','FASTASeq 300 FCM PE150','FCM','PE150',300,125,37.5,37.5,90,NULL,13,'{panels,mNGS}',0.9),
-- ===== GeneMind GenoLab M (= Геноскан 4000) =====
('GeneMind','GenoLab M','GLM-FCH-PE150','GenoLab M FCH PE150','FCH','PE150',300,500,150,150,85,NULL,50,'{WES,RNA-Seq,onco panels}',0.7),
('GeneMind','GenoLab M','GLM-FCM-PE150','GenoLab M FCM PE150','FCM','PE150',300,250,75,75,85,NULL,38,'{NIPT,PGT-A,WES}',0.7),
('GeneMind','GenoLab M','GLM-FCM-SE75','GenoLab M FCM SE75','FCM','SE75',75,250,18,18,85,NULL,13,'{NIPT,CNV-seq}',0.7),
-- ===== GeneMind SURFSeq 5000 (= Геноскан 5000); output FCx2 =====
('GeneMind','SURFSeq 5000','S000369','SURFSeq 5000 FCH PE150 (FCx2)','FCH','PE150',300,2000,1200,1200,90,NULL,30,'{WGS,single-cell,mNGS}',0.9),
('GeneMind','SURFSeq 5000','S000367','SURFSeq 5000 FCH PE100 (FCx2)','FCH','PE100',200,2000,800,800,90,NULL,26,'{RNA-seq,WES}',0.9),
('GeneMind','SURFSeq 5000','S000377','SURFSeq 5000 FCP PE150 (FCx2)','FCP','PE150',300,3600,2160,2160,90,NULL,38,'{population WGS}',0.85),
('GeneMind','SURFSeq 5000','S000358','SURFSeq 5000 FCM PE150 (FCx2)','FCM','PE150',300,500,300,300,90,NULL,24,'{WES,targeted,ctDNA}',0.9),
-- ===== GeneMind SURFSeq Q (= Геноскан 6000); Q40; output FCx2 =====
('GeneMind','SURFSeq Q','S000386','SURFSeq Q FCH PE150 (FCx2)','FCH','PE150',300,46600,14000,14000,90,90,36,'{population WGS at scale}',0.85),
('GeneMind','SURFSeq Q','S000385','SURFSeq Q FCH PE100 (FCx2)','FCH','PE100',200,46600,9400,9400,90,90,29,'{RNA-seq at scale}',0.85),
('GeneMind','SURFSeq Q','S000382','SURFSeq Q FCM PE150 (FCx2)','FCM','PE150',300,23400,7000,7000,90,90,24,'{WGS,single-cell}',0.85),
-- ===== GeneMind GenoCare 1600 (single-molecule) =====
('GeneMind','GenoCare 1600','GC1600-SE','GenoCare 1600 SE','single','SE75',75,240,10,12,NULL,NULL,24,'{NIPT,targeted,clinical}',0.7),
-- ===== Salus Pro (chip x mode); output per 1 chip (x2 with 2 chips) =====
('Salus BioMed','Salus Pro','SALUS-80M-PE150','Salus Pro 80M PE150','80M','2x150',300,80,24,24,85,NULL,20,'{sWGS,metagenomics}',0.9),
('Salus BioMed','Salus Pro','SALUS-150M-PE150','Salus Pro 150M PE150','150M','2x150',300,150,45,45,85,NULL,24,'{WES,tNGS}',0.9),
('Salus BioMed','Salus Pro','SALUS-250M-PE150','Salus Pro 250M PE150','250M','2x150',300,250,75,75,85,NULL,25,'{WES,large panel}',0.9),
('Salus BioMed','Salus Pro','SALUS-500M-PE150','Salus Pro 500M PE150','500M','2x150',300,500,150,150,85,NULL,43,'{single-cell,WGS}',0.9),
('Salus BioMed','Salus Pro','SALUS-1000M-PE150','Salus Pro 1000M PE150','1000M','2x150',300,1000,300,300,85,NULL,45,'{WGS 30X}',0.85),
('Salus BioMed','Salus Pro','SALUS-500M-SE50','Salus Pro 500M SE50','500M','SE50',50,500,25,25,85,NULL,10.7,'{NIPT,CNV-seq}',0.9),
-- ===== Salus EVO (chip x mode); output 1x chip =====
('Salus BioMed','Salus EVO','EVO-1500M-PE150','Salus EVO 1500M PE150','1500M','2x150',300,1500,450,450,85,NULL,21,'{WGS,WES,single-cell}',0.9),
('Salus BioMed','Salus EVO','EVO-1500M-PE100','Salus EVO 1500M PE100','1500M','2x100',200,1500,300,300,85,NULL,15,'{RNA-seq,WES}',0.9),
('Salus BioMed','Salus EVO','EVO-3000M-PE150','Salus EVO 3000M PE150','3000M','2x150',300,3000,1000,1000,85,NULL,24,'{population WGS,spatial}',0.85),
-- ===== Saluseq Nimbo (no chip breakdown) =====
('Salus BioMed','Saluseq Nimbo','NIMBO-PE150','Saluseq Nimbo PE150','-','PE150',300,100,40,40,85,NULL,25,'{small WGS,panels}',0.5);

-- ---- 2a. configs ----
INSERT INTO product_configuration (tenant_id, product_id, config_type, configuration_code, name, specs, metadata, imported_from)
SELECT :'T', p.id, 'sequencer_kit', k.code, k.name,
       jsonb_strip_nulls(jsonb_build_object(
         'flowcell',k.flowcell,'read_mode',k.read_mode,'cycles',k.cycles,'reads_million',k.reads_m,
         'output_gb_typ',k.gb_typ,'output_gb_max',k.gb_max,'q30',k.q30,'q40',k.q40,
         'run_time_h',k.rt_h,'applications',to_jsonb(k.apps),'source_confidence',k.conf)),
       '{"seed":"ngs_seed_v2"}', 'ngs_seed'
FROM seed_kit k JOIN product p ON p.tenant_id=:'T' AND p.brand=k.brand AND p.model=k.platform;

-- ---- 2b. runtime metrics ----
INSERT INTO sequencer_runtime_metric
  (tenant_id, sequencer_id, reagent_kit_id, read_mode, cycles, is_paired_end,
   total_reads_million_typ, total_output_gb_typ, total_output_gb_max, q30_pct, q40_pct,
   run_time_hours_max, applications, notes, source_confidence)
SELECT :'T', p.id, pc.id, k.read_mode, k.cycles, (k.read_mode ILIKE 'PE%' OR k.read_mode ILIKE '2x%'),
       k.reads_m, k.gb_typ, k.gb_max, k.q30, k.q40, k.rt_h, k.apps, 'ngs_seed_v2', k.conf
FROM seed_kit k
JOIN product p ON p.tenant_id=:'T' AND p.brand=k.brand AND p.model=k.platform
JOIN product_configuration pc ON pc.product_id=p.id AND pc.configuration_code=k.code
   AND pc.metadata->>'seed'='ngs_seed_v2' AND pc.name=k.name;

-- ---- 2c. slots (flowcell) ----
INSERT INTO product_slot (product_id, slot_name, slot_role, min_count, max_count, required, notes)
SELECT id, 'flowcell','flowcell',1, coalesce((base_specs->>'fc_slots')::int,1), true, 'ngs_seed_v2'
FROM product WHERE tenant_id=:'T' AND category='sequencer_platform'
  AND metadata->>'seed'='ngs_seed_v2' AND oem_of_id IS NULL AND base_specs ? 'fc_slots';

-- ---- 2d. compatibility (kit installable_in platform) ----
INSERT INTO product_compatibility (tenant_id, a_config_id, b_product_id, compatibility_type, notes, confidence)
SELECT :'T', pc.id, pc.product_id, 'installable_in', 'ngs_seed_v2', 0.9
FROM product_configuration pc WHERE pc.metadata->>'seed'='ngs_seed_v2';

-- ---- 3. link existing gluvexlab/1c SKUs by vendor_code to our kit configs ----
UPDATE product SET category='sequencer_reagent_kit',
       metadata = coalesce(metadata,'{}'::jsonb) || jsonb_build_object('seed_linked','ngs_seed_v2','kit_code',vendor_code)
WHERE tenant_id=:'T' AND vendor_code IN (
  SELECT configuration_code FROM product_configuration WHERE metadata->>'seed'='ngs_seed_v2');

COMMIT;

-- ============================================================================
-- verify
-- ============================================================================
SELECT 'platforms_total' k, count(*) v FROM product WHERE metadata->>'seed'='ngs_seed_v2' AND category='sequencer_platform'
UNION ALL SELECT 'platforms_OEM', count(*) FROM product WHERE metadata->>'seed'='ngs_seed_v2' AND category='sequencer_platform' AND oem_of_id IS NOT NULL
UNION ALL SELECT 'kit_configs', count(*) FROM product_configuration WHERE metadata->>'seed'='ngs_seed_v2'
UNION ALL SELECT 'runtime_metrics', count(*) FROM sequencer_runtime_metric WHERE notes='ngs_seed_v2'
UNION ALL SELECT 'slots', count(*) FROM product_slot WHERE notes='ngs_seed_v2'
UNION ALL SELECT 'compat', count(*) FROM product_compatibility WHERE notes='ngs_seed_v2'
UNION ALL SELECT 'linked_skus', count(*) FROM product WHERE metadata->>'seed_linked'='ngs_seed_v2';
