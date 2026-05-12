-- =====================================================================
-- migration 005 — Shimadzu category re-classify
-- =====================================================================
-- После первого Shimadzu JSON-driven crawl, ~20% записей попало в 'other'
-- (Nexera-e, MSS Method Development System, Co-Sense for BA, Reducing Sugar
-- Analysis System и пр.) — потому что URL_CATEGORY_MAP не покрывал hub slug'и
-- (`hplc-system`, `liquid-chromatography`, `nexera`, `gas-chromatography`).
--
-- В commit 1273b2b мы расширили URL_CATEGORY_MAP в shimadzu.py — эта миграция
-- применяет те же правила к ужe импортированным записям без re-crawl.
-- Идемпотентна: WHERE category='other' гарантирует что мы не перезатрём
-- правильные категории.

BEGIN;

-- HPLC system / UHPLC (Nexera, MSS, etc.)
UPDATE product SET category='hplc_system'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(liquid-chromatography|/hplc-system/|/nexera|/uhplc|/lc-systems/)';

-- GC system
UPDATE product SET category='gc_system'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/gas-chromatography/|/gc-system/|/gc-systems/)';

-- Mass spectrometers (Triple Quad, Single Quad, TOF, QTOF, LC-MS, GC-MS, MALDI)
UPDATE product SET category='mass_spectrometer'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(triple-quadrupole|single-quadrupole|tof-ms|qtof|/lc-ms/|/gc-ms/|/lcms/|/gcms/|/maldi/)';

-- UV-Vis / UV-Vis-NIR spectrophotometers
UPDATE product SET category='uv_vis_spectrometer'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(uv-vis|/spectrophotometer|/molecular-spectroscopy/uv)';

-- FTIR / FTIR microscopes
UPDATE product SET category='ftir_spectrometer'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/ftir|/ftir-microscope)';

-- AAS (atomic absorption)
UPDATE product SET category='aas_system'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '/atomic-absorption';

-- ICP-MS / EDX
UPDATE product SET category='icp_ms'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/icp-ms/|/edx-fs|wavelength-dispersive-x-ray-fluorescence)';

-- ICP-OES / Optical emission
UPDATE product SET category='icp_oes'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/icp-oes/|optical-emission-spectroscopy|inductively-coupled-plasma-emission-spectroscopy)';

-- Balances
UPDATE product SET category='balance'::product_category_t, domain='general_lab'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/balances/|analytical-balance|electronic-balance|moisture-analyzer)';

-- HPLC columns (Shim-pack series + generic LC/UHPLC columns)
UPDATE product SET category='hplc_column'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/shim-pack/|/hplc-column|/lc-column|/uhplc-column|/hplc-consumables/)';

-- GC columns
UPDATE product SET category='gc_column'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/gc-column|/gc-columns/)';

-- Vials & accessories
UPDATE product SET category='vial'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '/vials';

-- Autosamplers
UPDATE product SET category='hplc_autosampler'::product_category_t, domain='analytical'::product_domain_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '/autosampler';

-- Consumables (catch-all для расходки)
UPDATE product SET category='consumable'::product_category_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND source_urls[1] ~ '(/consumables|/reagents-and-consumables)';

-- Software (LabSolutions и пр.)
UPDATE product SET category='software'::product_category_t
WHERE brand='Shimadzu' AND category='other'::product_category_t
  AND (source_urls[1] ~ '/software' OR display_name ~* 'labsolutions');

COMMIT;

-- Verify post-migration distribution
\echo ''
\echo '== Shimadzu categories after re-classify =='
SELECT category, COUNT(*) FROM product WHERE brand='Shimadzu' GROUP BY category ORDER BY 2 DESC;
