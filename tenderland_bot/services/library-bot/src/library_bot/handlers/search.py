"""Свободно-текстовый поиск: text → intent (LLM) → DB → ответ + PDF."""
from __future__ import annotations

import logging
from typing import Any

from aiogram import F, Router
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.types import CallbackQuery

from ..db import DB, Product
from ..intent import IntentParser
from ..settings import Settings
from ..storage import Storage

log = logging.getLogger(__name__)
router = Router(name="search")


def _format_product_line(p: Product, idx: int) -> str:
    """Одна строка в результатах: '1. LCMS-8045 — Triple Quadrupole — 📄3 РУ✓'."""
    parts = [f"{idx}. <b>{p.model}</b>"]
    if p.display_name and p.display_name.lower() != p.model.lower():
        # обрезаем длинные display_name
        dn = p.display_name[:80]
        parts.append(f"— {dn}")
    badges = []
    if p.pdf_count:
        badges.append(f"📄{p.pdf_count}")
    if p.ru_status == "active":
        badges.append("🇷🇺")
    if badges:
        parts.append(" " + " ".join(badges))
    return " ".join(parts)


_SPEC_SKIP = {"summary_ru", "product_name", "name", "model", "manufacturer",
              "instrument_type", "product_type", "brand", "source_confidence", "ingest"}


def _fmt_val(v: Any) -> str:
    if isinstance(v, bool):
        return "да" if v else "нет"
    if isinstance(v, list):
        if len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            return f"{v[0]}–{v[1]}"
        return ", ".join(str(x) for x in v[:12])
    if isinstance(v, dict):
        return ", ".join(f"{k}: {x}" for k, x in list(v.items())[:8])
    return str(v)


def _format_specs(specs: dict) -> list[str]:
    """Рендер base_specs в читаемые строки карточки."""
    lines: list[str] = []
    summ = specs.get("summary_ru")
    if summ:
        lines.append(f"<i>{str(summ)[:550]}</i>")
    body: list[str] = []
    for k, v in specs.items():
        if k in _SPEC_SKIP or k in ("applications", "catalog_numbers"):
            continue
        if v in (None, "", [], {}):
            continue
        body.append(f"• <b>{k.replace('_', ' ')}:</b> {_fmt_val(v)}")
    if body:
        lines.append("")
        lines.append("<b>Характеристики:</b>")
        lines.extend(body[:24])
    apps = specs.get("applications")
    if apps:
        lines.append("")
        lines.append(f"🔬 <b>Применения:</b> {_fmt_val(apps)}")
    cats = specs.get("catalog_numbers")
    if cats:
        lines.append(f"🔖 <b>Каталожные №:</b> {_fmt_val(cats)[:240]}")
    return lines


def _format_product_card(p: Product) -> str:
    """Полная карточка позиции: шапка + характеристики/описание + datasheet."""
    lines = [f"<b>{p.brand}</b> — <b>{p.model}</b>"]
    if p.display_name and p.display_name.lower() != p.model.lower():
        lines.append(p.display_name[:140])
    meta = [f"кат: <code>{p.category}</code>"]
    if p.vendor_code:
        meta.append(f"арт: <code>{p.vendor_code}</code>")
    if p.ru_status == "active" and p.ru_number:
        meta.append(f"🇷🇺 РУ {p.ru_number}")
    lines.append(" · ".join(meta))
    if p.base_specs:
        lines += _format_specs(p.base_specs)
    elif p.description:
        lines.append("")
        lines.append(f"<i>{p.description[:450]}</i>")
    if p.pdf_count:
        lines.append("")
        lines.append(f"📄 datasheet: {p.pdf_count}")
    return "\n".join(lines)


def _build_results_text(intent: dict[str, Any], products: list[Product], total: int) -> str:
    lines = []
    expl = intent.get("explanation_ru") or "Обработал запрос"
    lines.append(f"🔍 <i>{expl}</i>")

    if not products:
        lines.append("")
        lines.append("<b>Ничего не нашёл.</b>")
        lines.append("")
        lines.append("Попробуй переформулировать или /brands чтобы посмотреть что есть.")
        return "\n".join(lines)

    cnt = (f"Нашёл {total} записей, показываю {len(products)}" if total > len(products)
           else f"Нашёл {total} {'запись' if total == 1 else ('записи' if 2 <= total <= 4 else 'записей')}")
    lines.append(f"<b>{cnt}.</b>")
    lines.append("")
    # топ-результат — полная карточка с характеристиками
    lines.append(_format_product_card(products[0]))
    # остальные — кратким списком (карточку можно открыть кнопкой «детали»)
    rest = products[1:]
    if rest:
        lines.append("")
        lines.append(f"<b>Ещё {len(rest)} — нажми «детали» для карточки:</b>")
        for i, p in enumerate(rest[:8], 2):
            lines.append(_format_product_line(p, i))

    return "\n".join(lines)


def _build_keyboard(products: list[Product], page: int, has_more: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    # одна кнопка "Отдать все PDF" если есть pdfs суммарно
    total_pdfs = sum(p.pdf_count for p in products)
    if total_pdfs > 0:
        rows.append([InlineKeyboardButton(
            text=f"📄 Отдать все PDF ({total_pdfs})",
            callback_data=f"pdfs:{','.join(str(p.id) for p in products[:10])}",
        )])
    # пер-продукт кнопки "детали"
    for p in products[:5]:
        rows.append([InlineKeyboardButton(
            text=f"🔍 {p.model[:40]}",
            callback_data=f"prod:{p.id}",
        )])
    if has_more:
        rows.append([InlineKeyboardButton(
            text="➡️ Ещё", callback_data=f"page:{page + 1}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(F.text)
async def on_text(
    msg: Message, db: DB, intent_parser: IntentParser,
    storage: Storage, settings: Settings,
) -> None:
    if not msg.text:
        return
    text = msg.text.strip()
    if not text:
        return

    # Иначе пробуем LLM intent
    await msg.chat.do("typing")
    try:
        intent = await intent_parser.parse(text)
    except Exception as e:
        log.exception("intent parse failed")
        await msg.answer(f"❌ LLM intent parse failed: <code>{type(e).__name__}: {e}</code>")
        return

    action = intent.get("action", "unclear")

    if action == "help":
        from .common import HELP
        await msg.answer(HELP)
        return

    if action == "unclear":
        expl = intent.get("explanation_ru", "Не смог разобрать запрос.")
        await msg.answer(
            f"🤔 {expl}\n\n"
            "Попробуй переформулировать. Например:\n"
            "• <i>покажи тройные квадруполы Шимадзу</i>\n"
            "• <i>что у нас есть по Sciex</i>"
        )
        return

    if action == "stats":
        # делегируем cmd_stats но через прямой вызов БД
        totals = await db.totals()
        brand_filter = intent.get("brand")
        if brand_filter:
            cats = await db.category_counts(brand=brand_filter)
            lines = [f"<b>📊 {brand_filter} — статистика</b>", ""]
            for c in cats[:15]:
                lines.append(f"  • <code>{c.category}</code> — {c.total:,}".replace(",", " "))
        else:
            cats = await db.category_counts()
            lines = [
                "<b>📊 Каталог — статистика</b>",
                "",
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
    brand = intent.get("brand")
    category = intent.get("category")
    keywords = intent.get("keywords") or []
    has_pdf = intent.get("has_pdf")
    has_ru = intent.get("has_ru")
    send_pdfs = bool(intent.get("send_pdfs"))

    products = await db.search_products(
        brand=brand, category=category, keywords=keywords,
        has_pdf=has_pdf, has_ru=has_ru, limit=limit,
    )
    total = await db.search_count(
        brand=brand, category=category, keywords=keywords,
        has_pdf=has_pdf, has_ru=has_ru,
    )

    text_out = _build_results_text(intent, products, total)
    kb = _build_keyboard(products, page=0, has_more=total > limit) if products else None
    await msg.answer(text_out[:4000], reply_markup=kb, disable_web_page_preview=True)

    # если LLM явно сказал send_pdfs — отдаём сразу
    if send_pdfs and products:
        await _send_all_pdfs(msg, products, storage, settings)


async def _send_all_pdfs(
    msg: Message, products: list[Product],
    storage: Storage, settings: Settings,
) -> None:
    max_pdfs = settings.max_pdfs_per_response
    sent = 0
    skipped_oversize = 0
    errors = 0
    for p in products:
        if sent >= max_pdfs:
            break
        for path in p.datasheet_paths:
            if sent >= max_pdfs:
                break
            try:
                data, size, fname = storage.get_pdf(path)
                if size > 49 * 1024 * 1024:   # Telegram bot upload limit ~50 MB
                    skipped_oversize += 1
                    continue
                caption = f"<b>{p.brand}</b> — {p.model[:80]}"
                await msg.answer_document(
                    BufferedInputFile(data.getvalue(), filename=fname),
                    caption=caption,
                )
                sent += 1
            except Exception as e:
                log.warning("failed sending %s: %s", path, e)
                errors += 1
    parts = [f"📦 Отправлено: {sent}"]
    if skipped_oversize:
        parts.append(f"пропущено больше 50MB: {skipped_oversize}")
    if errors:
        parts.append(f"ошибки: {errors}")
    if sent < sum(p.pdf_count for p in products):
        parts.append(f"(лимит {max_pdfs} файлов за раз)")
    await msg.answer(" • ".join(parts))


@router.callback_query(F.data.startswith("prod:"))
async def cb_product_details(cb: CallbackQuery, db: DB, storage: Storage, settings: Settings) -> None:
    assert cb.data is not None
    from uuid import UUID
    try:
        product_id = UUID(cb.data.split(":", 1)[1])
    except ValueError:
        await cb.answer("Bad id")
        return
    product = await db.get_product(product_id)
    if not product:
        await cb.answer("Не найдено")
        return
    card = _format_product_card(product)
    extra = []
    if product.subcategory:
        extra.append(f"<b>Подкатегория:</b> {product.subcategory}")
    if product.source_urls:
        extra.append(f"<a href=\"{product.source_urls[0]}\">Источник →</a>")
    if product.imported_from:
        extra.append(f"<i>(импорт: {product.imported_from})</i>")
    text = card + ("\n\n" + "\n".join(extra) if extra else "")
    assert cb.message is not None
    await cb.message.answer(text[:4000], disable_web_page_preview=True)

    # отдаём PDF если есть
    if product.datasheet_paths:
        for path in product.datasheet_paths[:settings.max_pdfs_per_response]:
            try:
                data, size, fname = storage.get_pdf(path)
                if size > 49 * 1024 * 1024:
                    continue
                await cb.message.answer_document(
                    BufferedInputFile(data.getvalue(), filename=fname),
                    caption=f"{product.brand} — {product.model}",
                )
            except Exception as e:
                log.warning("pdf %s: %s", path, e)
    await cb.answer()


@router.callback_query(F.data.startswith("pdfs:"))
async def cb_send_all_pdfs(cb: CallbackQuery, db: DB, storage: Storage, settings: Settings) -> None:
    assert cb.data is not None and cb.message is not None
    from uuid import UUID
    ids_str = cb.data.split(":", 1)[1]
    try:
        ids = [UUID(x) for x in ids_str.split(",") if x]
    except ValueError:
        await cb.answer("Bad ids")
        return
    products: list[Product] = []
    for pid in ids:
        p = await db.get_product(pid)
        if p:
            products.append(p)
    await cb.answer(f"Отправляю PDF для {len(products)} продуктов...")
    # повторно используем хелпер _send_all_pdfs (но он завязан на Message)
    await _send_all_pdfs(cb.message, products, storage, settings)
