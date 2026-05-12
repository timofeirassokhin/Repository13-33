"""Voice handler — голосовое сообщение → Whisper ASR → text → search pipeline.

Telegram voice format: Opus в OGG-контейнере. Whisper Web Service принимает любые
аудио (ffmpeg внутри), просто шлём bytes под form-field `audio_file`.

API: POST /asr?task=transcribe&language=ru&output=json → {"text": "..."}
"""
from __future__ import annotations

import io
import logging

import aiohttp
from aiogram import F, Router
from aiogram.types import Message

from ..db import DB
from ..intent import IntentParser
from ..settings import Settings
from ..storage import Storage
from .search import _build_results_text, _build_keyboard, _send_all_pdfs

log = logging.getLogger(__name__)
router = Router(name="voice")


async def _transcribe(audio_bytes: bytes, settings: Settings) -> str:
    """POST к Whisper ASR. Возвращает строку (распознанный текст).

    NB: onerahmet/openai-whisper-asr-webservice возвращает JSON в теле, но
    отдаёт `Content-Type: text/plain` — поэтому resp.json(content_type=None)
    + fallback на raw-text если парсинг JSON упадёт.
    """
    import json as _json
    url = f"{settings.whisper_url}/asr"
    params = {
        "task": "transcribe",
        "language": settings.whisper_language,
        "output": "json",
        "encode": "true",   # сервер сам ffmpeg-нет audio (для opus/ogg)
    }
    timeout = aiohttp.ClientTimeout(total=settings.whisper_timeout_sec)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        data = aiohttp.FormData()
        data.add_field("audio_file", audio_bytes,
                       filename="voice.ogg",
                       content_type="audio/ogg")
        async with session.post(url, params=params, data=data) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Whisper HTTP {resp.status}: {body[:300]}")
            # Whisper web service quirk: иногда отдаёт raw text вместо JSON, иногда JSON.
            stripped = body.strip()
            if stripped.startswith("{"):
                try:
                    payload = _json.loads(stripped)
                    return (payload.get("text") or "").strip()
                except _json.JSONDecodeError:
                    pass
            return stripped


@router.message(F.voice | F.audio)
async def on_voice(
    msg: Message, db: DB, intent_parser: IntentParser,
    storage: Storage, settings: Settings,
) -> None:
    """Принимает Telegram voice или audio → Whisper → переиспользует search pipeline."""
    file_obj = msg.voice or msg.audio
    if file_obj is None:
        return

    duration = getattr(file_obj, "duration", 0) or 0
    if duration > 120:
        await msg.answer(
            f"🎤 Слишком длинное голосовое ({duration} сек). "
            "Максимум 2 минуты. Сократи или напиши текстом."
        )
        return

    await msg.chat.do("record_voice")
    bot = msg.bot
    assert bot is not None

    # Download audio bytes from Telegram → BytesIO
    try:
        file_info = await bot.get_file(file_obj.file_id)
        buf = io.BytesIO()
        if file_info.file_path is None:
            await msg.answer("❌ Telegram не отдал путь к файлу.")
            return
        await bot.download_file(file_info.file_path, destination=buf)
        audio_bytes = buf.getvalue()
    except Exception as e:
        log.exception("download voice failed")
        await msg.answer(f"❌ Не удалось скачать голосовое: <code>{type(e).__name__}</code>")
        return

    if len(audio_bytes) < 200:
        await msg.answer("❌ Аудио слишком короткое или пустое.")
        return

    # Whisper transcribe
    await msg.chat.do("typing")
    try:
        text = await _transcribe(audio_bytes, settings)
    except Exception as e:
        log.exception("whisper failed")
        await msg.answer(
            f"❌ Whisper ошибка: <code>{type(e).__name__}: {str(e)[:200]}</code>"
        )
        return

    if not text:
        await msg.answer("🎤 Не удалось разобрать аудио. Попробуй ещё раз или напиши текстом.")
        return

    await msg.answer(f"🎤 <i>Распознал:</i> «{text}»")

    # Reuse intent + search pipeline
    try:
        intent = await intent_parser.parse(text)
    except Exception as e:
        log.exception("intent parse failed")
        await msg.answer(f"❌ LLM intent fail: <code>{type(e).__name__}: {e}</code>")
        return

    action = intent.get("action", "unclear")
    if action == "help":
        from .common import HELP
        await msg.answer(HELP)
        return
    if action == "unclear":
        expl = intent.get("explanation_ru", "Не смог разобрать запрос.")
        await msg.answer(f"🤔 {expl}")
        return

    if action == "stats":
        totals = await db.totals()
        brand_filter = intent.get("brand")
        if brand_filter:
            cats = await db.category_counts(brand=brand_filter)
            lines = [f"<b>📊 {brand_filter}</b>", ""]
            for c in cats[:15]:
                lines.append(f"  • <code>{c.category}</code> — {c.total:,}".replace(",", " "))
        else:
            cats = await db.category_counts()
            lines = [
                "<b>📊 Каталог</b>", "",
                f"<b>Всего:</b> {totals['total']:,}".replace(",", " "),
                f"<b>С PDF:</b> {totals['with_ds']:,}".replace(",", " "),
                f"<b>PDF файлов:</b> {totals['total_pdfs']:,}".replace(",", " "),
                "",
                "<b>Top-10 категорий:</b>",
            ]
            for c in cats[:10]:
                lines.append(f"  • <code>{c.category}</code> — {c.total:,}".replace(",", " "))
        await msg.answer("\n".join(lines))
        return

    # action == "search"
    limit = min(intent.get("limit") or settings.default_search_limit, 25)
    products = await db.search_products(
        brand=intent.get("brand"),
        category=intent.get("category"),
        keywords=intent.get("keywords") or [],
        has_pdf=intent.get("has_pdf"),
        has_ru=intent.get("has_ru"),
        limit=limit,
    )
    total = await db.search_count(
        brand=intent.get("brand"),
        category=intent.get("category"),
        keywords=intent.get("keywords") or [],
        has_pdf=intent.get("has_pdf"),
        has_ru=intent.get("has_ru"),
    )
    text_out = _build_results_text(intent, products, total)
    kb = _build_keyboard(products, page=0, has_more=total > limit) if products else None
    await msg.answer(text_out, reply_markup=kb, disable_web_page_preview=True)

    if intent.get("send_pdfs") and products:
        await _send_all_pdfs(msg, products, storage, settings)
