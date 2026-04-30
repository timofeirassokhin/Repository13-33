from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class Reminder(BaseModel):
    method: str = "popup"
    minutes_before: int = 15


class CalendarEvent(BaseModel):
    id: str | None = None
    summary: str
    description: str = ""
    start: datetime
    end: datetime
    location: str = ""
    reminders: list[Reminder] = []
    recurrence: list[str] = []
    attendees: list[str] = []

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: datetime, info: object) -> datetime:
        data = getattr(info, "data", {})
        if "start" in data and v <= data["start"]:
            raise ValueError("end must be after start")
        return v


class AgendaQuery(BaseModel):
    date: datetime | None = None
    days_ahead: int = 1
    max_results: int = 10


class TimeSlot(BaseModel):
    start: datetime
    end: datetime
