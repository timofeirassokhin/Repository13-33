from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def auth_keyboard(auth_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Авторизоваться в Google", url=auth_url)]
    ])


def confirm_keyboard(callback_prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Да", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton("Нет", callback_data=f"{callback_prefix}:no"),
        ]
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Отмена", callback_data="cancel")]
    ])
