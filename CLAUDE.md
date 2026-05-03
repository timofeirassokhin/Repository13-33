# CLAUDE.md

## Project Overview

Personal Assistant Telegram Bot — бот-помощник с интеграцией Google Calendar и Google Drive.
Управляет календарём, заметками и сортировкой файлов через Telegram.

## Tech Stack

- Python 3.11+
- python-telegram-bot 22.6 (async)
- google-api-python-client + google-auth-oauthlib (Calendar, Drive, Docs API)
- aiosqlite (SQLite для метаданных и токенов)
- pydantic + pydantic-settings (модели и конфиг)
- aiohttp (OAuth callback сервер)

## Project Structure

```
src/
├── __main__.py         # Entry point, DI wiring
├── config.py           # Settings from .env (prefix PA_)
├── logger.py           # Rotating file + console logging
├── models/             # Pydantic domain models
├── db/                 # aiosqlite connection, migrations, repositories
├── services/           # Business logic (google_auth, calendar, notes, file_sorter)
├── agent/              # Intent enum, Dispatcher (routes commands to services), response formatting
└── interfaces/
    ├── telegram/       # Bot, handlers (common, auth, calendar, notes, files), keyboards, middlewares
    └── webhook/        # OAuth callback aiohttp server
```

## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill config
cp .env.example .env

# Run the bot
python -m src

# Run tests
pytest tests/
```

## Code Style & Conventions

- Async throughout; Google API calls wrapped in `asyncio.to_thread()`
- All config via .env with PA_ prefix (pydantic-settings)
- Command-dispatch pattern: Telegram command → Intent → Dispatcher → Service → Google API
- Services return `ServiceResult[T]` (success/data/error)
- Handlers are thin: parse input → build ParsedCommand → call dispatcher → send formatted result
- Russian UI strings in bot responses, English in code/comments

## Key Context

- Google API client is synchronous — always use `asyncio.to_thread()` for API calls
- OAuth tokens stored in SQLite (users table); auto-refresh on expiry
- Notes metadata cached locally in SQLite for fast tag/text search
- On Windows, signal handlers don't work in asyncio — uses KeyboardInterrupt fallback
- Telegram user whitelist: set PA_TELEGRAM_ALLOWED_USER_IDS in .env (empty = allow all)

## Content system 13-33 (parallel infrastructure)

Contained in `infra/`. Production stack on server (RU VPS at 186.246.1.61).

### Components
- **Twenty CRM** (`crm.13-33.pro`) — workflow state: Idea / Draft / Publication / Direction / Topic / Channel
- **MemPalace** (server-side, http://mempalace:8080) — knowledge archive with 8 wings: `books`, `articles`, `13-33main`, `13-33pubs`, `13-33scenarios`, `13-33interviews`, `13-33drafts`, `misc`
- **WebDAV** (`drive.13-33.pro`) — общий диск, монтируется как `Z:\` на Windows через RaiDrive
- **Uploader** — следит за `Z:\inbox\<wing>\`, парсит PDF/DOCX/EPUB/TXT/MD, чанкит, грузит в MemPalace
- **LiteLLM** — роутер моделей: `cheap`=Haiku, `creative`=Sonnet, `premium`=Opus (через OpenRouter, обходит RU-блок)
- **Whisper** (локальный) — транскрипция голосовых
- **Bot** (`@claw1333_bot`) — `/idea`, `/draft`, `/iterate`, `/archive`, `/library_search`, голос/текст intake

### Rule: автоматическая архивация скачанной литературы

**Когда я выполняю поиск научной литературы по запросу пользователя (статьи, книги, исследования) и скачиваю файлы целиком — обязательно сохраняю их в библиотеку 13-33.**

Workflow:
1. Скачиваю файл локально (PDF/EPUB/DOCX) во временное место (`%TEMP%` или текущая директория)
2. **Сразу же копирую/перемещаю в правильный wing на Z:** (RaiDrive должен быть смонтирован):
   - **Научная статья / препринт / исследование** → `Z:\inbox\articles\<автор>-<краткое-имя>.<ext>`
   - **Книга** (монография, учебник, классическая работа) → `Z:\inbox\books\<автор>-<краткое-имя>.<ext>`
   - **Если непонятен тип** или источник смешанный → `Z:\inbox\misc\` с пояснительным именем
3. Имена файлов — `<автор>-<краткое-имя-без-пробелов>.<ext>`. Транслит русских имён или оригинал — не критично, главное чтобы было **узнаваемо при /library_search**
4. Через ~30 сек uploader на сервере подхватит файл, распарсит и зальёт в MemPalace
5. В ответе пользователю **упоминаю**: "также сохранил в библиотеку 13-33 → wing `<имя>`"

Если Z:\ не смонтирован (нет RaiDrive / другой машины) — сохраняю локально и **прямо говорю**: "файл лежит в `<путь>` — перетащи в `Z:\inbox\<wing>\` чтобы попал в библиотеку".

**Не дублируй** — если я уже знаю что точно такая же статья есть (по DOI / точному названию) — сначала проверяю через `/library_search` или `mempalace_search` mcp, прежде чем грузить.

**Не сохраняй мусор** — обзорные статьи в Wikipedia, новости, блог-посты не идут в библиотеку. Только **цельные академические тексты** (peer-reviewed, монографии, главы из книг).

### Rule: дайджесты и newsletters по нейронаукам

**Когда пользователь заказывает дайджест/обзор по нейронаукам, нейропластичности, психонейроиммунологии или смежным темам — итоговый дайджест автоматически сохраняется в `Z:\inbox\misc\<дата>-<тема>.md`.**

Это касается:
- Дайджестов по запросу ("сделай обзор последних работ по X")
- Newsletter-стиля сводок ("что нового в нейронауках за месяц")
- Кураторских подборок ссылок на исследования (с краткими summary'ями)

Имя файла: `digest-YYYY-MM-DD-<тема>.md` (пример: `digest-2026-05-03-neuroplasticity-talktherapy.md`).

Внутри — markdown с:
- заголовком и датой
- 5-15 ключевых работ с DOI/ссылкой и 2-3 предложениями summary каждая
- общими выводами (если уместно)

Через ~30 сек uploader зальёт это в MemPalace в wing `misc`. Потом найдётся через `/library_search wing:misc <тема>`.
