"""Handler /iterate — переписать существующий Draft через Opus с учётом комментария.

Использование:
  /iterate <draft_id>                    — просто полировка
  /iterate <draft_id> сократи в 2 раза    — с инструкцией
  /iterate <draft_id> сделай конкретнее, убери философствование
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.services.brand_voice import BRAND_VOICE_SYSTEM, HUMANIZER_SYSTEM, CHANNEL_RULES

logger = logging.getLogger(__name__)


HELP = (
    "Переписать драфт через Opus (премиум-модель):\n"
    "  `/iterate <draft_id>` — просто полировка\n"
    "  `/iterate <draft_id> комментарий` — с твоей правкой\n\n"
    "Примеры комментариев:\n"
    "  «сократи в 2 раза»\n"
    "  «убери философствование, сделай конкретнее»\n"
    "  «добавь личное наблюдение»\n"
    "  «финал слабый, переделай»\n\n"
    "draft_id можно сократить до первых 6-8 символов."
)


ITERATE_INSTRUCTIONS = """Твоя задача — переписать готовый драфт, учитывая комментарий автора
(если он есть). Это финальная итерация перед публикацией: текст должен быть лучше предыдущего,
естественнее, более авторским.

Что важно:
- Ты НЕ начинаешь с нуля — берёшь существующий драфт как основу.
- Сохраняешь конкретные детали: цитаты, имена, факты, специфические образы.
- Если комментарий автора есть — выполняй его буквально (сократить → сократи; убрать философствование → убери; и т.д.).
- Если комментария нет — твоя задача найти и улучшить слабые места:
    * слишком гладкие куски → добавь шероховатость
    * абстракцию → конкретный образ
    * резюме-финал → открытое окончание
    * параллельные конструкции → проза без симметрии
    * филлеры → удали
- Размер текста должен соответствовать каналу.
- Возвращай ТОЛЬКО переписанный текст, без вступлений и комментариев.
"""


def _format_channel_for_prompt(channel: dict) -> str:
    code = channel.get("code", "tg")
    rules = CHANNEL_RULES.get(code, CHANNEL_RULES["tg"])
    return f"{rules['name']} ({channel.get('handle')})\n{rules['format_hint']}"


async def iterate_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    args = msg.text.replace("/iterate", "", 1).strip()
    if not args:
        await msg.reply_text(HELP, parse_mode="Markdown")
        return

    parts = args.split(maxsplit=1)
    draft_partial = parts[0]
    user_comment = parts[1] if len(parts) > 1 else ""

    twenty = context.bot_data.get("twenty")
    llm = context.bot_data.get("llm")
    if twenty is None or llm is None:
        await msg.reply_text("⚠️ Twenty или LLM не подключены.")
        return

    # 1. Найти Draft
    matches = await twenty.find_drafts_by_partial_id(draft_partial)
    if not matches:
        await msg.reply_text(
            f"Не нашёл драфт по `{draft_partial}`. `/list drafts` покажет существующие.",
            parse_mode="Markdown",
        )
        return
    if len(matches) > 1:
        ids = "\n".join(f"  • `{d['id']}` — {d.get('name', '')[:60]}" for d in matches)
        await msg.reply_text(f"Несколько совпадений по `{draft_partial}`:\n{ids}", parse_mode="Markdown")
        return

    draft = matches[0]
    # Если получили из list_drafts (без полного body) — догрузим
    if not draft.get("body"):
        full = await twenty.get_draft(draft["id"])
        if full:
            draft = full

    if not draft.get("body"):
        await msg.reply_text("Не получилось загрузить тело драфта.")
        return

    channel = draft.get("channel") or {}
    idea = draft.get("idea") or {}

    # 2. Сформировать prompt для Opus
    prompt_parts = [
        f"## Канал\n{_format_channel_for_prompt(channel)}",
        f"## Тон\nТон {draft.get('tone') or '2'}",
    ]
    if (draft.get("topic") or {}).get("name"):
        prompt_parts.append(f"## Тема\n{draft['topic']['name']}")
    if idea.get("description"):
        prompt_parts.append(f"## Исходная идея\n{idea['description']}")
    prompt_parts.append(f"## Текущий драфт (нужно переписать)\n{draft['body']}")
    if user_comment:
        prompt_parts.append(f"## Комментарий автора\n{user_comment}")
    else:
        prompt_parts.append(f"## Комментарий автора\n(нет — просто отполируй и улучши слабые места)")
    prompt_parts.append(f"## Задача\n{ITERATE_INSTRUCTIONS}")

    user_prompt = "\n\n".join(prompt_parts)

    await msg.reply_text(
        f"🪶 Итерирую через Opus…\n_(~15-30 секунд, плюс humanizer)_",
        parse_mode="Markdown",
    )

    # 3. Opus пишет → humanizer чистит
    try:
        raw = await llm.premium(BRAND_VOICE_SYSTEM, user_prompt, max_tokens=2000)
        raw = raw.strip()
    except Exception as e:
        logger.exception("Opus call failed")
        await msg.reply_text(f"❌ Opus упал: {e}")
        return

    try:
        humanized = await llm.creative(HUMANIZER_SYSTEM, raw, max_tokens=2000)
        new_body = humanized.strip()
    except Exception:
        logger.exception("Humanizer pass failed")
        new_body = raw

    # 4. Сохранить как НОВЫЙ Draft с version+1, ссылающийся на ту же Idea и Channel
    try:
        new_version = (draft.get("version") or 1) + 1
        first_line = new_body.split("\n", 1)[0].strip()
        new_name = f"[v{new_version}] {first_line[:70]}"

        new_draft = await twenty.create_draft(
            idea_id=idea.get("id"),
            channel_id=channel.get("id"),
            body=new_body,
            tone=draft.get("tone") or "2",
            length=draft.get("length") or "medium",
            topic_id=(draft.get("topic") or {}).get("id"),
            author=f"agent:opus-iterate-v{new_version}",
            llm_model="premium",
        )
        # Переименовать с маркером версии
        try:
            await twenty.gql(
                """
                mutation Rename($id: UUID!, $data: DraftUpdateInput!) {
                  updateDraft(id: $id, data: $data) { id name version }
                }
                """,
                {"id": new_draft["id"], "data": {"name": new_name, "version": new_version}},
            )
        except Exception:
            logger.exception("Failed to set version/name on iterated draft")
    except Exception as e:
        logger.exception("Failed to save iterated draft")
        await msg.reply_text(f"❌ Не удалось сохранить итерацию: {e}")
        return

    preview = new_body if len(new_body) <= 3500 else new_body[:3500] + "\n…(обрезан превью)"
    comment_note = f"\n_комментарий: {user_comment}_" if user_comment else ""
    await msg.reply_text(
        f"✨ Итерация v{new_version} (Opus → humanizer)\n"
        f"draft id: `{new_draft['id']}`{comment_note}\n\n"
        f"{preview}",
        parse_mode="Markdown",
    )


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("iterate", iterate_handler))
