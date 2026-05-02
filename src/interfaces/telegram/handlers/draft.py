"""Handler /draft — превращает Idea в Draft через Sonnet (creative) для одного канала.

Использование:
  /draft <idea_id> <channel_code>     — для конкретного канала
  /draft <idea_id>                    — для всех enabled каналов

idea_id можно сократить до первых 6 символов UUID (бот матчит по startswith).
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.services.brand_voice import (
    BRAND_VOICE_SYSTEM,
    build_draft_prompt,
    channel_default_tone,
)

logger = logging.getLogger(__name__)


HELP = (
    "Сгенерировать Draft из Idea:\n"
    "  `/draft <idea_id> <channel_code>` — для одного канала\n"
    "  `/draft <idea_id>` — для всех enabled каналов\n\n"
    "channel_code: tg, fb, vk, dzen, site\n"
    "idea_id можно сократить до первых 6 символов."
)


async def _resolve_idea(twenty, partial_id: str) -> dict | None:
    """Найти idea по полному UUID или по startswith."""
    direct = await twenty.get_idea(partial_id) if len(partial_id) == 36 else None
    if direct:
        return direct
    # fallback: ищем в последних 50 записях
    ideas = await twenty.list_ideas(limit=50)
    matches = [i for i in ideas if i.get("id", "").startswith(partial_id)]
    if len(matches) == 1:
        return await twenty.get_idea(matches[0]["id"])
    return None


async def _generate_draft_for_channel(
    bot_data: dict, idea: dict, channel: dict
) -> tuple[str, dict]:
    """Сгенерировать body + создать Draft в Twenty. Возвращает (body, draft_record)."""
    llm = bot_data["llm"]
    twenty = bot_data["twenty"]

    code = channel["code"]
    tone = channel.get("defaultTone") or channel_default_tone(code)

    direction_name = (idea.get("direction") or {}).get("name") if idea.get("direction") else None
    topic_name = (idea.get("topic") or {}).get("name") if idea.get("topic") else None

    user_prompt = build_draft_prompt(
        idea_description=idea["description"],
        channel_code=code,
        channel_handle=channel.get("handle") or "",
        tone=str(tone),
        direction_name=direction_name,
        topic_name=topic_name,
    )

    body = await llm.creative(BRAND_VOICE_SYSTEM, user_prompt, max_tokens=1500)
    body = body.strip()

    draft = await twenty.create_draft(
        idea_id=idea["id"],
        channel_id=channel["id"],
        body=body,
        tone=str(tone),
        length="medium" if code in ("tg", "fb", "vk") else "long",
    )
    return body, draft


async def draft_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    args = msg.text.replace("/draft", "", 1).strip().split()
    if not args:
        await msg.reply_text(HELP, parse_mode="Markdown")
        return

    twenty = context.bot_data.get("twenty")
    llm = context.bot_data.get("llm")
    if twenty is None or llm is None:
        await msg.reply_text("⚠️ Twenty или LLM не подключены.")
        return

    idea_partial = args[0]
    target_channel = args[1] if len(args) > 1 else None

    # 1. Найти Idea
    idea = await _resolve_idea(twenty, idea_partial)
    if not idea:
        await msg.reply_text(
            f"Не нашёл идею по `{idea_partial}`. Используй `/list ideas` чтобы увидеть список.",
            parse_mode="Markdown",
        )
        return

    # 2. Каналы — один или все enabled
    if target_channel:
        ch = await twenty.get_channel_by_code(target_channel)
        if not ch:
            await msg.reply_text(f"Канал `{target_channel}` не найден.", parse_mode="Markdown")
            return
        channels = [ch]
    else:
        channels = await twenty.list_channels(enabled_only=True)

    if not channels:
        await msg.reply_text("Нет включённых каналов.")
        return

    await msg.reply_text(
        f"🪶 Генерирую {len(channels)} draft(а) для идеи *{idea['name']}*…",
        parse_mode="Markdown",
    )

    # 3. По каждому каналу — сгенерировать draft, выслать пользователю
    for ch in channels:
        try:
            body, draft = await _generate_draft_for_channel(context.bot_data, idea, ch)
            preview = body if len(body) <= 3500 else body[:3500] + "\n…(обрезан превью)"
            await msg.reply_text(
                f"📝 *{ch['name']}* ({ch['code']}, tone {ch.get('defaultTone') or '2'})\n"
                f"draft id: `{draft['id']}`\n\n"
                f"{preview}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.exception("Draft generation failed for channel %s", ch.get("code"))
            await msg.reply_text(f"❌ {ch.get('name')}: {e}")

    # 4. Обновить Idea.lifecycle = processed
    try:
        await twenty.update_idea_lifecycle(idea["id"], "processed")
    except Exception:
        logger.exception("Failed to update idea lifecycle")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("draft", draft_handler))
