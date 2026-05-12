-- =====================================================================
-- migration 003 — расширение GLUVEX_CATEGORY_MAP по реальным slug'ам
-- =====================================================================
-- После первого crawl 53k товаров — 98% попало в 'other'. Здесь — UPDATE
-- по реальным slug'ам (без re-crawl), сразу классифицируем.
--
-- Источник: топ-50 slug'ов из SELECT metadata->>'category_slug' GROUP BY.
-- Идемпотентно: WHERE category='other' гарантирует что не перезатрём правильные.

BEGIN;

-- 1. Запчасти (32 613 = 62% всех "other"!)
UPDATE product SET category = 'spare_part', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' = 'spare-parts';

-- 2. Колонки хроматографии (опечатки в моём mapping)
UPDATE product SET category = 'hplc_column', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'kolonki-dlya-vezhkh';

UPDATE product SET category = 'gc_column', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'kolonki-dlya-gkh';

-- 3. Фильтры (шприцевые + мембранные)
UPDATE product SET category = 'syringe_filter'
WHERE category = 'other' AND metadata->>'category_slug' LIKE 'shpricevye-filtry%';

UPDATE product SET category = 'syringe_filter'
WHERE category = 'other' AND metadata->>'category_slug' LIKE 'membrannye-filtry%';

UPDATE product SET category = 'syringe_filter'
WHERE category = 'other' AND metadata->>'category_slug' = 'membrannye-laboratornye-filtry';

-- 4. Стеклянная и пластиковая посуда -> consumable
UPDATE product SET category = 'consumable'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'kolby', 'stakany-chimicheskie', 'cilindry', 'voronki', 'byuretki',
  'chashki-petri', 'eksikatory', 'probki-dlya-butylok-i-kolb',
  'butylochnye-kryshki', 'konteynery-dlya-stekla', 'stekla-dlya-mikroskopa',
  'plastikovye-pipetki'
);

-- 5. Виалы и аксессуары
UPDATE product SET category = 'vial'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'vialy_i_kryshki', 'vstavki_v_vialy', 'kryshki-dlya-vial'
);

-- 6. Дозаторы и наконечники
UPDATE product SET category = 'consumable'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'dozatory', 'nakonechniki-k-dozatoram'
);

-- 7. Микропланшеты, ПЦР пластик
UPDATE product SET category = 'consumable'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'mikroplanshety', 'planshety-dlya-pcr'
);

-- 8. Весы
UPDATE product SET category = 'balance', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'precizionnye-vesy', 'vesovoe-oborudovanie'
);

-- 9. Сушильные шкафы (с подчёркиванием)
UPDATE product SET category = 'drying_oven', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' = 'sushilnye_shkafy';

-- 10. Боксы и вытяжные шкафы
UPDATE product SET category = 'biological_safety_cabinet', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' = 'boksy_biologicheskoy_bezopasnosti';

UPDATE product SET category = 'laminar_hood', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' IN ('shkafy_vytyazhnye', 'shkafy_dlya_khraneniya');

-- 11. Термоконтроль (охладители, морозильники)
UPDATE product SET category = 'climate_chamber', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'tsirkulyatsionnye_okhladiteli_unichiller',
  'dinamicheskie_sistemy_temperaturnogo_kontrolya',
  'laboratornye-morozilniki'
);

-- 12. Водяные бани
UPDATE product SET category = 'drying_oven', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' = 'bani';

-- 13. Гомогенизаторы и УЗ-ванны
UPDATE product SET category = 'shaker_vortex', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'gomogenizatory', 'ultrazvukovye-vanny'
);

-- 14. Насосы
UPDATE product SET category = 'accessory'
WHERE category = 'other' AND metadata->>'category_slug' = 'membrannye-nasosy';

-- 15. Фитинги, аксессуары
UPDATE product SET category = 'accessory'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'fitingi', 'dopolnitelnye_prinadlezhnosti',
  'aksessuary-k-rotacionnym-isparitelyam',
  'raschodnye-materialy-dlya-sistem-vodopodgotovki-i-chraneniya-vody'
);

-- 16. TLC
UPDATE product SET category = 'accessory', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'instrumentalnaya-tonkosloynaya-chromatografiya';

-- 17. Клеточные культуры
UPDATE product SET category = 'consumable', domain = 'life_science_general'
WHERE category = 'other' AND metadata->>'category_slug' = 'kletochnye-kultury';

-- 18. Системы фильтрации
UPDATE product SET category = 'accessory', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'sistemy-filtracii-cross-flow';

-- 19. Стандартные образцы
UPDATE product SET category = 'consumable', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'standartnyy-obrazcy-ooo-ncso';

-- 20. Мебель и аксессуары
UPDATE product SET category = 'accessory'
WHERE category = 'other' AND metadata->>'category_slug' IN ('stoly', 'vzryvobezopasnye');

COMMIT;
