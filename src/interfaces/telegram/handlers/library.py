"""Handler /library_search и /library_wings — поиск в MemPalace 13-33."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


HELP = (
    "Поиск в архиве 13-33:\n"
    "  `/library_search <запрос>` — поиск по всему архиву\n"
    "  `/library_search wing:books <запрос>` — только в указанном wing\n"
    "  `/library_wings` — список wings + количество drawers\n\n"
    "Примеры:\n"
    "  `/library_search тревога и желание`\n"
    "  `/library_search wing:13-33main гордыня`"
)


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    args = msg.text.replace("/library_search", "", 1).strip()
    if not args:
        await msg.reply_text(HELP, parse_mode="Markdown")
        return

    # Парсим wing:foo
    wing_filter = None
    parts = args.split(maxsplit=1)
    if parts[0].startswith("wing:") and len(parts) > 1:
        wing_filter = parts[0][len("wing:"):]
        query = parts[1]
    else:
        query = args

    mempalace = context.bot_data.get("mempalace")
    if mempalace is None:
        await msg.reply_text("⚠️ MemPalace не подключён.")
        return

    try:
        results = await mempalace.search(query, wing=wing_filter, n_results=5)
    except Exception as e:
        logger.exception("Library search failed")
        await msg.reply_text(f"❌ {e}")
        return

    if not results:
        await msg.reply_text(
            f"Ничего не найдено по запросу «{query}»"
            + (f" в wing `{wing_filter}`" if wing_filter else "")
            + ".",
            parse_mode="Markdown",
        )
        return

    lines = [f"🔎 Найдено {len(results)} drawer(ов) по запросу «{query}»:\n"]
    for i, r in enumerate(results, 1):
        meta = r.get("metadata") or {}
        wing = meta.get("wing", "?")
        title = meta.get("title") or ""
        snippet = (r.get("content") or "")[:200].replace("\n", " ")
        if len(snippet) == 200:
            snippet += "…"
        distance = r.get("distance", 0)
        relevance = max(0, 100 - int(distance * 50))  # грубая оценка
        lines.append(
            f"*{i}. {title or '(без заголовка)'}* `[{wing}]` ~{relevance}%\n"
            f"   id: `{r['id']}`\n"
            f"   {snippet}\n"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:3900] + "\n…(обрезано)"
    await msg.reply_text(text, parse_mode="Markdown")


async def wings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    mempalace = context.bot_data.get("mempalace")
    if mempalace is None:
        await msg.reply_text("⚠️ MemPalace не подключён.")
        return

    try:
        wings = await mempalace.list_wings()
    except Exception as e:
        await msg.reply_text(f"❌ {e}")
        return

    lines = ["*Wings палаты 13-33:*\n"]
    for w in wings:
        # placeholder _init drawer не учитываем в "реальном" счёте
        real = max(0, w.get("drawer_count", 0) - 1)
        lines.append(f"  • `{w['wing']}` — {real} drawer(ов)")
    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("library_search", search_handler))
    app.add_handler(CommandHandler("library_wings", wings_handler))
