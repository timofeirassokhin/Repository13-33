# Listmonk для timofeirassokhin.com

## Первый запуск (init БД)

Listmonk требует разовой инициализации схемы БД. Делается так:

```bash
# Подними только БД
docker compose -f infra/tr-com/listmonk/docker-compose.yml up -d listmonk-db

# Жди пока healthy (~5 сек)
docker compose -f infra/tr-com/listmonk/docker-compose.yml ps

# Запусти init одноразово:
docker compose -f infra/tr-com/listmonk/docker-compose.yml run --rm listmonk \
  ./listmonk --install --idempotent --yes --config /dev/null

# Подними основной сервис
docker compose -f infra/tr-com/listmonk/docker-compose.yml up -d listmonk
```

После этого открой `https://mail-admin.timofeirassokhin.com` (basic-auth из общего `TRAEFIK_BASIC_AUTH`),
залогинься админ-пользователем `LISTMONK_ADMIN_USER` / `LISTMONK_ADMIN_PASSWORD`.

## Настройка SMTP (Unisender)

В админке Listmonk → Settings → SMTP → Add server:

- Host: `smtp.unisender.com`
- Port: `465` (TLS) или `587` (STARTTLS)
- Auth Protocol: Login
- Username: `${UNISENDER_SMTP_USER}` (обычно email)
- Password: `${UNISENDER_SMTP_PASSWORD}`
- TLS type: `TLS` если 465, `STARTTLS` если 587
- Skip TLS verification: **OFF**
- HELO hostname: `mail.timofeirassokhin.com`
- Email headers:
  - From: `${UNISENDER_FROM_NAME} <${UNISENDER_FROM_EMAIL}>`

Тестовое письмо: Settings → Send test email.

## DNS (Cloudflare)

Чтобы письма не падали в спам, добавить в Cloudflare DNS для `timofeirassokhin.com`:

1. **MX-запись** (если хочешь принимать почту через Unisender):
   ```
   timofeirassokhin.com.   MX  10  smtprelay.unisender.com.
   ```

2. **SPF** (TXT, root):
   ```
   v=spf1 include:_spf.unisender.com ~all
   ```

3. **DKIM** — Unisender выдаёт уникальную TXT-запись в кабинете → Настройки → DKIM. Скопировать туда.

4. **DMARC** (TXT, `_dmarc.timofeirassokhin.com`):
   ```
   v=DMARC1; p=none; rua=mailto:dmarc@timofeirassokhin.com; pct=100
   ```
   `p=none` — для прогрева. Через 2-3 недели после первой массовой рассылки и нулевых DMARC-репортов
   с проблемами поднимаем до `p=quarantine`, потом `p=reject`.

## Прогрев домена

Первые 2 недели:
- Шлём только подписчикам, которые явно подтвердили email (double opt-in)
- Объёмы: день 1 — 50 писем, день 3 — 200, день 7 — 500, день 14 — 2000
- Следим за Unisender Analytics (open rate >20%, bounce <2%, complaints <0.1%)

После прогрева можно слать большие рассылки без потери доходимости.
