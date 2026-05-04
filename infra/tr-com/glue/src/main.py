"""Glue — webhook router для tr-com.

Роуты:
  POST /subscribe        — форма с сайта (email, имя, lang) → Listmonk + Twenty Contact
  POST /robokassa/result — Result URL Робокассы (server-to-server, проверка подписи Pass2)
  GET  /robokassa/success — редирект пользователя после оплаты (UI)
  GET  /robokassa/fail    — редирект пользователя при отмене (UI)
  GET  /health           — для healthcheck

Заглушки сейчас возвращают 200 без бизнес-логики.
По мере появления Robokassa-аккаунта и Twenty API-ключа — заполняем.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from aiohttp import web

from .config import load


log = logging.getLogger("glue")


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def subscribe(request: web.Request) -> web.Response:
    settings, _twenty, _rk, _lm = request.app["cfg"]
    payload: dict[str, Any] = await request.json()
    # Минимальная валидация — secret подписан клиентом сайта (статикой) или приходит из бота
    secret = request.headers.get("X-Glue-Secret", "")
    if settings.webhook_secret and secret != settings.webhook_secret:
        return web.json_response({"error": "bad secret"}, status=401)

    email = (payload.get("email") or "").strip().lower()
    name = (payload.get("name") or "").strip()
    lang = (payload.get("lang") or "ru").lower()
    if "@" not in email:
        return web.json_response({"error": "invalid email"}, status=400)

    log.info("subscribe email=%s name=%s lang=%s", email, name, lang)
    # TODO: Listmonk POST /api/subscribers
    # TODO: Twenty B createOneContact mutation
    return web.json_response({"status": "queued"})


def _robokassa_signature_check(payload: dict[str, str], pass2: str) -> bool:
    """Robokassa Result URL: подпись = MD5(OutSum:InvId:Pass2)"""
    out_sum = payload.get("OutSum", "")
    inv_id = payload.get("InvId", "")
    sig = payload.get("SignatureValue", "").lower()
    expected = hashlib.md5(f"{out_sum}:{inv_id}:{pass2}".encode()).hexdigest().lower()
    return sig == expected


async def robokassa_result(request: web.Request) -> web.Response:
    _settings, _twenty, rk, _lm = request.app["cfg"]
    payload = dict(await request.post())
    if not _robokassa_signature_check(payload, rk.pass2):
        log.warning("robokassa: bad signature inv=%s", payload.get("InvId"))
        return web.Response(text="bad sign", status=400)

    inv_id = payload.get("InvId", "")
    out_sum = payload.get("OutSum", "")
    log.info("robokassa OK inv=%s sum=%s", inv_id, out_sum)
    # TODO: пометить заказ оплаченным в Twenty B (Deal stage = Won)
    # TODO: добавить покупателя в сегмент Listmonk "купил X" → triggered welcome-серия
    return web.Response(text=f"OK{inv_id}")


async def robokassa_success(request: web.Request) -> web.Response:
    inv = request.query.get("InvId", "")
    return web.Response(
        text=f"<h1>Оплата принята.</h1><p>Заказ #{inv}.</p>",
        content_type="text/html",
    )


async def robokassa_fail(_: web.Request) -> web.Response:
    return web.Response(
        text="<h1>Оплата отменена.</h1><p>Можешь попробовать ещё раз — никаких списаний не было.</p>",
        content_type="text/html",
    )


def make_app() -> web.Application:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = web.Application()
    app["cfg"] = load()
    app.router.add_get("/health", health)
    app.router.add_post("/subscribe", subscribe)
    app.router.add_post("/robokassa/result", robokassa_result)
    app.router.add_get("/robokassa/success", robokassa_success)
    app.router.add_get("/robokassa/fail", robokassa_fail)
    return app


if __name__ == "__main__":
    settings, *_ = load()
    web.run_app(make_app(), host="0.0.0.0", port=settings.port)
