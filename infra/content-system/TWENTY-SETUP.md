# Twenty CRM — настройка Custom Objects для контент-системы

Эту инструкцию выполняешь **один раз руками через UI**, чтобы создать структуру
базы. Дальше всё через API / агентов автоматически.

URL: `https://crm.13-33.pro`

## Иерархия

```
Direction (3 направления, top-level)
   ↓
Topic (темы внутри Direction)
   ↓
Idea (сырая заметка, может ссылаться на Topic и/или Direction)
   ↓
Draft (текст под конкретный Channel; один Idea → много Draft)
   ↓
Publication (запланированная/состоявшаяся публикация)

Channel — отдельная ось, не зависит от Direction
Asset — опционально, медиа-файлы (можно отложить)
```

## Подготовка

1. Зайди в Twenty, авторизуйся.
2. Сверху справа — **аватар → Settings** (или иконка ⚙️ слева внизу).
3. **Data Model** → **+ Add Object** для каждого объекта.

Порядок создания **важен** (релейшены — снизу вверх):
1. **Channel** (без релейшенов, проще)
2. **Direction**
3. **Topic** (ссылается на Direction)
4. **Idea** (ссылается на Topic, Direction)
5. **Draft** (ссылается на Idea, Topic, Channel)
6. **Publication** (ссылается на Draft, Channel)
7. (опционально) **Asset**

---

## Объект 1: `Channel`

**Object settings:**
- Name (singular): `Channel`
- Name (plural): `Channels`
- Description: `Канал публикации (TG, FB, VK, Дзен, сайт)`
- Icon: `IconBroadcast`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `code` | Text | Required, unique (`tg`, `fb`, `vk`, `dzen`, `site`) |
| `type` | Select | Options: `telegram`, `facebook`, `vk`, `dzen`, `site`, `instagram`, `x`, `linkedin`, `threads` |
| `handle` | Text | Optional |
| `apiEndpoint` | Text | Optional |
| `credentialsRef` | Text | Optional, имя env-переменной |
| `charLimit` | Number | Optional |
| `defaultTone` | Select | Options: `1`, `2` |
| `enabled` | Boolean | Default: true |

(`name` создаётся Twenty автоматически.)

**После создания — добавь 5 записей:**

| name | code | type | handle | charLimit | defaultTone |
|---|---|---|---|---|---|
| Telegram-канал | tg | telegram | @prostranstvo1333 | 4096 | 2 |
| Facebook Page | fb | facebook | id=61561590630465 | 63206 | 2 |
| VK группа | vk | vk | club229213865 | 16384 | 2 |
| Дзен | dzen | dzen | id=69f4c15949f7d66770f252c0 | 100000 | 1 |
| Сайт 13-33.pro | site | site | 13-33.pro | 0 | 1 |

---

## Объект 2: `Direction`

**Object settings:**
- Name (singular): `Direction`
- Name (plural): `Directions`
- Description: `Top-level направление контента 13-33`
- Icon: `IconCompass`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `slug` | Text | Required, unique (`psychology`, `spiritual`, `philosophy`...) |
| `description` | Text | Optional |
| `color` | Select | Options: `primary`, `blue`, `teal`, `brick`, `coral`, `olive`, `vanilla` |
| `defaultOrnament` | Select | Options: `morris`, `mandala_general`, `mandala_tibetan`, `vajra`, `ashtamangala`, `none` |
| `isActive` | Boolean | Default: true |

**После создания — добавь 3 записи** (твои реальные направления). Если ещё не
определился с названиями — поставь рабочие `Direction 1/2/3` и переименуй потом.

---

## Объект 3: `Topic`

**Object settings:**
- Name: `Topic`
- Plural: `Topics`
- Description: `Тема внутри Direction`
- Icon: `IconTag`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `slug` | Text | Required, unique |
| `description` | Text | Optional |
| `color` | Select | те же 7 опций (переопределяет direction.color) |
| `ornament` | Select | те же 6 опций (переопределяет direction.defaultOrnament) |
| `isActive` | Boolean | Default: true |
| `direction` | **Relation** | Many-to-One → `Direction`, **Required** |

(`name` авто.)

---

## Объект 4: `Idea`

**Object settings:**
- Name: `Idea`
- Plural: `Ideas`
- Description: `Сырая идея для контента — заметка, мысль, ссылка`
- Icon: `IconBulb`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `description` | Long Text | Required |
| `source` | Select | Options: `telegram_bot`, `voice`, `manual`, `email`, `web_clip` |
| `status` | Select | Options: `raw` (default), `processed`, `archived`, `dropped` |
| `capturedAt` | Date Time | Default: now |
| `processedAt` | Date Time | Optional |
| `referenceUrls` | Text | Optional (если массив не работает — храни JSON-строку или одну ссылку) |
| `embeddingId` | Text | Optional, для линка с Qdrant |
| `createdByExternalId` | Text | Optional, telegram_user_id |
| `topic` | **Relation** | Many-to-One → `Topic`, Optional |
| `direction` | **Relation** | Many-to-One → `Direction`, Optional |

(`name` Twenty — это title идеи; берётся из первой строки.)

---

## Объект 5: `Draft`

**Object settings:**
- Name: `Draft`
- Plural: `Drafts`
- Description: `Готовый текст для одного канала`
- Icon: `IconFileText`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `body` | Long Text | Required |
| `tone` | Select | Options: `1`, `2` |
| `length` | Select | Options: `short`, `medium`, `long` |
| `status` | Select | Options: `draft` (default), `review`, `approved`, `scheduled`, `published`, `failed` |
| `reviewNotes` | Text | Optional |
| `author` | Text | "agent:producer_v1" / "human:timofei" |
| `llmModel` | Text | Optional |
| `scheduledAt` | Date Time | Optional |
| `publishedAt` | Date Time | Optional |
| `publicationUrl` | Link | Optional |
| `version` | Number | Default: 1 |
| `idea` | **Relation** | Many-to-One → `Idea`, Required |
| `topic` | **Relation** | Many-to-One → `Topic`, Optional |
| `channel` | **Relation** | Many-to-One → `Channel`, Required |

---

## Объект 6: `Publication`

**Object settings:**
- Name: `Publication`
- Plural: `Publications`
- Description: `Запланированная или состоявшаяся публикация`
- Icon: `IconCalendarTime`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `scheduledAt` | Date Time | Required |
| `status` | Select | Options: `pending` (default), `posting`, `posted`, `failed`, `cancelled` |
| `resultUrl` | Link | Optional |
| `errorMessage` | Text | Optional |
| `attemptCount` | Number | Default: 0 |
| `engagementViews` | Number | Default: 0 |
| `engagementLikes` | Number | Default: 0 |
| `engagementShares` | Number | Default: 0 |
| `engagementComments` | Number | Default: 0 |
| `lastMetricsAt` | Date Time | Optional |
| `draft` | **Relation** | Many-to-One → `Draft`, Required |
| `channel` | **Relation** | Many-to-One → `Channel`, Required |

---

## Объект 7 (опционально, можно сразу или потом): `Asset`

**Object settings:**
- Name: `Asset`
- Plural: `Assets`
- Description: `Медиа-файл — картинка, видео, обложка`
- Icon: `IconPhoto`

**Fields:**

| Field name | Type | Settings |
|---|---|---|
| `type` | Select | Options: `image`, `video`, `audio`, `document` |
| `storage` | Select | Options: `git`, `s3`, `local` |
| `path` | Text | Required, путь или URL |
| `width` | Number | Optional |
| `height` | Number | Optional |
| `altText` | Text | Optional |
| `caption` | Text | Optional |
| `generatedBy` | Select | Options: `canvas-design`, `algorithmic-art`, `human`, `external`, `canva`, `adobe-express` |
| `ornamentUsed` | Select | Options: `morris`, `mandala_general`, `mandala_tibetan`, `vajra`, `ashtamangala`, `none` |
| `colorPalette` | Text | Список HEX через запятую |

Связь Asset ↔ Draft многие-ко-многим — добавь в Draft поле `assets` как
Relation Many-to-Many → Asset (или сделаем через промежуточную сущность позже).

---

## Связи "обратной стороны"

После создания Twenty автоматически создаст обратные связи:
- `Direction.topics` (one-to-many)
- `Topic.ideas`, `Topic.drafts` (one-to-many)
- `Channel.drafts`, `Channel.publications` (one-to-many)
- `Idea.drafts` (one-to-many)
- `Draft.publications` (one-to-many)

Проверь, что они появились — если нет, в редакторе релейшена есть опция
"Create reverse relation".

---

## Что прислать мне

1. **API names всех 7 объектов** — Twenty иногда отличает display от API name
   (например, `Direction` → `direction` или `directions`). Найдёшь в каждом
   объекте → "API" вкладка вверху.
2. **Названия 3 Direction**, как ты их завёл (Psychology / Spiritual / Philosophy
   или твои варианты).
3. Сообщение **"всё создал"**.

После этого я начну писать `/idea` команду в боте + n8n адаптеры — они уже будут
обращаться к правильным API endpoints.

---

## API token (на сервере, чтобы я мог гонять GraphQL)

API key уже у меня есть. Сразу клади на сервер:

```bash
echo 'TWENTY_API_KEY=eyJhbGciOi... (полный токен)' | sudo tee -a /opt/stack/Repository13-33/infra/.env
```

(после деплоя ротируй: Settings → Developers → API Keys → Revoke + Generate new)

---

## Если что-то не получается

Twenty UI они активно меняют. Если не находишь нужную опцию (например, тип поля
"Long Text" или option-set вместо Select) — снимай скриншот, кидай, разберёмся.
