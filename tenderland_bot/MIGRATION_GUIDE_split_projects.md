# Миграция на отдельные компьютеры — разделение проектов

**Дата:** 2026-05-08
**Текущая машина:** Windows, пользователь `rstim` (`C:\Users\rstim\`)

**Цель:** разнести два пула проектов на физически отдельные компьютеры:

- **🟢 Компьютер A — Gluvex + Tender Machine** (новый бизнес-стек)
- **🟡 Компьютер B — 13-33 + Timofei Rassokhin Personal** (контентная экосистема)

Можно установить оба проекта на один компьютер, но если хочется чёткого разделения для разных контекстов работы Claude — следующая инструкция.

---

## Часть 0. Что общее (нужно ОБОИМ компьютерам)

Без этого Claude Code просто не запустится. Установить на каждый компьютер.

### 0.1. Программы (установить с нуля)

| ПО | Источник | Зачем |
|---|---|---|
| **Claude Code CLI** (или Claude desktop) | https://claude.com/claude-code | Этот инструмент |
| **Git for Windows** | https://gitforwindows.org/ | git, ssh, bash, scp — критически нужно |
| **GitHub CLI (gh)** | https://cli.github.com/ или `winget install GitHub.cli` | для PR из терминала |
| **Python 3.12+** | https://python.org или Windows Store | для скриптов, виртуальных окружений |
| **Docker Desktop** | https://docker.com (если хочешь локальные тесты) | для тестов docker-compose |
| **PowerShell 7** | `winget install Microsoft.PowerShell` | удобнее чем стандартный |
| **VPN-клиент** | твой текущий | для общения с Anthropic API из РФ |
| **RaiDrive** | https://www.raidrive.com/ — `RaiDrive.Mount_2025.12.30_x64.exe` | для монтирования `Z:\` (общий диск через WebDAV) |
| **Yandex Disk / Google Drive client** | по предпочтению | если нужен sync файлов |
| **PuTTY** *(опц.)* | https://www.putty.org/ | альтернативный SSH-клиент |

### 0.2. Файлы пользователя (копировать в одинаковые места на оба компьютера)

> ⚠️ **Эти файлы содержат секреты — копировать только напрямую через защищённый канал, никогда не через публичные облака без шифрования.**

| Что копировать | Откуда | Куда | Содержимое |
|---|---|---|---|
| **`~/.claude/`** (вся папка) | `C:\Users\rstim\.claude\` | `C:\Users\<имя>\.claude\` | Настройки Claude Code, плагины, credentials, projects history |
| **`~/.gitconfig`** | `C:\Users\rstim\.gitconfig` | `C:\Users\<имя>\.gitconfig` | Имя/email для коммитов |
| **`~/.ssh/config`** *(только нужные блоки)* | `C:\Users\rstim\.ssh\config` | `C:\Users\<имя>\.ssh\config` | SSH алиасы серверов |

### 0.3. Учётные записи / cloud-аккаунты

| Сервис | Где входить |
|---|---|
| GitHub | `gh auth login` или через credential manager |
| Anthropic | при первом запуске Claude Code |
| Google Workspace | через браузер для веб-сервисов |

---

## Часть 1. Компьютер A — Gluvex + Tender Machine

### 1.1. Что нужно скопировать

#### Git-репо (можно либо clone заново, либо скопировать)

**Вариант 1 (рекомендую): склонировать с нуля**
```bash
gh auth login
git clone https://github.com/timofeirassokhin/Repository13-33.git D:\-=ClaudeCode=-
cd D:\-=ClaudeCode=-
git checkout claude/nostalgic-bose-03e0b8  # ветка с PR #6
```

После клонирования у тебя появится **весь моно-репо** включая `tenderland_bot/`. Это **не плохо** — лишние папки можно не открывать. Но если хочется чисто — см. Вариант 2.

**Вариант 2: скопировать только нужное**
```powershell
# Создать пустую папку
New-Item -ItemType Directory -Force "D:\Gluvex"
# Скопировать только tenderland_bot/
robocopy "D:\-=ClaudeCode=-\tenderland_bot" "D:\Gluvex\tenderland_bot" /E /XD __pycache__ .venv node_modules
```

Минус: оторвётся от git, не сможешь делать PR. Лучше Вариант 1.

#### Отдельный начатый проект (Documents/New project/)

```powershell
robocopy "C:\Users\rstim\Documents\New project" "D:\Gluvex\New project" /E /XD .venv node_modules /XF "~$*"
```

Это **второй проект** Gluvex CRM с готовым docker-compose, FastAPI scaffold и таблицами поставщиков молекулярки. Критично для следующих фаз.

#### SSH-ключ к серверу Gluvex

```powershell
# С текущего компьютера
robocopy "C:\Users\rstim\.ssh" "D:\Gluvex\_secrets\.ssh" id_ed25519_gluvex id_ed25519_gluvex.pub
```

Затем на новом компьютере:
```powershell
# В пользовательской папке нового компа
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh"
Copy-Item "D:\Gluvex\_secrets\.ssh\id_ed25519_gluvex*" "$env:USERPROFILE\.ssh\"
icacls "$env:USERPROFILE\.ssh\id_ed25519_gluvex" /inheritance:r /grant:r "$env:USERNAME:R"
```

#### SSH-конфиг (только Gluvex-блоки)

Создать `~/.ssh/config` на новом компе с двумя записями (взять из `C:\Users\rstim\.ssh\config`):

```
Host gluvex
    HostName 45.66.117.251
    User gluvex
    IdentityFile ~/.ssh/id_ed25519_gluvex
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60

Host gluvex-root
    HostName 45.66.117.251
    User root
    IdentityFile ~/.ssh/id_ed25519_gluvex
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
```

**Не копировать** блок `Host tr-vps` (это для проекта 13-33, см. Часть 2).

#### Файлы из Downloads (рабочие материалы Gluvex)

```powershell
robocopy "C:\Users\rstim\Downloads" "D:\Gluvex\_downloads" `
  "API Tenderland (v1).pdf" `
  "Tenderland_keywords_config.xlsx" `
  "Tenderland_keywords_molecular_diagnostics.xlsx" `
  "gluvex_L3_order_to_delivery.svg" `
  "gluvex_L3_sales_lead_to_contract.svg" `
  "gluvex_main_spine_lead_to_warranty.svg" `
  "выигранные тендеры Альбиоген список.docx"

# Все рабочие тендерные xlsx-выгрузки  
robocopy "C:\Users\rstim\Downloads" "D:\Gluvex\_downloads\tenderland_exports" `
  "Выгрузка *.xlsx"
```

#### Иллюминовские материалы (если нужны)

```powershell
robocopy "C:\Users\rstim\Downloads" "D:\Gluvex\_downloads\illumina" `
  "NEW PO_ILLUMINA *.xls"
```

#### Z:\tenders (опционально — RaiDrive подключение)

`Z:\tenders\` — это **сетевая папка** на твоём сервере 13-33 через RaiDrive. Чтобы получить к ней доступ с нового компа:

1. Установить RaiDrive
2. Настроить WebDAV mount к `https://drive.13-33.pro` (или внутреннему адресу)
3. Маунт окажется как `Z:\` со всеми папками (`tenders/`, `inbox/`, и т.д.)

**Файлы физически копировать не нужно** — они на сервере, доступ из любого компа через RaiDrive.

### 1.2. Структура после миграции на компьютере A

```
D:\
├── Gluvex\                                    # рабочая директория
│   ├── -=ClaudeCode=-\                        # git clone Repository13-33
│   │   └── tenderland_bot\                    # ← основной проект
│   ├── New project\                            # отдельный проект Gluvex CRM
│   ├── _downloads\                             # материалы из Downloads
│   │   ├── API Tenderland (v1).pdf
│   │   ├── Tenderland_keywords_*.xlsx
│   │   ├── gluvex_*.svg
│   │   └── tenderland_exports\
│   └── _secrets\                               # ⚠️ удалить после копирования в ~/.ssh
└── ...

C:\Users\<имя>\
├── .claude\                                    # настройки Claude Code (общие)
├── .gitconfig                                  # git настройки (общие)
└── .ssh\
    ├── config                                  # только gluvex + gluvex-root блоки
    ├── id_ed25519_gluvex                        # приватный ключ
    └── id_ed25519_gluvex.pub                    # публичный
```

### 1.3. Первые команды на компьютере A после миграции

```bash
# Проверка
git --version
gh --version
ssh -V
claude --version

# Тест SSH к серверу
ssh gluvex 'hostname; uptime'

# Открыть Claude Code в проекте
cd /d/Gluvex/-=ClaudeCode=-/tenderland_bot
claude
```

В первой сессии Claude скажи:
> Прочитай `HANDOFF_NEXT_SESSION.md` и `ARCHITECTURE.md`. Я перенёс проект на новый компьютер. Сервер 45.66.117.251 уже настроен. Продолжаем Phase 3 — деплой docker-compose стека.

---

## Часть 2. Компьютер B — 13-33 + Timofei Rassokhin Personal

### 2.1. Что нужно скопировать

#### Git-репо (тот же `Repository13-33`)

```bash
gh auth login
git clone https://github.com/timofeirassokhin/Repository13-33.git D:\-=ClaudeCode=-
cd D:\-=ClaudeCode=-
git checkout main
```

После клонирования будут все папки. Релевантные **для 13-33 / TR-com**:
- `src/` — Personal Assistant Telegram Bot (Google Calendar/Drive)
- `booking_bot/` — букинг-бот
- `koob_scraper/`, `lib_scraper/` — скраперы
- `photodrama_web/` — Next.js сайт photodrama
- `infra/` — вся инфраструктура content system 13-33 + tr-com (Twenty/MemPalace/LiteLLM/Whisper/Traefik/n8n/qdrant/openwebui/uploader/sites/bot/openclaw/webdav)
- `data/`, `docs/`, `tests/`
- `CLAUDE.md` — глобальные инструкции для контента 13-33

**`tenderland_bot/`** просто игнорируется — это для другого компьютера, можно удалить локально:
```bash
# В рабочей копии репо на компьютере B
git rm -r tenderland_bot/
git commit -m "drop tenderland_bot/ from this checkout (lives on Gluvex computer)"
# НЕ ПУШИТЬ это — иначе пропадёт у компьютера A
```

⚠️ **На самом деле — не делай этого**. Лучше просто не открывать `tenderland_bot/`. Любые правки в этой папке делать только на компьютере A.

#### SSH-ключ к серверу tr-com

```powershell
robocopy "C:\Users\rstim\.ssh" "D:\TR\_secrets\.ssh" id_ed25519_tr_com_deploy id_ed25519_tr_com_deploy.pub id_rsa_cornholio
```

На новом компьютере:
```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh"
Copy-Item "D:\TR\_secrets\.ssh\*" "$env:USERPROFILE\.ssh\"
icacls "$env:USERPROFILE\.ssh\id_ed25519_tr_com_deploy" /inheritance:r /grant:r "$env:USERNAME:R"
```

#### SSH-конфиг (только tr-vps блок)

```
Host tr-vps
  HostName 186.246.1.61
  User agent
  IdentityFile ~/.ssh/id_ed25519_tr_com_deploy
  IdentitiesOnly yes
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

**Не копировать** блоки `Host gluvex` и `Host gluvex-root`.

#### Z:\ через RaiDrive

Настроить так же как на компьютере A. Папки `inbox/` (8 wings), `processed/`, `markdown/` — рабочие папки контентной системы. Можно работать прямо с сетевого диска.

#### Документы и материалы 13-33

В `Documents/` у тебя могут быть личные docx/md по проекту 13-33 (`fraktal_13_33`, `practice_of_thinking`, `karpman_obzor` и т.п.). Скопируй всё что нужно:

```powershell
robocopy "C:\Users\rstim\Documents" "D:\TR\_documents" /E /XD ".git" "node_modules" /XF "~$*"
```

⚠️ **Документы из `Documents/New project/`** (Gluvex проект) — **не копировать** на компьютер B, это для A.

### 2.2. Структура после миграции на компьютере B

```
D:\
├── -=ClaudeCode=-\                            # git clone Repository13-33
│   ├── src\                                    # PA bot
│   ├── infra\                                  # инфра 13-33 + tr-com
│   ├── booking_bot\
│   ├── lib_scraper\, koob_scraper\
│   ├── photodrama_web\
│   └── tenderland_bot\                         # ← НЕ ОТКРЫВАТЬ (для компьютера A)
├── TR\                                         # рабочие материалы 13-33
│   ├── _documents\                             # из Documents
│   └── _secrets\                               # ⚠️ удалить после копирования в ~/.ssh
└── ...

C:\Users\<имя>\
├── .claude\                                    # настройки Claude Code (общие)
├── .gitconfig                                  # git настройки (общие)
└── .ssh\
    ├── config                                  # только tr-vps блок
    ├── id_ed25519_tr_com_deploy                 # приватный ключ
    ├── id_ed25519_tr_com_deploy.pub             # публичный
    └── id_rsa_cornholio                         # старый ключ (если нужен)
```

### 2.3. Первые команды на компьютере B после миграции

```bash
# Тест SSH к серверу
ssh tr-vps 'hostname; uptime'

# Тест RaiDrive (Z:\)
ls Z:/inbox/

# Открыть Claude Code в проекте
cd /d/-=ClaudeCode=-
claude
```

---

## Часть 3. Что НЕ копировать (мусор / regenerable)

| Что | Почему |
|---|---|
| `node_modules/` (везде где есть) | Восстанавливается через `npm install`. Может быть **сотни мегабайт** |
| `__pycache__/` | Регенерируется Python автоматически |
| `.venv/`, `venv/` | Восстанавливается через `pip install -r requirements.txt` |
| `*.pyc`, `*.pyo` | Сгенерированный байткод |
| `~$*` (Word lock files) | Системный мусор |
| `*.egg-info/` | Регенерируется |
| Старые установщики из Downloads (`gh_*.msi`, `PuTTY Installer.exe`, `RaiDrive.Mount_*.exe`, `setup-Happ*.exe` и т.д.) | Скачиваются заново при необходимости |
| `Movavi Sync\`, `Movavika Sync\` | Кэши приложений |
| `Telegram Desktop\` | Кэш TG-клиента, не нужно (логин повторно) |
| Системные cache в `C:\Users\<имя>\AppData\Local\Temp\` | Временные файлы |

---

## Часть 4. Чек-лист пошагового переноса

### На текущем компьютере (этом)

- [ ] **Закоммитить и запушить всё незакоммиченное** в git: `cd /d/-=ClaudeCode=-; git status`
- [ ] **Проверить PR #6** в GitHub: https://github.com/timofeirassokhin/Repository13-33/pull/6
- [ ] **Создать на флешке/внешнем диске две папки** `Gluvex_migration/` и `TR_migration/`
- [ ] **Скопировать секреты** (см. разделы 1.1 и 2.1) в `_secrets/`
- [ ] **Скопировать `~/.claude/`** (вся папка, ~10 МБ) в обе целевые папки
- [ ] **Скопировать `~/.gitconfig`** в обе папки
- [ ] **Документы из `C:\Users\rstim\Documents\`** разделить:
  - `New project/` → Gluvex_migration/
  - всё остальное (фрактал, психология, статьи, методики) → TR_migration/
- [ ] **Проверить на флешке итоговый размер** (Gluvex < 100 МБ, TR может быть большим из-за документов)

### На новом компьютере A (Gluvex)

- [ ] Установить программы из части 0.1
- [ ] Скопировать `.claude/`, `.gitconfig`, `.ssh/*` из секретов на флешке
- [ ] Установить права на ssh-ключи через `icacls`
- [ ] `gh auth login` (или использовать access token из credential manager старого компа)
- [ ] `git clone` репо
- [ ] Проверить `ssh gluvex 'whoami'` — должен вернуть `gluvex`
- [ ] Запустить `claude` в `tenderland_bot/`
- [ ] Дать первое сообщение из `HANDOFF_NEXT_SESSION.md` раздела 4

### На новом компьютере B (13-33)

- [ ] Установить программы из части 0.1
- [ ] Скопировать `.claude/`, `.gitconfig`, `.ssh/*`
- [ ] `gh auth login`
- [ ] `git clone` репо
- [ ] Установить и настроить **RaiDrive** для `Z:\`
- [ ] Проверить `ssh tr-vps 'whoami'` — должен подключиться
- [ ] Скопировать персональные документы из флешки в `D:\TR\_documents\`

---

## Часть 5. Стратегия работы после разделения

### Один git-репо, два компьютера

Поскольку оба проекта живут в **одном `Repository13-33`**, обе машины работают с одной и той же кодовой базой. Это даёт:

- ✅ Можно делать PR из любого компьютера
- ✅ История проектов не разрывается
- ⚠️ Нужно следить чтобы не было одновременных правок в одних и тех же файлах
- ⚠️ Нельзя удалять `tenderland_bot/` на компе B и пушить — это сломает A

### Правила

1. **Компьютер A работает только в `tenderland_bot/`**. Любые правки в `infra/`, `src/`, `booking_bot/` и других папках 13-33 — **запрещены**.
2. **Компьютер B работает где угодно КРОМЕ `tenderland_bot/`**.
3. Перед началом работы на любом компе — **`git pull`**.
4. После завершения — **`git push`** или PR.

### Альтернатива: два отдельных репо

Если строгое разделение критично — можно сделать так:

1. Создать отдельный репо `gluvex-tender-machine` на GitHub
2. Перенести только `tenderland_bot/*` туда (`git subtree split` или ручной copy)
3. Удалить `tenderland_bot/` из `Repository13-33`
4. На компьютере A работать только с `gluvex-tender-machine`
5. На компьютере B — только с `Repository13-33`

Это **большая операция**, делать только если действительно нужно. Сейчас не нужно.

---

## Часть 6. После переноса — на каждом компьютере

Положи этот файл (`MIGRATION_GUIDE_split_projects.md`) в видное место:

- На компьютере A: `D:\Gluvex\MIGRATION_GUIDE_split_projects.md`
- На компьютере B: `D:\TR\MIGRATION_GUIDE_split_projects.md`

Чтобы при необходимости вспомнить структуру.

---

## Часть 7. Quick-команды копирования (одной строкой)

### Создать `Gluvex_migration/` папку для флешки

```powershell
$dest = "F:\Gluvex_migration"  # замени F: на букву флешки
New-Item -ItemType Directory -Force $dest

# Секреты
robocopy "$env:USERPROFILE\.claude" "$dest\.claude" /E
Copy-Item "$env:USERPROFILE\.gitconfig" "$dest\"
robocopy "$env:USERPROFILE\.ssh" "$dest\.ssh" id_ed25519_gluvex* config

# Отдельный проект Gluvex CRM
robocopy "C:\Users\rstim\Documents\New project" "$dest\Documents\New project" /E /XD .venv node_modules /XF "~$*"

# Материалы из Downloads
$downloads = "C:\Users\rstim\Downloads"
robocopy $downloads "$dest\Downloads" `
  "API Tenderland (v1).pdf" `
  "Tenderland_keywords_config.xlsx" `
  "Tenderland_keywords_molecular_diagnostics.xlsx" `
  "gluvex_L3_order_to_delivery.svg" `
  "gluvex_L3_sales_lead_to_contract.svg" `
  "gluvex_main_spine_lead_to_warranty.svg" `
  "выигранные тендеры Альбиоген список.docx"

# Тендерные xlsx (все)
robocopy $downloads "$dest\Downloads\tenderland_exports" "Выгрузка *.xlsx"

# Этот guide
Copy-Item "C:\Users\rstim\Documents\MIGRATION_GUIDE_split_projects.md" "$dest\"
```

### Создать `TR_migration/` папку для флешки

```powershell
$dest = "F:\TR_migration"
New-Item -ItemType Directory -Force $dest

# Секреты
robocopy "$env:USERPROFILE\.claude" "$dest\.claude" /E
Copy-Item "$env:USERPROFILE\.gitconfig" "$dest\"
robocopy "$env:USERPROFILE\.ssh" "$dest\.ssh" id_ed25519_tr_com_deploy* id_rsa_cornholio config

# Документы 13-33 / Timofei (всё кроме New project и тендерных xlsx)
robocopy "C:\Users\rstim\Documents" "$dest\Documents" /E /XD ".git" "node_modules" "New project" /XF "~$*"

# Этот guide
Copy-Item "C:\Users\rstim\Documents\MIGRATION_GUIDE_split_projects.md" "$dest\"
```

После копирования: безопасно вытащить флешку, перенести на новый компьютер, распаковать.

---

_Документ обновляй по мере появления нового важного контента в проектах. Если что-то упустил — допиши в раздел 1 (для Gluvex) или 2 (для 13-33)._
