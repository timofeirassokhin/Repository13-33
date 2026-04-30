from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.interfaces.telegram.keyboards import auth_keyboard, confirm_keyboard
from src.services.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)


def _get_auth_service(context: ContextTypes.DEFAULT_TYPE) -> GoogleAuthService:
    dispatcher = context.bot_data["dispatcher"]
    return dispatcher._auth


async def login_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    user_repo = context.bot_data["user_repo"]
    if await user_repo.is_authenticated(user.id):
        await update.message.reply_text(
            "Вы уже авторизованы в Google.\n"
            "Используйте /logout для отключения."
        )
        return

    auth_service = _get_auth_service(context)
    auth_url = auth_service.get_auth_url(user.id)

    await update.message.reply_text(
        "Для работы с Google Calendar и Drive нужна авторизация.\n"
        "Нажмите кнопку ниже:",
        reply_markup=auth_keyboard(auth_url),
    )


async def logout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    user_repo = context.bot_data["user_repo"]
    if not await user_repo.is_authenticated(user.id):
        await update.message.reply_text("Вы не авторизованы.")
        return

    await update.message.reply_text(
        "Вы уверены, что хотите отключить Google аккаунт?",
        reply_markup=confirm_keyboard("logout"),
    )


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    if query.data == "logout:yes":
        user = update.effective_user
        if user:
            auth_service = _get_auth_service(context)
            await auth_service.revoke(user.id)
            await query.edit_message_text("Google аккаунт отключён.")
    elif query.data == "logout:no":
        await query.edit_message_text("Отменено.")


def register(app: Application) -> None:  # type: ignore[type-arg]
    from telegram.ext import CallbackQueryHandler

    app.add_handler(CommandHandler("login", login_handler))
    app.add_handler(CommandHandler("logout", logout_handler))
    app.add_handler(CallbackQueryHandler(logout_callback, pattern=r"^logout:"))
