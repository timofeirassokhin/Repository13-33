"""/start, /help, /stats — статичные команды."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from ..db import DB

router = Router(name="common")


WELCOME = """\
<b>📚 Gluvex Library</b>

Каталог приборов и брошюр Gluvex. Напиши <i>что ищешь</i> человеческим языком,
бот разберёт запрос, найдёт записи в каталоге и отдаст PDF брошюры.

<b>Примеры:</b>
• <code>тройные квадрупольные масс-спектрометры Шимадзу</code>
• <code>покажи брошюры на Orbitrap</code>
• <code>что у нас есть по Sciex</code>
• <code>центрифуги Sartorius с РУ</code>
• <code>хроматографы Шимадзу серии Nexera</code>

<b>Команды:</b>
/stats — общая статистика каталога
/brands — список брендов с числом записей
/help — это сообщение
"""


HELP = WELCOME


@router.message(CommandStart())
async def cmd_start(msg: Message) -> None:
    await msg.answer(WELCOME)


@router.message(Command("help"))
async def cmd_help(msg: Message) -> None:
    await msg.answer(HELP)


@router.message(Command("stats"))
async def cmd_stats(msg: Message, db: DB) -> None:
    totals = await db.totals()
    cats = await db.category_counts()
    text_lines = [
        "<b>📊 Каталог Gluvex — статистика</b>",
        "",
        f"<b>Всего записей:</b> {totals['total']:,}".replace(",", " "),
        f"<b>Уникальных брендов:</b> {totals['brands']:,}".replace(",", " "),
        f"<b>С PDF брошюрами:</b> {totals['with_ds']:,}".replace(",", " "),
        f"<b>Всего PDF в storage:</b> {totals['total_pdfs']:,}".replace(",", " "),
        f"<b>Agilent stubs (sitemap):</b> {totals['agilent_stubs']:,}".replace(",", " "),
        "",
        "<b>Top-10 категорий:</b>",
    ]
    for c in cats[:10]:
        text_lines.append(f"  • <code>{c.category}</code> — {c.total:,}".replace(",", " "))
    await msg.answer("\n".join(text_lines))


@router.message(Command("brands"))
async def cmd_brands(msg: Message, db: DB) -> None:
    brands = await db.brand_counts(top=30)
    if not brands:
        await msg.answer("В каталоге пока пусто.")
        return
    lines = ["<b>🏷 Бренды в каталоге</b> (top-30)", ""]
    for b in brands:
        marker_ds = f" 📄{b.with_ds}" if b.with_ds else ""
        marker_ru = f" 🇷🇺{b.with_ru}" if b.with_ru else ""
        lines.append(f"  • <b>{b.brand}</b> — {b.total:,}".replace(",", " ") + marker_ds + marker_ru)
    lines.append("")
    lines.append("📄 = записи с PDF, 🇷🇺 = с активным РУ Росздравнадзора")
    await msg.answer("\n".join(lines))
