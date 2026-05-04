"""@timofeirassokhin_bot — minimal scaffold (polling).

Команды первой версии:
- /start  — приветствие и регистрация Contact в Twenty (через glue)
- /book   — записаться на консультацию (placeholder, потом — Calendar slots)
- /subscribe — подписка на рассылку (placeholder)

Расширяем по мере появления требований.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from .config import load


log = logging.getLogger("tr-bot")


async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name if message.from_user else "друг"
    text = (
        f"Привет, {name}.\n\n"
        "Это бот <b>Тимофея Рассохина</b> — коуча, психолога, фотографа и бизнес-консультанта.\n\n"
        "Что можно:\n"
        "• /book — записаться на консультацию\n"
        "• /subscribe — подписаться на письма про события и тренинги\n"
        "• Просто напиши вопрос — отвечу лично."
    )
    await message.answer(text)


async def cmd_book(message: Message) -> None:
    await message.answer(
        "Запись на консультацию пока в ручном режиме.\n\n"
        "Напиши коротко: что хочешь обсудить и в какие дни/часы тебе удобно — пришлю слот."
    )


async def cmd_subscribe(message: Message) -> None:
    await message.answer(
        "Подписка скоро будет здесь. Пока — добавляй email на сайте: "
        "https://timofeirassokhin.com/subscribe"
    )


async def fallback(message: Message) -> None:
    # Любое сообщение, которое не команда — пересылаем админу как лид.
    await message.answer(
        "Получил твоё сообщение. Тимофей ответит в течение дня."
    )
    # TODO: переслать админу через bot.forward_message + сохранить Contact в Twenty через glue.


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings, glue = load()
    log.info("starting bot, glue=%s mempalace=%s", glue.glue_base_url, glue.mempalace_url)

    bot = Bot(
        token=settings.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_book, Command("book"))
    dp.message.register(cmd_subscribe, Command("subscribe"))
    dp.message.register(fallback, F.text)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
