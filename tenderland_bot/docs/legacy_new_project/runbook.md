# Server Runbook

## Bootstrap

Recommended baseline:

- Ubuntu 22.04 or 24.04 LTS.
- 2 GB RAM minimum for Twenty; 4 GB+ preferred once tender jobs run.
- Docker Engine and Docker Compose plugin.
- Public domain with HTTPS reverse proxy for production.

## Environment

Copy `.env.example` to `.env` and set:

- `SERVER_URL` to the public Twenty URL.
- `APP_SECRET` from `openssl rand -base64 32`.
- `PG_DATABASE_PASSWORD` without special characters for Twenty compatibility.
- `TENDER_DATABASE_PASSWORD`.
- `TENDERLAND_API_TOKEN` when credentials are available.
- `TWENTY_API_TOKEN` after creating the integration token in Twenty.

## Deploy

```bash
docker compose pull
docker compose up -d --build
docker compose ps
```

## Health Checks

```bash
curl http://localhost:3000/healthz
curl http://localhost:8080/healthz
```

## Logs

```bash
docker compose logs -f twenty-server
docker compose logs -f twenty-worker
docker compose logs -f tender-monitor
```

## Backups

Twenty database:

```bash
docker exec gluvex-twenty-db-1 pg_dump -U postgres default > backups/twenty_$(date +%Y%m%d).sql
```

Tender monitor database:

```bash
docker exec gluvex-tender-db-1 pg_dump -U tender tender_monitor > backups/tender_monitor_$(date +%Y%m%d).sql
```

Keep local rolling backups and copy encrypted backups off-server.

## Restore Sketch

1. Stop dependent services.
2. Restore the target database with `psql`.
3. Start services again.
4. Check health endpoints and sample CRM records.

## Production HTTPS

Twenty's self-hosting docs recommend setting `SERVER_URL` to the exact external URL users open in the browser. In production, put the stack behind a reverse proxy with SSL termination and set:

```env
SERVER_URL=https://crm.example.com
```

The tender monitor can remain private on the Docker network unless an external API is needed.

