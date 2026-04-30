from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Note(BaseModel):
    id: str | None = None
    title: str
    content: str = ""
    tags: list[str] = []
    folder_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NoteSearchQuery(BaseModel):
    query: str = ""
    tags: list[str] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    max_results: int = 20


class NoteMetadata(BaseModel):
    drive_file_id: str
    title: str
    tags: list[str] = []
    snippet: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    folder_path: str = ""
