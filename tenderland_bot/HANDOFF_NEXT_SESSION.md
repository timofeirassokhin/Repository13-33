# Gluvex Tender Machine — handoff в новый чат

**Дата:** 2026-05-08
**Контекст:** текущий чат стал большой, продолжаем в новой сессии
**Цель документа:** дать новому Claude-агенту полную картину состояния проекта, что копировать на сервер, что игнорировать

---

## ⚠️ КРИТИЧНО — прочитать ДО любых действий

В **`C:\Users\rstim\Documents\New project\`** обнаружен **отдельный начатый проект Gluvex CRM + tender monitor**, **который не учитывался** в текущем чате. Это git-репо со следующим:

```
Documents/New project/
├── README.md                                                    # «Gluvex CRM and Tender Monitoring Server»
├── docker-compose.yml                                           # Twenty + Postgres + Redis + tender-monitor
├── .env.example                                                 # стартовые env переменные
├── docs/
│   ├── architecture.md                                          # ⭐ target architecture
│   ├── runbook.md                                               # ⭐ server bootstrap, deployment, backups
│   └── tender-domain-model.md                                   # ⭐ domain matching model
├── services/
│   └── tender-monitor/                                          # ⭐ FastAPI scaffold
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── src/                                                 # уже есть стартовый код!
├── scripts/
│   ├── backup-twenty.sh                                         # ⭐ backup скрипт Twenty
│   └── backup-tender-monitor.sh                                 # ⭐ backup скрипт сервиса
├── molecular_diagnostics_supplier_products_table.md (24 KB)     # ⭐⭐ ТАБЛИЦА ПОСТАВЩИКОВ
├── molecular_diagnostics_supplier_products_table_v2.md (28 KB)  # ⭐⭐ ВЕРСИЯ 2
└── tenderland_*_keywords.md                                     # уже использовано в config/
```

### Что это значит для нового чата

1. **Первое действие нового агента:** прочитать
   - `Documents/New project/README.md`
   - `Documents/New project/docs/architecture.md`
   - `Documents/New project/docs/runbook.md`
   - `Documents/New project/docs/tender-domain-model.md`
   - `Documents/New project/molecular_diagnostics_supplier_products_table_v2.md`
   - `Documents/New project/services/tender-monitor/` (структура и pyproject)

2. **Сравнить с текущим состоянием в `tenderland_bot/`:**
   - Возможно `Documents/New project/docs/architecture.md` дополняет/конфликтует с нашим `tenderland_bot/ARCHITECTURE.md`
   - `tender-domain-model.md` — это **прямой материал для Analyzer Module 2** (matcher), нужно изучить
   - `services/tender-monitor/` — возможно стартовый scaffold который надо доделать вместо писания с нуля

3. **`molecular_diagnostics_supplier_products_table_v2.md` — это ЧЕРНОВИК КАТАЛОГА ПРОДУКЦИИ Gluvex** в табличном виде с колонками:
   - `supplier_site` / `block` (секвенатор/ячейки/библиотеки/сервис) / `market_name` (как пишут в ТЗ)
   - `oem_or_platform` / `manufacturer` / `registration` (РЗН/РУ)
   - `key_characteristics` / `consumables_or_assays` / `applications`
   - **`tz_matching_terms` — слова и паттерны для агента-матчера** ← золотой ресурс
   - `source` / `confidence`

   Это **именно структура** которая нужна для `products` таблицы Postgres и Analyzer Module 2. Импорт этой таблицы в JSON/БД сразу даёт частичный каталог по молекулярке.

### Решение конфликта дублирования

Вариант A: **Объединить два проекта в один репо.** Перенести `Documents/New project/*` в `tenderland_bot/`:
- `docker-compose.yml` → `tenderland_bot/infra/gluvex_tender_machine/stack/docker-compose.yml` (как стартовая точка для Phase 3)
- `docs/architecture.md` → сравнить с нашим `tenderland_bot/ARCHITECTURE.md`, объединить
- `docs/runbook.md` → `tenderland_bot/docs/runbook.md`
- `docs/tender-domain-model.md` → `tenderland_bot/docs/tender-domain-model.md`
- `services/tender-monitor/` → `tenderland_bot/services/tender-monitor/` (или объединить с `src/tenderland_bot/`)
- `scripts/backup-*.sh` → `tenderland_bot/infra/gluvex_tender_machine/scripts/`
- Таблицы поставщиков → `tenderland_bot/catalog/molecular_diagnostics_suppliers.md` (+ парсер для импорта в БД)

Вариант B: оставить два проекта параллельно — но это плохо, дублирование тех же вопросов.

**Рекомендую вариант A.** Действие в новом чате — после анализа, объединить и закоммитить отдельным PR.

---

## 1. Где что лежит локально на машине

### Корень `D:\-=ClaudeCode=-\` (Repository13-33)

Большой моно-репо с несколькими проектами. **Не путать с одним проектом.** Структура:

| Директория | Размер | Описание | Релевантно Gluvex Tender Machine? |
|---|---|---|---|
| **`tenderland_bot/`** | 5.7M, 66 files | **Наш текущий проект** — Tenderland CLI, конфиги, документация, bootstrap-скрипты | ✅ **КРИТИЧНО, копируем целиком** |
| `infra/twenty/` | — | Конфиг Twenty CRM (для содержащего system 13-33) | 🟡 **Образец**, копируем структуру docker-compose, но БД и данные новые |
| `infra/mempalace/` | — | MemPalace для content system 13-33 | 🟡 **Образец**, копируем код, но **создаём отдельный инстанс** для тендеров |
| `infra/litellm/` | — | LiteLLM роутер моделей | ✅ **Полезно** — переиспользуем конфиг, обновим под локальный Qwen + Sonnet |
| `infra/whisper/` | — | Whisper-сервис (faster-whisper) | ✅ **Полезно** — переиспользуем |
| `infra/traefik/` | — | Reverse-proxy для content system 13-33 | 🟡 **Образец**, на новом VPS используем **Caddy** |
| `infra/uploader/` | — | Watcher для MemPalace inbox | 🟡 Может быть полезен, если хотим uploader для тендерных ZIP |
| `infra/n8n/`, `openwebui/`, `qdrant/`, `bot/`, `content-system/`, `sites/`, `openclaw/`, `webdav/` | — | Сервисы content system 13-33 | ❌ **НЕ копируем** — остаётся на VPS 186.246.1.61 |
| `src/` (PA Bot) | 456K | Personal Assistant Telegram Bot (Google Calendar/Drive) | ❌ Отдельный проект |
| `booking_bot/` | 135M | Букинг-бот | ❌ Отдельный проект |
| `koob_scraper/`, `lib_scraper/` | 21K + 158M | Скраперы | ❌ Отдельный проект |
| `photodrama_web/` | 573M (с node_modules) | Next.js сайт | ❌ Отдельный проект |
| `data/`, `docs/`, `tests/` | 96K + 140K | Общая документация и тесты PA Bot | ❌ Не наше |

### Worktree `D:\-=ClaudeCode=-\.claude\worktrees\nostalgic-bose-03e0b8\`

Изолированная копия репо для PR #6. Содержит свежее состояние `tenderland_bot/` после коммита.

### Z:\ (RaiDrive WebDAV mount → 186.246.1.61)

| Путь | Описание | Релевантно? |
|---|---|---|
| `Z:\tenders\` | Тендерные выгрузки CLI tenderland_bot (~2.4M, только Memmert тест) | ✅ **Копируем на новый VPS** в свежий tenders volume |
| `Z:\inbox\<wing>\` | 8 wings библиотеки 13-33: books, articles, 13-33main, 13-33pubs, 13-33scenarios, 13-33interviews, 13-33drafts, misc | ❌ **Не наше** — это данные content system 13-33 |
| `Z:\processed\`, `failed\`, `markdown\`, `preview-assets\`, `test_folder\` | Рабочие папки content system uploader | ❌ Не наше |

### `C:\Users\rstim\Documents\New project\`

Внешний project с материалами. Нашли там:

| Файл | Что это | Использовано? |
|---|---|---|
| `tenderland_analytical_instruments_keywords.md` | Ключевые слова для аналитики (внешний source) | ✅ Влилось в `config/keywords_config.md` |
| `tenderland_molecular_diagnostics_keywords.md` | То же для молекулярки | ✅ Влилось в `config/keywords_config_molecular_diagnostics.md` |
| `molecular_diagnostics_supplier_products_table.md` (+ v2) | **Таблица поставщиков молекулярки** | ⚠️ **НЕ ВНЕСЕНО**, посмотреть в новом чате — может быть полезно для каталога |
| `docker-compose.yml`, `docs/`, `scripts/`, `services/` | Какой-то проект — посмотреть содержимое | ⚠️ Проверить в новом чате |

### `C:\Users\rstim\Downloads\` (xlsx тендерных выгрузок)

Все рабочие выгрузки `Выгрузка '<name>' (DD мая 2026 г._HH_MM_SS).xlsx` — большая часть уже импортирована в `tenderland_bot/docs/` под именами `test*.xlsx`. После миграции на сервер можно удалить.

---

## 2. Что точно копировать на новый VPS 45.66.117.251

### 2.1. Из git: `tenderland_bot/` целиком

После мерджа PR #6:

```bash
# На сервере 45.66.117.251 (как пользователь gluvex):
git clone https://github.com/timofeirassokhin/Repository13-33.git /opt/repo
cp -r /opt/repo/tenderland_bot /opt/gluvex
```

Что внутри:
- `ARCHITECTURE.md` — главная архитектура
- `HANDOFF_TO_ANALYZER.md` — контракт для будущего Analyzer-агента
- `HANDOFF_NEXT_SESSION.md` — этот документ
- `README.md` — быстрый старт
- `catalog/brands_index.md` — карта 43 брендов Gluvex
- `config/keywords_config.md` — 8 тематик аналитики
- `config/keywords_config_molecular_diagnostics.md` — 5 тематик молекулярки
- `docs/SERVER_INFRASTRUCTURE.md` — полная спецификация инфраструктуры
- `docs/autosearch_*.json` — образцы автопоисков
- `docs/autosearch_ui_patches.md` — патчи для сломанных автопоисков
- `docs/autosearch_configs_phase2.md` — конфиги расходники/молекулярка/общелаб
- `docs/test*.xlsx` (12 файлов) — эталонные выгрузки для воспроизводимости
- `infra/gluvex_tender_machine/bootstrap_phase1.sh` + `phase2.sh` + `README.md` — bootstrap-скрипты (уже применены)
- `scripts/` — Python-утилиты (analyze_lcms_export, dump_autosearch_compare, summarize_autosearch, read_keywords_xlsx)
- `src/tenderland_bot/` — Tenderland CLI (api_client, exporter, downloader, models, config)

### 2.2. Из главного репо: переиспользуемые конфиги

С VPS 13-33 (186.246.1.61) можно скопировать **рабочие конфиги** docker-compose как образец:

| Откуда | Что брать | Куда на новом VPS |
|---|---|---|
| `infra/twenty/docker-compose.yml` | Конфиг Twenty CRM с Google SSO | `/opt/gluvex/stack/twenty.yml` |
| `infra/mempalace/Dockerfile + код` | MemPalace FastAPI service | `/opt/gluvex/stack/mempalace/` (свой инстанс!) |
| `infra/litellm/config.yaml` | LiteLLM с роутингом моделей | `/opt/gluvex/stack/litellm/config.yaml` (обновим под Qwen+Sonnet) |
| `infra/whisper/` | faster-whisper service | `/opt/gluvex/stack/whisper/` |
| `infra/uploader/` | (опционально) Watcher для tender ZIP | если решим автоматизировать загрузку в MemPalace |

### 2.3. С Z:\ (RaiDrive)

```bash
# Только Z:\tenders\ (наши тестовые выгрузки)
# На сервере создать /opt/gluvex/data/tenders/
# Перенести:
rsync -av /z/tenders/ root@45.66.117.251:/opt/gluvex/data/tenders/
```

Z:\inbox\* (8 wings 13-33) **не трогаем** — это данные content system 13-33.

### 2.4. Из `Documents\New project\` (проверить в новом чате)

```
molecular_diagnostics_supplier_products_table.md     # таблица поставщиков
molecular_diagnostics_supplier_products_table_v2.md  # версия 2
```

Эти файлы могут содержать структурированный список молекулярных поставщиков для каталога. **Действие в новом чате:** прочитать, если полезно — внести в `tenderland_bot/catalog/`.

---

## 3. Состояние сервера (что уже сделано)

**Сервер:** 45.66.117.251 (Selectel Cloud VPS, Ubuntu 24.04 LTS)
**Конфиг:** 16 vCPU Intel Xeon Gold 6140 / 64 GB RAM ECC / 768 GB NVMe / 1 Gbps
**Стоимость:** 35 187 ₽/мес

**SSH-доступ:**
- `ssh gluvex` (alias в `~/.ssh/config` на машине пользователя) — основной, под пользователем `gluvex`
- `ssh gluvex-root` — backup под root
- Ключ: `~/.ssh/id_ed25519_gluvex`

**Что установлено и настроено (применили `bootstrap_phase1.sh` + `phase2.sh`):**
- ✅ Hostname: `gluvex-tender-machine`
- ✅ apt upgrade (194 пакета)
- ✅ Docker 29.4.3 + Docker Compose V2 (v5.1.3)
- ✅ Swap 8 GB, swappiness=10
- ✅ UFW: deny incoming, allow 22/80/443
- ✅ fail2ban: 3 попытки SSH → бан 1 час
- ✅ unattended-upgrades для security патчей
- ✅ User `gluvex` (sudo + docker, NOPASSWD)
- ⚠️ Root SSH login пока **не отключён** — отключим после стабильности

**Сетевая проверка:**
- ✅ OpenRouter, GitHub, Google, Tenderland, Anthropic API — работают
- Нужен ли VPN/прокси: **нет**, исходящий зарубежный трафик идёт нормально

**Split-tunneling Windows:**
- На машине пользователя добавлен static route для 45.66.117.251 через локальный gateway, чтобы VPN не блокировал доступ к серверу

---

## 4. Что делать в новом чате

### Шаг 1. Стартовое сообщение для нового агента

Скажи новому Claude:
> Привет! Продолжаю работу над Gluvex Tender Machine. Прочитай `D:\-=ClaudeCode=-\.claude\worktrees\nostalgic-bose-03e0b8\tenderland_bot\HANDOFF_NEXT_SESSION.md` и `tenderland_bot/ARCHITECTURE.md` для контекста. Сервер 45.66.117.251 уже настроен, доступ через `ssh gluvex`. Следующий этап — деплой Docker-стека (Caddy + Postgres + Twenty CRM с Google SSO + MemPalace + LiteLLM).

### Шаг 2. Проверить состояние

```bash
# Подключиться, убедиться что сервер на месте
ssh gluvex 'whoami; hostname; docker ps; df -h /'
```

### Шаг 3. Дождаться от тебя

| Ресурс | Статус |
|---|---|
| **DNS-записи** для `crm/tender/bot/mem/litellm.gluvexlab.com` → 45.66.117.251 | ⏳ Сегодня вечером |
| **Google Cloud Project** + OAuth Client ID/Secret | ⏳ После DNS |
| **Service Account JSON** для Drive/Gmail/Calendar API | ⏳ После DNS |

### Шаг 4. Деплой Phase 3 — Docker stack

Когда DNS и Google credentials готовы, новый агент должен:

1. **Подготовить локально в репо** `infra/gluvex_tender_machine/stack/`:
   - `docker-compose.yml` (Caddy + Postgres + Redis + Twenty + MemPalace + LiteLLM + Whisper)
   - `Caddyfile` с auto-SSL Let's Encrypt
   - `.env.example` с Google OAuth переменными
   - `README.md` с инструкцией деплоя

2. **Залить на сервер:**
   ```bash
   ssh gluvex 'sudo mkdir -p /opt/gluvex && sudo chown gluvex:gluvex /opt/gluvex'
   git clone https://github.com/timofeirassokhin/Repository13-33.git /tmp/repo
   cp -r /tmp/repo/tenderland_bot/infra/gluvex_tender_machine/stack/* /opt/gluvex/
   ```

3. **Заполнить `.env`** секретами Google OAuth + сгенерированными паролями Postgres

4. **Запустить:**
   ```bash
   cd /opt/gluvex && docker compose up -d
   ```

5. **Smoke-тесты:**
   - `https://crm.gluvexlab.com` отвечает с кнопкой Sign in with Google
   - Пользователь `rstim@gluvexlab.com` логинится → создаётся Workspace в Twenty
   - `https://mem.gluvexlab.com` отвечает (MemPalace API)
   - `https://litellm.gluvexlab.com` отвечает на тестовый запрос к Sonnet через OpenRouter

### Шаг 5. Phase 4 — Tender Pipeline

После деплоя стека:
1. Активация модуля API Поиск Tenderland (через менеджера) — переходим с UI-автопоисков на JSON-фильтры через `Search/Find`
2. Деплой `gluvex_tender_machine` Python-приложения (Searcher агент)
3. Импорт накопленных xlsx-выгрузок в Postgres + MemPalace `tenders_archive` wing
4. Cron `0 7 * * 1-5` для ежедневного сбора

### Шаг 6. Phase 5+ — параллельные задачи

- Параллельный парсинг каталога Gluvex (60 000 позиций) на новом VPS
- Сбор каталога приборов в структурированном виде (Excel → JSON → Postgres `products`)
- Analyzer Module 1 (классификация + извлечение характеристик) на тестовых архивах Memmert
- Analyzer Module 2 (matcher) — после готовности каталога

---

## 5. Известные открытые задачи

| # | Задача | Статус | Приоритет |
|---|---|---|---|
| 1 | DNS-записи для 5 поддоменов | ⏳ ждём | блокирует Phase 3 |
| 2 | Google OAuth Client + Service Account | ⏳ ждём | блокирует Phase 3 |
| 3 | Активация модуля API Поиск Tenderland | ⏳ запрос менеджеру | блокирует Phase 4 |
| 4 | Подкрутка EXCLUDE для расходников: антивирусы, Касперский, Secret Net | 🟡 готова правка, нужна выгрузка | можно отложить |
| 5 | Создать 4 оставшихся автопоиска через UI Tenderland (молекулярка приборы / молекулярка расходники / общелаб) | 🟡 конфиги в `autosearch_configs_phase2.md` | до миграции на новый VPS — опционально |
| 6 | Каталог продукции Gluvex в структурированном виде | ⏳ блокер для Analyzer Module 2 | параллельная задача |
| 7 | Phase 3: docker-compose стек | ⏳ ждёт DNS + Google credentials | следующий PR |
| 8 | Phase 4: код Tender Pipeline (Searcher/Analyzer/CRM Pusher) | ⏳ ждёт Phase 3 | большой следующий PR |

---

## 6. Полезные ссылки и URL

- **GitHub репо:** https://github.com/timofeirassokhin/Repository13-33
- **PR #6:** https://github.com/timofeirassokhin/Repository13-33/pull/6
- **Сайт Gluvex:** https://gluvexlab.com (каталог)
- **Tenderland API doc:** локально `C:\Users\rstim\Downloads\API Tenderland (v1).pdf`
- **Tenderland API ключ:** в `~/.ssh/...` или `.env` на сервере, **никогда не в git**
- **Сервер Gluvex:** 45.66.117.251 (Selectel)
- **Старый VPS 13-33:** 186.246.1.61 (`crm.13-33.pro`, остаётся работать как было)

---

## 7. Что НЕ делать в новом чате

- ❌ **Не пиши Tenderland API ключ или Google secret в чат** — клади в `.env` на сервере
- ❌ **Не лезь в content system 13-33** на 186.246.1.61 — это отдельная система, работающая в проде
- ❌ **Не пиши код Analyzer Module 2** до готовности каталога продукции — будет бесполезен
- ❌ **Не разворачивай docker-compose** до настройки DNS и Google OAuth
- ❌ **Не переписывай ARCHITECTURE.md** без явного решения — это уже стабильная спецификация

---

_Документ — единственная точка входа в новую сессию. Все детали по архитектуре в `ARCHITECTURE.md`, по инфраструктуре в `docs/SERVER_INFRASTRUCTURE.md`, по конфигам автопоисков в `config/keywords_config*.md` и `docs/autosearch_configs_phase2.md`._
