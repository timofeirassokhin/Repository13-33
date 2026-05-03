# preview.13-33.pro

Демо-стенд для прототипов сайта 13-33.pro.

## Что отдаёт

`html/index.html` — текущий логический прототип главной (тёмная палитра + ванильные карточки + коралловый CTA).
Если в `html/` положить любой другой `.html` или папку — он тоже будет доступен по соответствующему пути.

## Деплой

DNS: A-запись `preview.13-33.pro` → IP сервера (как у `13-33.pro`).

На сервере:

```bash
cd ~/infra
git pull
docker compose -f sites/preview.13-33.pro/docker-compose.yml --env-file .env up -d --build
```

После этого Traefik автоматически выпустит SSL-сертификат через Let's Encrypt и сайт будет доступен на https://preview.13-33.pro/.

## Обновление прототипа

Источник правды живёт в репо в `docs/13-33-website/02-prototype-home.html`. После правок:

```bash
cp docs/13-33-website/02-prototype-home.html infra/sites/preview.13-33.pro/html/index.html
git add -A && git commit -m "preview: update prototype" && git push
# на сервере:
git pull && docker compose -f sites/preview.13-33.pro/docker-compose.yml up -d --build
```

## Шрифты

Сейчас прототип использует Google Fonts (Bebas Neue, Manrope, Source Sans 3, Bodoni Moda).
Чтобы подключить лицензированные DIN 2014 и Myriad Pro:

1. Положи `.woff2` файлы в `html/fonts/`
2. В `html/index.html` раскомментируй блок `@font-face` в шапке
3. Пересобери контейнер

Они автоматически перекроют fallback благодаря порядку в font-stack.
