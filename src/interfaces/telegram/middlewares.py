from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import BaseHandler, ContextTypes

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
_rate_limits: dict[int, list[float]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 30  # max requests per window


def is_user_allowed(user_id: int, allowed_ids: list[int]) -> bool:
    if not allowed_ids:
        return True
    return user_id in allowed_ids


def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    timestamps = _rate_limits[user_id]
    # Clean old entries
    _rate_limits[user_id] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limits[user_id]) >= RATE_LIMIT_MAX:
        return True
    _rate_limits[user_id].append(now)
    return False


async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user:
        return False

    settings: Settings = context.bot_data["settings"]

    # Whitelist check
    if not is_user_allowed(user.id, settings.telegram_allowed_user_ids):
        logger.warning("Unauthorized access attempt from user %d", user.id)
        if update.message:
            await update.message.reply_text("У вас нет доступа к этому боту.")
        return False

    # Rate limit check
    if is_rate_limited(user.id):
        logger.warning("Rate limited user %d", user.id)
        if update.message:
            await update.message.reply_text("Слишком много запросов. Подождите минуту.")
        return False

    return True
