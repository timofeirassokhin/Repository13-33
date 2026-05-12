# Gluvex Catalog Crawler — handoff в новую сессию

**Дата:** 2026-05-12
**Завершено в чате:** Phase 3 (инфраструктура) + Phase 4 (каталог + 12 vendor adapters + Memmert brochures)
**Branch:** `claude/nostalgic-bose-03e0b8` (PR #6)
**Последний коммит:** `20901fb` (плюс этот handoff)

> Прочитай в строгом порядке:
> 1. этот файл — **что готово / что в работе / что приоритетно**
> 2. `tenderland_bot/docs/system-state.md` — operational reference (URL, контейнеры, БД)
> 3. `tenderland_bot/docs/master-data-architecture.md` — кто master, контуры
> 4. `tenderland_bot/docs/catalog-architecture.md` — модель данных каталога

---

## TL;DR — текущее состояние

```
Сервер:       45.66.117.251 (gluvex.com)
Стек:         12 контейнеров healthy
БД gluvex_documents:  39,859 продуктов
  ├─ Gluvex (с сайта gluvexlab.com):  39,395
  └─ Vendor crawls (12 источников):       464
В MinIO:       455 PDF/markdown в product-brochures/memmert/
              + сотни в других brand bucket'ах
IPRoyal:      5GB residential proxy, ~0.1 GB израсходовано
```

### 12 vendor adapters — состояние

| Brand | Records | Datasheets | Статус | Доработка |
|---|---|---|---|---|
| Sartorius | 160 | 160 PDF | ✅ done | — |
| Sciex | 116 | 115 PDF | ✅ done | — |
| BANDELIN | 51 | 47 md | ✅ done (через proxy) | — |
| Metrohm | 38 | 38 PDF | ✅ done | — |
| Huber | 31 | 30 md | ✅ done (через proxy) | — |
| Bruker | 24 | 24 PDF | ✅ done | — |
| Memmert | 20 + 435 PDF | 20 md + 435 PDF (не matched) | 🟡 PDF собраны, не linked | matching по filename pattern |
| Heidolph | 7 | 7 md | 🟡 partial | BFS не идёт на model-level |
| Shimadzu | 6 | 6 md | ✅ done | — |
| Thermo Fisher | 6 | 6 md | ✅ done | — |
| SOTAX | 4 | 4 md | 🟡 partial | мало product pages на сайте |
| CAMAG | 1 | 1 md | ❌ blocked | сайт нестабилен — повторить позже |

---

## Что готово полностью

1. ✅ **Полная инфраструктура** на 45.66.117.251 (Phase 3+3.5)
   - Twenty CRM (`crm.gluvex.com`), LiteLLM (`litellm.gluvex.com`), Camunda (`bpm.gluvex.com`), MinIO (`files.gluvex.com`)
   - app-db с 11+7 таблицами (master-data + catalog)
   - MemPalace на Qdrant, Caddy auto-SSL
   - Бэкап cron, manage.sh, OpenRouter ключ работает

2. ✅ **Каталог Gluvex** — 39,395 артикулов спарсены и категоризованы (migration 003+004)

3. ✅ **VendorAdapter framework** в catalog-crawler:
   - `base.py` — общая логика, fetcher selection, UPSERT in product, save PDF/markdown to MinIO
   - `generic.py` — universal adapter через YAML-style конфиг
   - `core/playwright_fetcher.py` — headless Chromium для anti-bot
   - `core/fetcher.py` — httpx с proxy support
   - 12 brand presets в `__main__.py`

4. ✅ **IPRoyal residential proxy** подключён, PROXY_URL в `/opt/gluvex/secrets/.env`

5. ✅ **Brochure-finder** для download-center страниц (`adapters/brochure_finder.py`)

---

## Что в полупозиции (требует доработки)

### A. Matching PDF к product записям

**Проблема:** Memmert brochure-finder скачал 435 PDF, но `matched=0` — мой regex `[A-Z]{2,5}\d{2,4}[a-zA-Z]*` не ловит короткие коды Memmert (VO, IN, IF, U, HCP без цифр).

**Решение в новой сессии:**
- В `adapters/brochure_finder.py` улучшить `model_pattern` для Memmert:
  ```python
  "model_pattern": r"\b(UN|UF|UF\d|IN|INplus|IF|IFplus|ICO|ICOmed|ICP|IPP|SF|SFP|SFE|HCP|HPP|ST|BE|WB|WPE|VO|VOcool|SR|TTC|TWB|WTB|UFB|UNB|UNm)\b",
  ```
- Запустить **только UPDATE matching** (не пере-скачивать PDF — они в MinIO):
  ```python
  # отдельная функция rematch_brochures(brand_slug) — пробегает по MinIO listing,
  # делает SELECT product WHERE brand=X AND filename содержит series-code
  ```
- ~30 минут работы

### B. Heidolph / SOTAX — BFS не идёт на model level

**Проблема:** entry_urls на категории (`/emea/en/Products/Stirring`) находят только subcategory pages, не отдельные модели типа `MR-Hei-Standard`, `RX-300`.

**Решение:** Изучить руками 1-2 product page на Heidolph + добавить **второй уровень entry_urls** или recursive walk до depth 6 с keyword filtering.

### C. Retsch — URL trap

**Проблема:** Retsch HTML имеет relative hrefs которые `urljoin` интерпретирует неправильно — `/products/milling/` + `products/milling/jaw-crusher/` = `/products/milling/products/milling/jaw-crusher/` (404).

**Решение:** Добавить поддержку `<base href="...">` тега в parser:
```python
# в _extract_internal_links парсе
base_tag = tree.css_first("base[href]")
if base_tag:
    base_url = urljoin(base_url, base_tag.attrs["href"])
# дальше urljoin делать от base_url
```

### D. CAMAG — сайт нестабилен

Был timeout при попытке. Проверить через 1-2 дня.

### E. Waters — HTTP/2 error в одном из URL

Нужен retry с HTTP/1.1 fallback.

---

## Что **не** сделано (новая работа)

### Приоритет 1 — Русские дистрибьюторы (cross-check Agilent + Thermo + Shimadzu)

Это **критически важно для бизнеса Gluvex**:
- У нас 35,641 артикулов Agilent в БД из gluvexlab.com БЕЗ описаний/datasheets
- Сам сайт Agilent защищён Akamai (IPRoyal не пробивает)
- **5 русских дистрибьюторов открыты БЕЗ proxy** (мы и так в RU маршруте быстрее):
  - **Lacopa** (lacopa.group) — самый широкий: analytical + genomics + biotech
  - **Millab** (millab.ru) + **analitika.millab.ru** — premium-каталог с фильтром по производителям
  - **IMC Systems** (imc-systems.ru) — хроматография
  - **Element-msc** (element-msc.ru) — генеральный дистрибьютор Shimadzu в РФ

Sitemap.xml есть у всех. Просто `GenericVendorAdapter` с правильными `entry_urls` и `category_keyword_map`.

**~1 час на adapter** каждый, ~4-5 часов на все 4.

### Приоритет 2 — Agilent sitemap stubs

Файл `adapters/vendors/agilent_sitemap.py` уже написан. Нужно:
- Override `run()` чтобы skip `fetcher.get(url)` для Agilent product pages (всё равно 403)
- Получить 9,215 URL из products0.xml
- Создать stub-записи в `product` table с metadata `{stub_from_sitemap: true, needs_enrichment: true}`

После этого через distributor crawlers (priority 1) обогатить — они дают real specs и описания для тех же артикулов.

### Приоритет 3 — SelectScience

`selectscience.net` открыт **без proxy**, имеет independent reviews приборов. Полезно для:
- Cross-validation specs
- Реальные user feedback (полезно для агента-аналитика)

### Приоритет 4 — Доделать SOTAX/Heidolph/Retsch/CAMAG

См. секцию «в полупозиции» выше.

### Приоритет 5 — Memmert PDF matching

См. секцию A выше.

---

## Файловая структура (что где)

```
/opt/gluvex/repos/Repository13-33/tenderland_bot/
├── docs/
│   ├── system-state.md             ← operational reference (READ FIRST)
│   ├── master-data-architecture.md ← 1С как master + 5 контуров
│   ├── storage-architecture.md     ← БД + MinIO + Qdrant
│   ├── catalog-architecture.md     ← модель product/configuration/compatibility
│   └── HANDOFF_NEXT_SESSION.md     ← (этот файл)
└── infra/gluvex_tender_machine/stack/
    ├── docker-compose.yml          ← 12 services
    ├── Caddyfile
    ├── manage.sh                   ← операционные команды
    ├── migrations/                 ← 4 SQL миграции
    └── catalog-crawler/
        └── src/catalog_crawler/
            ├── __main__.py         ← typer CLI (12 brand presets)
            ├── adapters/
            │   ├── gluvexlab.py
            │   ├── gluvexlab_products.py
            │   ├── brochure_finder.py
            │   └── vendors/
            │       ├── base.py          ← VendorAdapter ABC
            │       ├── generic.py       ← конфигурируемый
            │       ├── memmert.py       ← специфический
            │       ├── sartorius.py     ← специфический
            │       └── agilent_sitemap.py ← STUB (требует run() override)
            └── core/
                ├── db.py
                ├── fetcher.py            ← httpx + proxy support
                ├── playwright_fetcher.py ← Chromium + stealth
                └── storage.py            ← MinIO helpers
```

---

## Главные операционные команды

### Запустить crawl одного вендора:
```bash
ssh gluvex
cd /opt/gluvex/repos/Repository13-33/tenderland_bot/infra/gluvex_tender_machine/stack
PROXY=$(grep "^PROXY_URL=" /opt/gluvex/secrets/.env | cut -d= -f2-)

docker compose run --rm -e PROXY_URL="$PROXY" catalog-crawler vendor <name> [--limit N] [--skip-fresh-days D]
# где <name>: memmert sartorius sotax bandelin retsch metrohm huber heidolph camag
#             agilent shimadzu waters thermofisher sciex bruker

# через Playwright (для anti-bot):
docker compose run --rm -e USE_PLAYWRIGHT=1 -e PROXY_URL="$PROXY" catalog-crawler vendor <name>
```

### Запустить brochure-finder:
```bash
docker compose run --rm catalog-crawler brochures memmert
```

### Проверить состояние БД:
```bash
docker exec app-db psql -U postgres -d gluvex_documents -c "
SELECT imported_from, COUNT(*), COUNT(*) FILTER (WHERE array_length(datasheet_paths,1) > 0) AS with_ds
FROM product WHERE imported_from != 'gluvexlab' GROUP BY 1 ORDER BY 2 DESC;"
```

### MinIO inventory:
```bash
MC_HOST=$(grep ^MINIO_ROOT_USER /opt/gluvex/secrets/.env | cut -d= -f2):$(grep ^MINIO_ROOT_PASSWORD /opt/gluvex/secrets/.env | cut -d= -f2)
docker exec -e MC_HOST_local="http://${MC_HOST}@localhost:9000" minio mc ls --recursive local/product-brochures/ | head -50
```

---

## Известные баги / quirks

1. **Sartorius URL filter** — иногда ловит resource/compendium pages (не товары). Edge case, ~10 errors на полном crawl.
2. **Heidolph entry_urls** — берёт только emea/en, но всё равно находит мало deeper pages.
3. **Sciex 4500md-mass-spectrometer** — пример редкого vendor_code-by-default извлечения (работает).
4. **TYPO3-сайты** (Memmert) — query-параметр URL'ы с `cHash` дают 404. Уже отфильтровано через `?` блокировку в URL.
5. **403 редко на отдельных PDFs Sartorius** — раз в 50-100 запросов. Norm.

---

## Бюджет ресурсов

- **IPRoyal**: 5 GB plan, использовано ~0.1 GB. Хватит на десятки полных crawl'ов.
- **OpenRouter**: $50 limit, использовано ~$0.01 (один smoke test). LLM-matching пока не использовали.
- **Anthropic API**: не используется напрямую.
- **Сервер**: 16 CPU/64 GB/512 GB NVMe — нагрузка ~5% CPU, ~5 GB RAM.

---

## Команда для старта в новой сессии

```
Продолжаем работу по tenderland_bot.

Прочитай в порядке:
1. tenderland_bot/docs/HANDOFF_NEXT_SESSION.md
2. tenderland_bot/docs/system-state.md
3. tenderland_bot/docs/catalog-architecture.md

После — приступай к Приоритету 1 (русские дистрибьюторы как cross-check для Agilent).
Начни с Lacopa.

GitHub: https://github.com/timofeirassokhin/Repository13-33/pull/6
Branch: claude/nostalgic-bose-03e0b8
Сервер:  ssh gluvex@45.66.117.251 (или ssh gluvex с твоим ssh-config)
```
