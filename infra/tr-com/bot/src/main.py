"""@timofeirassokhin_bot — основной поток: контакты, заявки, форвард админу.

Команды:
- /start    — приветствие + регистрация
- /help     — список команд
- /whoami   — мой Telegram ID и базовая инфа (для отладки)
- /book     — записаться на разговор (тема + удобное время)
- /subscribe — оставить email для писем (когда дозреем до рассылок)
- /cancel   — отмена многошагового сценария (book/subscribe)

Админ-команды (только для TR_BOT_ALLOWED_ADMIN_IDS):
- /admin       — справка по админ-командам
- /users       — последние 20 пользователей
- /bookings    — все необработанные заявки
- /subscribers — кто оставил email

Любое другое сообщение (текст / голос / фото / документ) — форвардится админу
(если он задан) и логируется в локальную SQLite.

Когда в админский чат прилетит forward, можно ответить на него (Reply) — бот
перешлёт ответ исходному пользователю.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.utils.markdown import hbold, hcode

from .config import load
from .db import DB


log = logging.getLogger("tr-bot")

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


class BookFlow(StatesGroup):
    waiting_topic = State()
    waiting_when = State()


class SubscribeFlow(StatesGroup):
    waiting_email = State()


# ----- helpers ---------------------------------------------------------------

def is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


def fmt_user(u: dict) -> str:
    name = " ".join(filter(None, [u.get("first_name"), u.get("last_name")])).strip() or "—"
    handle = f"@{u['username']}" if u.get("username") else "(без username)"
    return f"{name} {handle} <code>id={u['tg_id']}</code>"


# ----- public commands -------------------------------------------------------

async def cmd_start(message: Message, db: DB) -> None:
    u = message.from_user
    if not u:
        return
    await db.upsert_user(u.id, u.username, u.first_name, u.last_name, u.language_code)
    name = u.first_name or "друг"
    text = (
        f"Привет, {name}.\n\n"
        f"Это бот <b>Тимофея Рассохина</b> — коуча, психолога, фотографа и бизнес-консультанта.\n\n"
        f"Что можно:\n"
        f"• /book — записаться на разговор\n"
        f"• /subscribe — оставить email для писем про события и тренинги\n"
        f"• Просто напиши вопрос — Тимофей увидит и ответит лично.\n\n"
        f"Полный список команд — /help."
    )
    await message.answer(text)


async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Команды:</b>\n"
        "/start — начать с начала\n"
        "/book — записаться на консультацию\n"
        "/subscribe — оставить email для рассылки\n"
        "/whoami — показать мой Telegram ID\n"
        "/cancel — отменить текущее действие"
    )


async def cmd_whoami(message: Message) -> None:
    u = message.from_user
    if not u:
        return
    await message.answer(
        f"Твой Telegram ID: {hcode(str(u.id))}\n"
        f"Username: @{u.username or '—'}\n"
        f"Имя: {u.first_name or '—'} {u.last_name or ''}".strip()
    )


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    cur = await state.get_state()
    if cur is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Отменил. Если что — пиши /help.")


# ----- /book -----------------------------------------------------------------

async def book_start(message: Message, state: FSMContext) -> None:
    await state.set_state(BookFlow.waiting_topic)
    await message.answer(
        "Напиши коротко — <b>о чём хотел бы поговорить</b>?\n"
        "(Одним сообщением — пара предложений достаточно.)"
    )


async def book_topic(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Жду текстом, пожалуйста.")
        return
    await state.update_data(topic=message.text.strip()[:1000])
    await state.set_state(BookFlow.waiting_when)
    await message.answer("Хорошо. <b>Когда тебе удобно</b>? Можно примерно (день недели, время суток).")


async def book_when(message: Message, state: FSMContext, db: DB, admin_ids: list[int], bot: Bot) -> None:
    if not message.text:
        await message.answer("Жду текстом.")
        return
    when_pref = message.text.strip()[:500]
    data = await state.get_data()
    topic = data.get("topic", "")
    u = message.from_user
    assert u
    booking_id = await db.add_booking(u.id, topic, when_pref)
    await state.clear()

    await message.answer(
        f"Принял заявку #{booking_id}. Тимофей свяжется с тобой здесь же — обычно в течение дня."
    )

    if admin_ids:
        admin_text = (
            f"📅 <b>Новая заявка #{booking_id}</b>\n\n"
            f"От: {fmt_user({'tg_id': u.id, 'username': u.username, 'first_name': u.first_name, 'last_name': u.last_name})}\n\n"
            f"<b>Тема:</b>\n{topic}\n\n"
            f"<b>Когда удобно:</b>\n{when_pref}"
        )
        for aid in admin_ids:
            try:
                await bot.send_message(aid, admin_text)
            except Exception as e:
                log.warning("can't notify admin %s: %s", aid, e)


# ----- /subscribe -----------------------------------------------------------

async def subscribe_start(message: Message, state: FSMContext) -> None:
    await state.set_state(SubscribeFlow.waiting_email)
    await message.answer(
        "Скинь email одной строкой. Я добавлю тебя в лист — рассылка стартует, когда будет что прислать.\n"
        "Отписаться можно в любой момент."
    )


async def subscribe_email(message: Message, state: FSMContext, db: DB) -> None:
    if not message.text:
        await message.answer("Жду email текстом.")
        return
    email = message.text.strip().lower()
    if not EMAIL_RE.match(email):
        await message.answer("Это не похоже на email. Попробуй ещё раз или /cancel.")
        return
    u = message.from_user
    assert u
    await db.set_email(u.id, email)
    await state.clear()
    await message.answer(
        f"Готово, записал {hcode(email)}. Когда дозреем до первой рассылки — пришлю письмо с подтверждением."
    )


# ----- forward to admin -----------------------------------------------------

async def forward_to_admin(message: Message, db: DB, admin_ids: list[int], bot: Bot) -> None:
    """Любое не-командное сообщение пользователя → форвард админу + лог в БД."""
    u = message.from_user
    if not u:
        return

    # Логируем в БД
    kind = "text" if message.text else (
        "voice" if message.voice else
        "photo" if message.photo else
        "video" if message.video else
        "document" if message.document else
        "audio" if message.audio else
        "sticker" if message.sticker else
        "other"
    )
    await db.log_message(u.id, message.chat.id, message.message_id, kind, message.text or message.caption)

    # Подтверждение пользователю
    await message.answer("Получил. Тимофей увидит и ответит здесь.")

    # Форвард в админский чат (первого ID хватит — обычно один админ)
    if admin_ids:
        target = admin_ids[0]
        try:
            await message.forward(chat_id=target)
        except Exception as e:
            log.warning("forward to admin %s failed: %s", target, e)


async def admin_reply(message: Message, bot: Bot) -> None:
    """Когда админ отвечает Reply на форварднутое сообщение — посылаем юзеру.

    aiogram: forwarded message хранит forward_origin (forward_from в старых API).
    Ищем оригинального автора в forward_from.id и шлём ему текст ответа.
    """
    if not message.reply_to_message or not message.text:
        return
    orig = message.reply_to_message
    target_id: int | None = None
    if orig.forward_from:
        target_id = orig.forward_from.id
    elif orig.forward_origin and getattr(orig.forward_origin, "sender_user", None):
        target_id = orig.forward_origin.sender_user.id  # type: ignore[union-attr]
    if not target_id:
        await message.answer("Не нашёл оригинального автора (возможно, у юзера приватность). Скопируй сообщение и пошли вручную.")
        return
    try:
        await bot.send_message(target_id, message.text)
        await message.answer("Отправил ответ.")
    except Exception as e:
        await message.answer(f"Не получилось отправить: {e}")


# ----- admin commands -------------------------------------------------------

async def cmd_admin(message: Message) -> None:
    await message.answer(
        "<b>Админ:</b>\n"
        "/users — последние 20 пользователей\n"
        "/bookings — необработанные заявки\n"
        "/subscribers — кто оставил email\n\n"
        "Чтобы ответить юзеру: <b>Reply</b> на форварднутое сообщение — бот доставит."
    )


async def cmd_users(message: Message, db: DB) -> None:
    rows = await db.list_recent_users(20)
    if not rows:
        await message.answer("Пользователей пока нет.")
        return
    lines = [f"<b>Последние {len(rows)} пользователей:</b>"]
    for r in rows:
        sub = " 📧" if r["is_subscribed"] else ""
        lines.append(f"• {fmt_user(r)}{sub}")
    await message.answer("\n".join(lines))


async def cmd_bookings(message: Message, db: DB) -> None:
    rows = await db.list_pending_bookings()
    if not rows:
        await message.answer("Открытых заявок нет.")
        return
    lines = [f"<b>Открытых заявок: {len(rows)}</b>\n"]
    for r in rows:
        topic = (r["topic"] or "")[:120]
        lines.append(
            f"#{r['id']} от {fmt_user(r)}\n"
            f"<i>Тема:</i> {topic}\n"
            f"<i>Когда:</i> {r['when_pref'] or '—'}\n"
        )
    await message.answer("\n".join(lines))


async def cmd_subscribers(message: Message, db: DB) -> None:
    rows = await db.list_subscribers()
    if not rows:
        await message.answer("Подписчиков с email пока нет.")
        return
    lines = [f"<b>Подписчиков: {len(rows)}</b>"]
    for r in rows:
        lines.append(f"• {r['email']} ({r.get('first_name') or '—'}, lang={r.get('language_code') or '?'})")
    await message.answer("\n".join(lines))


# ----- bootstrap ------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings, glue = load()
    log.info(
        "starting bot, glue=%s mempalace=%s proxy=%s db=/data/bot.db admins=%s",
        glue.glue_base_url, glue.mempalace_url, settings.proxy or "none", settings.allowed_admin_ids,
    )

    db_path = Path("/data/bot.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = DB(db_path)
    await db.open()

    session = AiohttpSession(proxy=settings.proxy) if settings.proxy else AiohttpSession()
    bot = Bot(
        token=settings.token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    admin_ids = settings.allowed_admin_ids

    # /start, /help, /whoami, /cancel
    dp.message.register(lambda m: cmd_start(m, db), CommandStart())
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_whoami, Command("whoami"))
    dp.message.register(cmd_cancel, Command("cancel"))

    # /book flow
    dp.message.register(book_start, Command("book"))
    dp.message.register(book_topic, BookFlow.waiting_topic)
    dp.message.register(
        lambda m, state: book_when(m, state, db, admin_ids, bot),
        BookFlow.waiting_when,
    )

    # /subscribe flow
    dp.message.register(subscribe_start, Command("subscribe"))
    dp.message.register(
        lambda m, state: subscribe_email(m, state, db),
        SubscribeFlow.waiting_email,
    )

    # admin commands — отдельно (только для админов)
    dp.message.register(cmd_admin, Command("admin"), F.from_user.id.in_(admin_ids))
    dp.message.register(lambda m: cmd_users(m, db), Command("users"), F.from_user.id.in_(admin_ids))
    dp.message.register(lambda m: cmd_bookings(m, db), Command("bookings"), F.from_user.id.in_(admin_ids))
    dp.message.register(lambda m: cmd_subscribers(m, db), Command("subscribers"), F.from_user.id.in_(admin_ids))

    # admin reply на форварды
    dp.message.register(
        lambda m: admin_reply(m, bot),
        F.from_user.id.in_(admin_ids),
        F.reply_to_message,
    )

    # fallback — всё остальное в форвард админу
    dp.message.register(lambda m: forward_to_admin(m, db, admin_ids, bot))

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
