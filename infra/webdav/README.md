# WebDAV — общий диск для контента 13-33

Точка входа: `https://drive.13-33.pro/` (basic auth)

## Что это

Сетевой диск, монтируется на любое устройство как обычная папка. Файлы попадают
в volume `mempalace_uploads`, откуда bulk-uploader (Phase 5I.4) подхватывает и грузит
в MemPalace.

## Структура каталога (рекомендуемая)

```
/                       (WebDAV root)
├── inbox/              — drop-zone, сюда кладёшь новые файлы
│   ├── books/          — книги (PDF/EPUB/DOCX)
│   ├── articles/       — научные статьи
│   ├── 13-33main/      — наши проверенные тексты
│   ├── 13-33pubs/      — опубликованные посты
│   ├── 13-33scenarios/ — сценарии
│   ├── 13-33interviews/— интервью
│   └── misc/           — остальное
├── processed/          — после успешной загрузки в MemPalace (auto-move)
└── failed/             — что не парсится (auto-move с error.log рядом)
```

## Как монтировать

### Windows
1. File Explorer → "This PC" → правый клик → **Map network drive**
2. Drive letter: `Z:` (любая)
3. Folder: `https://drive.13-33.pro/`
4. ✓ Connect using different credentials
5. Username: `13-33` (или твой логин)
6. Password: см. .env → `WEBDAV_PASSWORD`

### Mac
1. Finder → меню Go → **Connect to Server** (`Cmd+K`)
2. `https://drive.13-33.pro/`
3. Connect As: Registered User → credentials

### iOS / iPadOS
1. Files app → ... → **Connect to Server**
2. `https://drive.13-33.pro/`
3. Credentials

### Linux (CLI mount)
```bash
sudo apt install davfs2
sudo mkdir /mnt/13-33
sudo mount -t davfs https://drive.13-33.pro/ /mnt/13-33
```

### Через браузер (только просмотр, не для регулярной работы)
Перейди на `https://drive.13-33.pro/`, введи credentials.

## Multi-user

Сейчас один логин/пароль из `.env`. Чтобы добавить второго пользователя —
монтируй свой `.htpasswd` файл в контейнер:

1. На сервере:
   ```bash
   docker run --rm httpd:alpine htpasswd -nb username password >> /opt/webdav/.htpasswd
   ```
2. Добавь в `docker-compose.yml`:
   ```yaml
   volumes:
     - /opt/webdav/.htpasswd:/etc/nginx/.htpasswd:ro
   ```
3. Recreate: `docker compose up -d --force-recreate`

## Лимит размера файла

Сейчас 4 GB на загрузку (см. `CLIENT_MAX_BODY_SIZE` в compose). Книги в PDF
обычно влезают. Если надо больше — увеличь.

## Безопасность

- TLS через Traefik (Let's Encrypt) — траффик зашифрован.
- Basic auth — простая защита от случайных глаз. Для серьёзной защиты добавь
  IP allowlist через Traefik middleware.
- Volume `mempalace_uploads` — единственное место, куда WebDAV пишет.
