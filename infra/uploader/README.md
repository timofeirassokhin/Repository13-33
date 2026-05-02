# Bulk Uploader для MemPalace 13-33

Контейнер, который смотрит за `/uploads/inbox/<wing>/` (тот же volume, что у WebDAV)
и автоматически парсит файлы, чанкует и грузит в MemPalace.

## Workflow

1. Кладёшь файлы через WebDAV в `Z:\inbox\<wing>\some.pdf`
2. Uploader через 30 сек видит файл
3. Парсит → конвертирует в markdown → чанкит ~2000 знаков
4. Грузит каждый chunk в MemPalace как отдельный drawer
5. Перемещает оригинал в `processed/<wing>/`
6. Markdown-копия лежит в `markdown/<wing>/some.md` для прозрачности

Если что-то падает — оригинал летит в `failed/<wing>/` с `.error.log` рядом.

## Поддерживаемые форматы

| Ext | Парсер | Качество |
|---|---|---|
| `.pdf` | pymupdf | ⭐⭐⭐⭐ хорошо для большинства PDF |
| `.docx` | python-docx | ⭐⭐⭐⭐⭐ + сохраняет H1/H2/H3 |
| `.epub` | ebooklib | ⭐⭐⭐⭐ + структура заголовков |
| `.txt` | chardet+decode | ⭐⭐⭐⭐⭐ авто-детект кодировки |
| `.md` / `.markdown` | прямое чтение | ⭐⭐⭐⭐⭐ |
| `.rtf` | striprtf | ⭐⭐⭐ |

## Структура `/uploads`

Внутри volume `mempalace_uploads`:
```
/uploads/
├── inbox/
│   ├── books/                — wings создают подпапку
│   ├── articles/
│   ├── 13-33main/
│   ├── 13-33pubs/
│   ├── 13-33scenarios/
│   ├── 13-33interviews/
│   ├── 13-33drafts/
│   └── misc/
├── processed/                — успешно обработанные оригиналы
├── failed/                   — что не удалось распарсить (+ error.log)
└── markdown/                 — конвертированные .md копии
```

Если файл лежит прямо в `inbox/` (без подпапки), он попадает в `misc`.

## Команды

### Watch (по умолчанию)

Контейнер просто работает в режиме watch — каждые 30 сек проверяет inbox.

```bash
cd /opt/stack/Repository13-33/infra/uploader
docker compose up -d
docker compose logs -f uploader   # смотреть, что обрабатывает
```

### Process-all (одноразово)

Обработать всё что есть и выйти:
```bash
docker compose run --rm uploader python uploader.py process-all
```

### Process один файл/папку

```bash
docker compose run --rm uploader python uploader.py process /uploads/inbox/books/jung.pdf
```

## Метаданные drawer'ов

Для каждого chunk создаётся drawer с полями:
- `wing` = имя подпапки в inbox
- `room` = базовое имя файла (без расширения, обрезано до 60 символов)
- `title` = `<имя файла> (часть N/M)`
- `source_file` = относительный путь от `/uploads/`
- `added_by` = `bulk_uploader`
- `tags` = `["chunk_N_of_M"]`

Это позволяет потом группировать chunks по `room`, искать по `title`, видеть связь
chunks одного исходного документа.

## Правила чанкинга

- target ~2000 знаков (≈ 500-700 слов)
- overlap ~200 знаков для плавного перехода контекста
- Не режет по середине абзаца, если возможно
- Сверхдлинные абзацы режутся по предложениям

## Расширение

Добавить парсер для нового формата:
1. В `parsers.py` добавь функцию `parse_<ext>(path) -> str`
2. Добавь её в словарь `PARSERS`
3. Добавь нужные deps в `requirements.txt`
4. `docker compose build && docker compose up -d`
