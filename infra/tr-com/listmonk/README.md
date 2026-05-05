# Listmonk для timofeirassokhin.com

## Email-архитектура

Email-роли разделены между разными провайдерами:

| Роль | Провайдер | Почему |
|---|---|---|
| Личная почта (`mail@`, `hello@`, `book@` и алиасы) | **Яндекс 360 для бизнеса** | Бесплатно для 1 пользователя, отличная доходимость в РФ, IMAP/SMTP/web-клиент готовы |
| Newsletter — массовые рассылки | Отдельный ESP (**Sendsay** для РФ / Resend для международной) | Нужен прогретый IP-пул и DKIM, провайдер уже всё это даёт |
| Транзакционные (welcome, подтверждения) | Тот же ESP что и newsletter | На старте простой; позже можно перевести на Unisender REST API |

**Свой mail-сервер не поднимаем** — RU-VPS IP с большой вероятностью на блок-листах Gmail/Mail.ru, восстановление репутации годами не оправдает себя.

## Первый запуск Listmonk (init БД)

```bash
docker compose -f infra/tr-com/listmonk/docker-compose.yml up -d listmonk-db
# жди healthy ~5 сек
docker compose -f infra/tr-com/listmonk/docker-compose.yml run --rm listmonk \
  ./listmonk --install --idempotent --yes --config /dev/null
docker compose -f infra/tr-com/listmonk/docker-compose.yml up -d listmonk
```

Открой `https://mail-admin.timofeirassokhin.com/` (basic-auth от Traefik из общего `TRAEFIK_BASIC_AUTH`).
В UI Listmonk создаёт superadmin при первом заходе.

## Настройка SMTP в Listmonk

В админке Listmonk → **Settings → SMTP → Add server**:

- **Host:** значение из `ESP_SMTP_HOST` (`smtp.sendsay.ru`, `smtp.resend.com` или другое)
- **Port:** `465` (TLS) или `587` (STARTTLS)
- **Auth Protocol:** `Login`
- **Username:** `ESP_SMTP_USER`
- **Password:** `ESP_SMTP_PASSWORD`
- **TLS type:** `TLS` если 465, `STARTTLS` если 587
- **Skip TLS verification:** OFF
- **HELO hostname:** `timofeirassokhin.com`
- **Email headers:** From: `${ESP_FROM_NAME} <${ESP_FROM_EMAIL}>`

Тестовое письмо: Settings → Send test email.

## DNS в Cloudflare для timofeirassokhin.com

### Личная почта (после Яндекс 360 wizard)

Яндекс 360 wizard сам подскажет какие записи добавить. Типовой набор:

```
@   MX  10  mx.yandex.net.
@   TXT     v=spf1 redirect=_spf.yandex.net
mail._domainkey  TXT  v=DKIM1; k=rsa; p=<выдаст Яндекс>
_dmarc  TXT  v=DMARC1; p=none; rua=mailto:mail@timofeirassokhin.com; pct=100
```

Если планируем **слать рассылки тоже через свой домен** (а не через subdomain ESP) —
SPF нужно расширить чтобы покрывал и Яндекс, и ESP:

```
@   TXT     v=spf1 include:_spf.yandex.net include:<ESP-spf-host> ~all
```

(У Sendsay: `include:sendsay.ru`. У Resend: `include:_spf.resend.com`. Замени когда выберешь ESP.)

### DKIM для рассылок (отдельная запись)

ESP даст уникальную TXT-запись на selector типа `selector1._domainkey.timofeirassokhin.com`
(имя селектора зависит от ESP). Прописываем как есть.

### DMARC

`p=none` на старте (только репорты, без блокировок). После 2-3 недель прогрева и нулевых
проблем поднимаем до `p=quarantine`, потом `p=reject`.

## Прогрев домена для рассылок

Первые 2 недели:
- Только подтвердившие email подписчики (double opt-in включён в Listmonk по умолчанию)
- Объёмы: день 1 — 50 писем, день 3 — 200, день 7 — 500, день 14 — 2000
- Метрики из ESP-кабинета: open rate >20%, bounce <2%, complaints <0.1%

После прогрева можно делать большие рассылки без потери доходимости.
