# MemPalace для 13-33

Серверный экземпляр MemPalace — отдельный от твоей локальной палаты.
Хранит контент 13-33 и источники для producer-агента.

## Wings (структура)

| Wing | Что туда |
|---|---|
| `books` | Книги полным текстом |
| `articles` | Научные статьи и исследования (внешние) |
| `13-33pubs` | Опубликованные посты 13-33 (auto-fill из publication workflow) |
| `13-33scenarios` | Сценарии — для видео, подкастов |
| `13-33interviews` | Интервью с экспертами, расшифровки |
| `13-33` | Основной контент 13-33 — статьи, распаковки, исследования |
| `13-33drafts` | Драфты в работе (параллельно с Twenty.Drafts) |
| `misc` | Идеи, заметки, случайные тексты |

Wings создаются на лету (при первом drawer). `init_wings.py` создаёт placeholder-drawer
в каждом wing'е, чтобы они были видны в `/wings` сразу.

## HTTP API

База: `http://mempalace:8080` (внутри docker-сети `proxy`).

| Метод | Endpoint | Зачем |
|---|---|---|
| GET | `/health` | проверка |
| GET | `/wings` | список wings + счётчик drawers |
| POST | `/drawer` | добавить drawer (`{content, wing, room?, title?, tags[]}`) |
| GET | `/drawer/{id}` | получить drawer |
| DELETE | `/drawer/{id}` | удалить |
| POST | `/search` | семантический поиск (`{query, wing?, n_results?}`) |
| POST | `/kg/add` | добавить triple в knowledge graph |
| POST | `/kg/query` | запрос связей по сущности |
| GET | `/kg/stats` | статистика KG |

## Использование из бота / агентов

```python
import httpx
async with httpx.AsyncClient(base_url="http://mempalace:8080") as c:
    # Добавить
    r = await c.post("/drawer", json={
        "content": "Полный текст статьи или книги",
        "wing": "articles",
        "room": "psychology",
        "title": "Юнг — психология переноса",
    })
    
    # Поиск
    r = await c.post("/search", json={
        "query": "что такое теневые аспекты гордыни",
        "wing": "books",
        "n_results": 5,
    })
```

## Как загружать контент

### Прямо в API (для текстов которые уже есть как text)

```bash
curl -X POST http://mempalace:8080/drawer \
  -H "Content-Type: application/json" \
  -d '{"content": "...", "wing": "13-33pubs", "title": "Пост от 2026-05-02"}'
```

### Через bulk-upload скрипт (Phase 5I.4 — TODO)

Будет читать файлы из директории, конвертировать PDF/DOCX/EPUB → markdown,
делить на семантические куски, грузить как drawers с правильными метаданными.

## Backup

Volume `mempalace_data` бекапится через restic вместе со всем `/var/lib/docker/volumes/`
(см. `infra/scripts/backup.sh`).

## Восстановление

После restic restore — `mempalace_data` volume содержит всю палату. Контейнер видит её
автоматически при старте.
