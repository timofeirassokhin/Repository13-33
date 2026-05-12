-- =====================================================================
-- migration 004 — добор мелких категорий
-- =====================================================================
-- После 003 осталось 369 товаров в 'other'. Здесь подтягиваем критичные:
--   • HPLC модули (для slot-based config: автосемплеры + детекторы)
--   • mass spectrometers
--   • мешалки (магнитные, многоместные)
--   • остальная мелочёвка → accessory

BEGIN;

-- 1. HPLC модули — критично для slot-based конфигурации
UPDATE product SET category = 'hplc_autosampler', domain = 'analytical', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' IN ('moduli-avtosamplerov-dlya-vegch', 'avtosamplery');

UPDATE product SET category = 'hplc_detector', domain = 'analytical', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' = 'moduli-detektorov-dlya-vegch';

-- 2. Mass spectrometers (упустил exact slug)
UPDATE product SET category = 'mass_spectrometer', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' = 'mass-spektrometry';

-- 3. Мешалки (магнитные, многоместные, с подогревом)
UPDATE product SET category = 'shaker_vortex', domain = 'general_lab', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'magnitnye-meshalki',
  'mnogomestnye-meshalki',
  'odnomestnye-meshalki',
  'meshalki-1',
  'meshalki-dlya-kultivirovaniya-i-mikroplanshet',
  'meshalki-s-nagrevom-i-mnogomestnye-nagrevateli',
  'promyshlennye-meshalki-dlya-bolshich-obemov'
);

-- 4. Климатические камеры (опечатки)
UPDATE product SET category = 'climate_chamber', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'klimaticheskie_kamery',
  'laboratornye-cholodilniki',
  'farmacevticheskie-cholodilniki'
);

-- 5. Лабораторные весы
UPDATE product SET category = 'balance', domain = 'general_lab'
WHERE category = 'other' AND metadata->>'category_slug' = 'laboratornye-vesy';

-- 6. Автоклавы — в general lab как accessory (нет своей категории сейчас)
UPDATE product SET category = 'accessory', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' IN ('avtoklavy', 'avtoklavy-1');

-- 7. Тестеры растворения (от SOTAX) — фарма, в accessory с подкатегорией
UPDATE product SET category = 'accessory', domain = 'pharmaceutical', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' = 'tester_rastvoreniya';

-- 8. Ротационные испарители
UPDATE product SET category = 'accessory', domain = 'general_lab', subcategory = metadata->>'category_slug'
WHERE category = 'other' AND metadata->>'category_slug' IN ('rotatsionnye_ispariteli_1');

-- 9. Вакуумные системы
UPDATE product SET category = 'accessory'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'vakuumnye-otkachnye-sistemy', 'vakuumnoe-oborudovanie'
);

-- 10. Системы фильтрации/манифолды
UPDATE product SET category = 'accessory', domain = 'analytical'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'sistemy-dlya-filtracii-i-manifoldy', 'filtraciya'
);

-- 11. ПЦР пластик
UPDATE product SET category = 'consumable', domain = 'molecular_diagnostics'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'plastikovye-probirki-pcr', 'centrifugnye-probirki-pcr', 'reakcionnye-sosudy'
);

-- 12. Изоляторы, мебель промышленная и пр. → accessory
UPDATE product SET category = 'accessory'
WHERE category = 'other' AND metadata->>'category_slug' IN (
  'izolyatory', 'oborudovanie-dlya-promyshlennosti', 'laboratorno-promyshlennye'
);

-- 13. Микробио
UPDATE product SET category = 'consumable', domain = 'life_science_general'
WHERE category = 'other' AND metadata->>'category_slug' = 'mikrobiologicheskiy-analiz-i-kontrol';

COMMIT;
