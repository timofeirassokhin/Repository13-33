from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from src.agent.intent import Intent, ParsedCommand
from src.models.common import UserContext

logger = logging.getLogger(__name__)

# Conversation states for /add_rule
RULE_NAME, RULE_PATTERNS, RULE_DESTINATION, RULE_CONFIRM = range(4)


async def _build_user_context(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> UserContext:
    user = update.effective_user
    chat = update.effective_chat
    user_repo = context.bot_data["user_repo"]
    is_auth = await user_repo.is_authenticated(user.id) if user else False
    return UserContext(
        telegram_user_id=user.id if user else 0,
        telegram_chat_id=chat.id if chat else 0,
        google_authenticated=is_auth,
    )


# --- /sort ---

async def sort_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    args = context.args or []
    folder_id = args[0] if args else ""

    if not folder_id:
        settings = context.bot_data["settings"]
        folder_id = settings.default_sort_root

    if not folder_id:
        await update.message.reply_text(
            "Укажите ID папки: /sort <folder_id>\n"
            "Или установите папку по умолчанию в настройках."
        )
        return

    await update.message.reply_text("Сортирую файлы...")

    command = ParsedCommand(
        intent=Intent.SORT_FOLDER,
        params={"folder_id": folder_id},
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")


# --- /rules ---

async def rules_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    command = ParsedCommand(intent=Intent.LIST_SORT_RULES)
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")


# --- /add_rule conversation ---

async def add_rule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message:
        return ConversationHandler.END
    await update.message.reply_text(
        "Создаём правило сортировки. Введите название правила:"
    )
    return RULE_NAME


async def rule_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    context.user_data["rule_name"] = update.message.text  # type: ignore[index]
    await update.message.reply_text(
        "Введите расширения файлов через пробел:\n"
        "Например: .jpg .png .gif"
    )
    return RULE_PATTERNS


async def rule_patterns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    patterns = update.message.text.strip().split()
    context.user_data["rule_patterns"] = patterns  # type: ignore[index]
    await update.message.reply_text(
        "Введите ID целевой папки в Google Drive:"
    )
    return RULE_DESTINATION


async def rule_destination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END
    context.user_data["rule_destination"] = update.message.text.strip()  # type: ignore[index]

    patterns_str = ", ".join(context.user_data["rule_patterns"])  # type: ignore[index]
    await update.message.reply_text(
        f"<b>Подтвердите правило:</b>\n\n"
        f"Название: {context.user_data['rule_name']}\n"  # type: ignore[index]
        f"Расширения: {patterns_str}\n"
        f"Папка: {context.user_data['rule_destination']}\n\n"  # type: ignore[index]
        f"Создать? (да/нет)",
        parse_mode="HTML",
    )
    return RULE_CONFIRM


async def rule_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return ConversationHandler.END

    if update.message.text.strip().lower() not in ("да", "yes", "д", "y"):
        await update.message.reply_text("Создание правила отменено.")
        return ConversationHandler.END

    user_ctx = await _build_user_context(update, context)
    dispatcher = context.bot_data["dispatcher"]

    command = ParsedCommand(
        intent=Intent.ADD_SORT_RULE,
        params={
            "name": context.user_data["rule_name"],  # type: ignore[index]
            "extension_patterns": context.user_data["rule_patterns"],  # type: ignore[index]
            "destination_folder_id": context.user_data["rule_destination"],  # type: ignore[index]
        },
    )
    result = await dispatcher.dispatch(command, user_ctx)
    await update.message.reply_text(result, parse_mode="HTML")
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Отменено.")
    return ConversationHandler.END


def register(app: Application) -> None:  # type: ignore[type-arg]
    app.add_handler(CommandHandler("sort", sort_handler))
    app.add_handler(CommandHandler("rules", rules_handler))

    conv = ConversationHandler(
        entry_points=[CommandHandler("add_rule", add_rule_start)],
        states={
            RULE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, rule_name)],
            RULE_PATTERNS: [MessageHandler(filters.TEXT & ~filters.COMMAND, rule_patterns)],
            RULE_DESTINATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, rule_destination)],
            RULE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, rule_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    app.add_handler(conv)
