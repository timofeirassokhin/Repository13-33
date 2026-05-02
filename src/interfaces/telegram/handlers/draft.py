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
    HUMANIZER_SYSTEM,
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


async def _fetch_library_context(bot_data: dict, idea_description: str) -> str:
    """Достать топ-3 релевантных drawer из MemPalace для подмешивания в prompt.

    Без MemPalace или при ошибке — возвращает пустую строку, генерация продолжается без контекста.
    """
    mempalace = bot_data.get("mempalace")
    if mempalace is None:
        return ""
    try:
        results = await mempalace.search(idea_description, n_results=3, max_distance=1.3)
    except Exception:
        logger.exception("Mempalace search failed (non-fatal — генерируем без контекста)")
        return ""
    if not results:
        return ""
    parts = ["## Контекст из библиотеки 13-33"]
    parts.append(
        "Ниже релевантные фрагменты из нашего архива. Используй как фон и опору — "
        "помогают точнее попасть в смысл и язык. Не цитируй дословно если не указано явно."
    )
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        title = meta.get("title") or "(фрагмент)"
        wing = meta.get("wing", "?")
        snippet = (r.get("content") or "")[:1500]
        parts.append(f"\n### Источник {i}: {title} [{wing}]\n{snippet}")
    return "\n".join(parts)


async def _generate_one_variant(
    bot_data: dict, idea: dict, channel: dict, variant: str
) -> tuple[str, dict]:
    """Генерирует один draft (вариант A или B), сохраняет в Twenty.

    Возвращает (body, draft_record).
    """
    llm = bot_data["llm"]
    twenty = bot_data["twenty"]

    code = channel["code"]
    tone = channel.get("defaultTone") or channel_default_tone(code)

    direction_name = (idea.get("direction") or {}).get("name") if idea.get("direction") else None
    topic_name = (idea.get("topic") or {}).get("name") if idea.get("topic") else None

    base_prompt = build_draft_prompt(
        idea_description=idea["description"],
        channel_code=code,
        channel_handle=channel.get("handle") or "",
        tone=str(tone),
        direction_name=direction_name,
        topic_name=topic_name,
        variant=variant,
    )

    # Подмешиваем контекст из MemPalace (топ-3 релевантных drawers)
    library_context = await _fetch_library_context(bot_data, idea["description"])
    user_prompt = f"{library_context}\n\n{base_prompt}" if library_context else base_prompt

    # Pass 1: Sonnet пишет под brand voice + подход
    raw = await llm.creative(BRAND_VOICE_SYSTEM, user_prompt, max_tokens=1800)
    raw = raw.strip()

    # Pass 2: humanizer вычищает AI-tells (em-dash, перечисления, fillers, резюме-финалы)
    try:
        humanized = await llm.creative(HUMANIZER_SYSTEM, raw, max_tokens=1800)
        body = humanized.strip()
    except Exception:
        logger.exception("Humanizer pass failed, using raw output")
        body = raw

    # Префиксуем имя в Twenty чтобы было видно вариант
    first_line = body.split("\n", 1)[0].strip()
    name_with_variant = f"[{variant.upper()}] {first_line[:70]}"

    draft = await twenty.create_draft(
        idea_id=idea["id"],
        channel_id=channel["id"],
        body=body,
        tone=str(tone),
        length="medium" if code in ("tg", "fb", "vk") else "long",
        author=f"agent:producer_v1:variant_{variant.upper()}",
    )
    # Override name to include variant marker
    try:
        await twenty.gql(
            """
            mutation Rename($id: UUID!, $data: DraftUpdateInput!) {
              updateDraft(id: $id, data: $data) { id name }
            }
            """,
            {"id": draft["id"], "data": {"name": name_with_variant}},
        )
        draft["name"] = name_with_variant
    except Exception:
        logger.exception("Failed to set variant in draft name")

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

    total = len(channels) * 2  # 2 варианта на канал
    await msg.reply_text(
        f"🪶 Генерирую {total} draft(ов) — {len(channels)} канал(а) × 2 варианта (A=рефлексия, B=расширение)…\n"
        f"_(Sonnet пишет → humanizer чистит, ~15-25 секунд на вариант)_",
        parse_mode="Markdown",
    )

    # 3. По каждому каналу — два варианта (A и B), оба через humanizer
    for ch in channels:
        for variant in ("A", "B"):
            try:
                body, draft = await _generate_one_variant(context.bot_data, idea, ch, variant)
                preview = body if len(body) <= 3500 else body[:3500] + "\n…(обрезан превью)"
                approach = "рефлексия" if variant == "A" else "расширение"
                await msg.reply_text(
                    f"📝 *{ch['name']}* — вариант *{variant}* ({approach}, tone {ch.get('defaultTone') or '2'})\n"
                    f"draft id: `{draft['id']}`\n\n"
                    f"{preview}",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.exception("Draft generation failed for channel %s variant %s", ch.get("code"), variant)
                await msg.reply_text(f"❌ {ch.get('name')} вариант {variant}: {e}")

    # 4. Обновить Idea.lifecycle = processed
    try:
        await twenty.update_idea_lifecycle(idea["id"], "processed")
    except Exception:
        logger.exception("Failed to update idea lifecycle")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("draft", draft_handler))
