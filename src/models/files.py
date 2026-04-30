from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class SortStrategy(str, Enum):
    BY_TYPE = "by_type"
    BY_DATE = "by_date"
    BY_TAG = "by_tag"


class FileEntry(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int = 0
    created_at: datetime | None = None
    parent_folder_id: str | None = None


class SortRule(BaseModel):
    id: int | None = None
    name: str
    mime_patterns: list[str] = []
    extension_patterns: list[str] = []
    destination_folder_id: str
    destination_folder_name: str = ""


class SortResult(BaseModel):
    moved: list[tuple[str, str]] = []
    skipped: list[str] = []
    errors: list[str] = []
