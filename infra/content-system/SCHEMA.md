# Content System — Schema (13-33)

База данных контента + распределение по каналам.
Реализуется как **custom objects в Twenty CRM** (хранилище + API).

## Каналы 13-33

| ID | Тип | Адрес | API | Ограничения |
|---|---|---|---|---|
| `tg` | Telegram-канал | `t.me/prostranstvo1333` | Bot API (`@claw1333_bot` admin) | до 4096 знаков, 1 фото или альбом до 10 |
| `fb` | Facebook Page | `facebook.com/profile.php?id=61561590630465` | Blotato (handles Facebook Graph API) | до 63206 знаков, 1 фото/видео или альбом |
| `vk` | VK группа | `vk.com/club229213865` (group_id `229213865`) | VK API v5.199 (`wall.post`) | до 16384 знаков, до 10 вложений |
| `dzen` | Яндекс.Дзен | profile id `69f4c15949f7d66770f252c0` | OAuth Publisher API (fallback: Playwright) | без жёсткого лимита, требует обложку 1100×600 |
| `site` | Сайт `13-33.pro` | git commit в `infra/sites/13-33.pro/site/src/content/posts/` | через файлы, не API | без ограничений |

## Сущности (custom objects)

### `Direction` — направление (top-level)

Три ключевых направления Пространства 13-33. Должны быть заведены **до** Topic и Idea.

| Поле | Тип | Заметки |
|---|---|---|
| id | uuid | |
| name | string | напр. "Психология", "Духовные практики", "Философия" — точные названия определит владелец |
| slug | string | `psychology`, `spiritual`, `philosophy` |
| description | text | для какой аудитории, какой угол |
| color | enum | один из 7 брендовых: `primary/blue/teal/brick/coral/olive/vanilla` |
| default_ornament | enum | `morris/mandala_general/mandala_tibetan/vajra/ashtamangala/none` |
| is_active | bool | |
| topic_count | int | автоматически |

### `Topic` — тема внутри Direction

| Поле | Тип | Примеры |
|---|---|---|
| id | uuid | |
| name | string | "Тревога", "Сепарация", "Тантра", "Экзистенциальная свобода" |
| slug | string | `anxiety`, `separation`, `tantra`, `freedom` |
| description | text | |
| direction_id | FK → Direction | **обязательное** |
| color | enum | переопределяет direction.color, если задан |
| ornament | enum | переопределяет direction.default_ornament |
| is_active | bool | |
| post_count | int | автоматически |

### `Idea` — сырая идея / общая заметка

Может быть привязана к Topic и/или Direction, или висеть free (если идея не разложилась
по темам — будет в "inbox", потом разнесём).

| Поле | Тип | Заметки |
|---|---|---|
| id | uuid | |
| title | string | автоматически по первой строке |
| description | text | полный текст идеи |
| source | enum | `telegram_bot`, `voice`, `manual`, `email`, `web_clip` |
| topic_id | FK → Topic | nullable; если есть — direction берётся отсюда |
| direction_id | FK → Direction | nullable; ставится отдельно, если topic ещё не присвоен |
| status | enum | `raw`, `processed`, `archived`, `dropped` |
| captured_at | timestamp | |
| processed_at | timestamp | когда producer-агент превратил в Draft |
| reference_urls | string[] | если идея пришла из ссылки/статьи |
| embedding_qdrant_id | string | uuid в Qdrant для дедупа и semantic search |
| created_by | string | telegram_user_id или "agent" |

### `Draft` — конкретный текст под канал

| Поле | Тип | Заметки |
|---|---|---|
| id | uuid | |
| idea_id | FK → Idea | источник |
| topic_id | FK → Topic | |
| channel_id | FK → Channel | в какой канал |
| title | string | для сайта; для соцсетей пусто |
| body | text (markdown) | основной текст |
| tone | enum | `1` (душевный) / `2` (живой) |
| length | enum | `short`, `medium`, `long` |
| asset_ids | FK[] → Asset | прикреплённые медиа |
| status | enum | `draft`, `review`, `approved`, `scheduled`, `published`, `failed` |
| review_notes | text | от человека, если правки |
| author | string | "producer_agent_v1", "human:timofei" |
| llm_model | string | какой модель писал, для статистики |
| scheduled_at | timestamp | если status=scheduled |
| published_at | timestamp | если status=published |
| publication_url | string | ссылка на пост после публикации |
| version | int | для апдейтов |

### `Channel` — публикационная площадка

| Поле | Тип | Значение |
|---|---|---|
| id | uuid | |
| code | string | `tg`, `vk`, `dzen`, `site`, ... |
| name | string | "Telegram-канал", "VK группа" |
| type | enum | `telegram`, `vk`, `dzen`, `site`, `instagram`, `x`, ... |
| handle | string | `@prostranstvo1333` |
| api_endpoint | string | если нужно |
| credentials_ref | string | имя в `.env` (например, `VK_GROUP_TOKEN`) |
| char_limit | int | |
| supported_assets | enum[] | `image`, `video`, `audio`, `gallery` |
| default_tone | enum | `1` или `2` (по умолчанию для канала) |
| enabled | bool | |
| post_count | int | автоматически |

### `Asset` — медиа-файл

| Поле | Тип | Заметки |
|---|---|---|
| id | uuid | |
| type | enum | `image`, `video`, `audio`, `document` |
| storage | enum | `git` (для site), `s3`, `local` (volume на сервере) |
| path | string | относительный путь или URL |
| width | int | |
| height | int | |
| alt_text | string | для доступности |
| caption | string | |
| generated_by | enum | `canvas-design`, `algorithmic-art`, `human`, `external` |
| ornament_used | enum | `morris/mandala_general/mandala_tibetan/vajra/ashtamangala/none` |
| color_palette | string[] | список HEX, использованных в макете |
| linked_drafts | FK[] → Draft | где использовался |
| created_at | timestamp | |

### `Publication` — расписание и факт публикации

| Поле | Тип | Заметки |
|---|---|---|
| id | uuid | |
| draft_id | FK → Draft | |
| channel_id | FK → Channel | |
| scheduled_at | timestamp | UTC |
| status | enum | `pending`, `posting`, `posted`, `failed`, `cancelled` |
| result_url | string | после публикации |
| error | text | если failed |
| attempt_count | int | |
| engagement | json | `{views, likes, shares, comments}` — обновляется n8n воркфлоу |
| last_metrics_at | timestamp | когда последний раз тянули метрики |

### `Series` — серии связанных публикаций

| Поле | Тип |
|---|---|
| id | uuid |
| name | string |
| description | text |
| drafts | FK[] → Draft (упорядоченно) |
| status | enum (`active`, `completed`, `paused`) |

## Связи

```
Direction (3)
   ↓
Topic
   ↓
Idea ──→ Topic, Direction
   ↓
Draft ──→ Idea, Topic, Channel, Asset[]
   ↓
Publication ──→ Draft, Channel
```

- Один **Idea** → **много Draft** (по одному на канал; на TG пишется иначе, чем на сайт).
- Один **Draft** → **одна Publication** (это конкретный факт публикации в конкретный момент в конкретном канале).
- **Channel** — отдельная ось, не зависит от Direction.

## Жизненный цикл идеи

```
  Telegram-бот /idea
        ↓
  Idea(status=raw)
        ↓ (cron каждые N минут)
  Producer-агент:
    - определяет Direction и Topic (по embedding или LLM)
    - генерирует Draft под каждый Channel.enabled
    - выбирает tone (1/2) по правилам канала
    - создаёт Publication (предлагает время)
    - проверяет brand-13-33 (тон, формат)
    - запускает canvas-design на Asset (если нужна обложка)
        ↓
  Draft(status=review)  +  Publication(status=pending)
        ↓
  Telegram-бот шлёт превью владельцу:
    "📝 Готов пост в TG-канал на завтра 9:00 — одобрить? /approve_<id>"
        ↓
  Owner approves → Draft(status=approved)
        ↓ (cron сравнивает scheduled_at с now)
  Publisher worker (n8n):
    - берёт Draft + Asset
    - адаптер для Channel.type
    - публикует
    - сохраняет result_url в Publication
        ↓
  Publication(status=posted)
        ↓ (через 1ч / 24ч / 7д)
  Metrics worker:
    - тянет engagement
    - обновляет Publication.engagement
        ↓
  Editor-агент еженедельно:
    - анализирует engagement
    - подсказывает Topic, которые "зашли"
    - предлагает следующие идеи
```

## Креды и доступы — что нужно собрать

### Telegram-канал (`t.me/prostranstvo1333`)
- [x] Bot token уже есть (`@claw1333_bot`)
- [ ] **Бота добавить администратором** в канал с правом «Публиковать сообщения»
- [ ] **Channel ID** — получим автоматически после добавления бота (через `getChat` или `getUpdates`)

### Facebook (`profile.php?id=61561590630465`)
- [ ] **Подключить FB к Blotato** в его UI — Connect → Facebook → выбрать эту Page → разрешить
- [x] После этого Blotato держит токен сам, мы постим через `blotato_create_post`

### VK (`club229213865`)
- [x] group_id = `229213865`
- [ ] **Group access token** — `vk.com/club229213865 → Управление → Работа с API → Создать ключ → права:** Стена, Фото, Документы, Сообщения сообщества (не personal — именно ключ сообщества)
- [ ] Версия API: `5.199`

### Дзен (`profile id 69f4c15949f7d66770f252c0`)
- [ ] Проверить, открывается ли Publisher API для нашего профиля (нужны права `dzen.com:publisher` через https://oauth.yandex.ru/)
- [ ] Если API доступен — пройти OAuth, получить токен
- [ ] Если нет — fallback на Playwright: входить в Дзен.Студию, заполнять форму создания публикации

### Сайт
- [x] git ssh-ключ деплой-юзера (`agent`) на сервере уже работает
- [ ] решить: producer пишет напрямую в `/opt/stack/Repository13-33/infra/sites/.../posts/` и делает `docker compose up -d --build`, ИЛИ коммитит в репозиторий и сервер сам подтягивает (через webhook/cron). Я бы сделал второе — git как audit log.

## Producer-агент: правила выбора tone и channel

```
def choose_channels(idea, topic) -> list[Channel]:
  # дефолт — все включённые
  channels = active_channels()
  # если идея помечена "private" — только site
  if idea.private: return [site]
  return channels

def choose_tone(channel, topic) -> int:
  if channel.code == 'site': return 1   # лонг по умолчанию серьёзный
  if channel.code in ['tg', 'x']: return 2   # ежедневный — живой
  if topic.slug in ['death', 'grief', 'crisis']: return 1   # тяжёлая тема — даже в TG тон 1
  return channel.default_tone

def choose_length(channel) -> str:
  return {
    'site': 'long',
    'tg':   'medium',
    'vk':   'medium',
    'dzen': 'long',
    'x':    'short',
  }[channel.code]
```

## Что НЕ делаем сразу

- Series (серии длинных постов в нескольких частях) — отложим до 5-10 публикаций.
- Editor-агент с переписыванием постов по статистике — после 30+ публикаций, когда есть данные.
- A/B тестирование тонов — ещё позже, требует объёма.

## Следующие шаги

1. Заводим Channel записи руками в Twenty (4 строки) — чтобы было от чего отталкиваться
2. Заводим Idea / Topic / Draft / Asset / PublicationSlot custom objects в Twenty UI
3. Добавляю `/idea` команду в pa-bot
4. n8n воркфлоу: producer + scheduler + publishers
5. Тест end-to-end: одна идея → один пост в TG-канал
