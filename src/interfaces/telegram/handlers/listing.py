"""Handler /list — показать idea/draft/channel.

  /list ideas             — последние 10 идей
  /list ideas raw         — только сырые
  /list ideas processed   — только обработанные
  /list drafts            — последние 10 драфтов
  /list drafts review     — на ревью
  /list channels          — все каналы
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


HELP = (
    "Команды:\n"
    "  `/list ideas` — последние идеи\n"
    "  `/list ideas raw` — только raw\n"
    "  `/list drafts` — последние драфты\n"
    "  `/list drafts review` — на ревью\n"
    "  `/list channels` — каналы\n"
)


async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    args = msg.text.replace("/list", "", 1).strip().split()
    if not args:
        await msg.reply_text(HELP, parse_mode="Markdown")
        return

    twenty = context.bot_data.get("twenty")
    if twenty is None:
        await msg.reply_text("⚠️ Twenty не подключён.")
        return

    cmd = args[0].lower()
    arg2 = args[1].lower() if len(args) > 1 else None

    try:
        if cmd in ("ideas", "idea"):
            items = await twenty.list_ideas(status=arg2, limit=10)
            if not items:
                await msg.reply_text("Идей нет.")
                return
            lines = [f"*Идеи* (показано {len(items)}):\n"]
            for i in items:
                short_id = i["id"][:8]
                desc = (i.get("description") or "")[:80]
                if len(desc) == 80:
                    desc += "…"
                lc = i.get("lifecycle") or "?"
                lines.append(f"• `{short_id}` [{lc}] {desc}")
            await msg.reply_text("\n".join(lines), parse_mode="Markdown")

        elif cmd in ("drafts", "draft"):
            items = await twenty.list_drafts(lifecycle=arg2, limit=10)
            if not items:
                await msg.reply_text("Драфтов нет.")
                return
            lines = [f"*Драфты* (показано {len(items)}):\n"]
            for d in items:
                short_id = d["id"][:8]
                ch_code = (d.get("channel") or {}).get("code", "?")
                lc = d.get("lifecycle") or "?"
                title = d.get("name") or "(без заголовка)"
                lines.append(f"• `{short_id}` [{ch_code}, {lc}] {title[:60]}")
            await msg.reply_text("\n".join(lines), parse_mode="Markdown")

        elif cmd == "channels":
            items = await twenty.list_channels(enabled_only=False)
            if not items:
                await msg.reply_text("Каналов нет.")
                return
            lines = ["*Каналы:*\n"]
            for c in items:
                mark = "✓" if c.get("enabled") else "✗"
                lines.append(f"{mark} `{c.get('code')}` — {c.get('name')} ({c.get('handle')})")
            await msg.reply_text("\n".join(lines), parse_mode="Markdown")

        else:
            await msg.reply_text(HELP, parse_mode="Markdown")

    except Exception as e:
        logger.exception("List handler failed")
        await msg.reply_text(f"❌ {e}")


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("list", list_handler))
