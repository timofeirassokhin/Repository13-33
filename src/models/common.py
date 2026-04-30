from __future__ import annotations

from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ServiceResult(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserContext(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int
    google_authenticated: bool = False
