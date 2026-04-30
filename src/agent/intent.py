from __future__ import annotations

from enum import Enum, auto
from typing import Any

from pydantic import BaseModel


class Intent(Enum):
    # Calendar
    CREATE_EVENT = auto()
    VIEW_AGENDA = auto()
    EDIT_EVENT = auto()
    DELETE_EVENT = auto()
    SET_REMINDER = auto()
    # Notes
    CREATE_NOTE = auto()
    SEARCH_NOTES = auto()
    VIEW_NOTE = auto()
    EDIT_NOTE = auto()
    DELETE_NOTE = auto()
    LIST_NOTES = auto()
    # Files
    SORT_FOLDER = auto()
    ADD_SORT_RULE = auto()
    LIST_SORT_RULES = auto()
    DELETE_SORT_RULE = auto()
    # System
    LOGIN = auto()
    LOGOUT = auto()
    HELP = auto()
    START = auto()


class ParsedCommand(BaseModel):
    intent: Intent
    raw_text: str = ""
    params: dict[str, Any] = {}
