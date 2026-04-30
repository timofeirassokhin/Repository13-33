from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from src.models.calendar import AgendaQuery, CalendarEvent, Reminder
from src.models.common import ServiceResult
from src.services.base import BaseService

if TYPE_CHECKING:
    from src.config import Settings
    from src.db.connection import Database
    from src.services.google_auth import GoogleAuthService

logger = logging.getLogger(__name__)


class CalendarService(BaseService):
    def __init__(
        self, db: Database, settings: Settings, auth: GoogleAuthService
    ) -> None:
        super().__init__(db, settings)
        self._auth = auth

    async def create_event(
        self, telegram_user_id: int, event: CalendarEvent
    ) -> ServiceResult[CalendarEvent]:
        try:
            service = await self._auth.build_service("calendar", "v3", telegram_user_id)
            body = {
                "summary": event.summary,
                "description": event.description,
                "start": {"dateTime": event.start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": event.end.isoformat(), "timeZone": "UTC"},
            }
            if event.location:
                body["location"] = event.location
            if event.reminders:
                body["reminders"] = {
                    "useDefault": False,
                    "overrides": [
                        {"method": r.method, "minutes": r.minutes_before}
                        for r in event.reminders
                    ],
                }
            if event.attendees:
                body["attendees"] = [{"email": e} for e in event.attendees]

            result = await asyncio.to_thread(
                service.events().insert(calendarId="primary", body=body).execute
            )
            event.id = result["id"]
            logger.info("Event created: %s for user %d", event.id, telegram_user_id)
            return ServiceResult(success=True, data=event)
        except Exception as e:
            logger.exception("Failed to create event")
            return ServiceResult(success=False, error=str(e))

    async def get_agenda(
        self, telegram_user_id: int, query: AgendaQuery
    ) -> ServiceResult[list[CalendarEvent]]:
        try:
            service = await self._auth.build_service("calendar", "v3", telegram_user_id)

            now = query.date or datetime.now(timezone.utc)
            time_min = now.isoformat()
            time_max = (now + timedelta(days=query.days_ahead)).isoformat()

            result = await asyncio.to_thread(
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=query.max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute
            )

            events = []
            for item in result.get("items", []):
                start_str = item["start"].get("dateTime", item["start"].get("date", ""))
                end_str = item["end"].get("dateTime", item["end"].get("date", ""))
                events.append(
                    CalendarEvent(
                        id=item.get("id"),
                        summary=item.get("summary", "(Без названия)"),
                        description=item.get("description", ""),
                        start=datetime.fromisoformat(start_str),
                        end=datetime.fromisoformat(end_str),
                        location=item.get("location", ""),
                    )
                )
            return ServiceResult(success=True, data=events)
        except Exception as e:
            logger.exception("Failed to get agenda")
            return ServiceResult(success=False, error=str(e))

    async def delete_event(
        self, telegram_user_id: int, event_id: str
    ) -> ServiceResult[None]:
        try:
            service = await self._auth.build_service("calendar", "v3", telegram_user_id)
            await asyncio.to_thread(
                service.events()
                .delete(calendarId="primary", eventId=event_id)
                .execute
            )
            logger.info("Event deleted: %s for user %d", event_id, telegram_user_id)
            return ServiceResult(success=True)
        except Exception as e:
            logger.exception("Failed to delete event")
            return ServiceResult(success=False, error=str(e))

    async def update_event(
        self, telegram_user_id: int, event_id: str, updates: dict
    ) -> ServiceResult[CalendarEvent]:
        try:
            service = await self._auth.build_service("calendar", "v3", telegram_user_id)
            result = await asyncio.to_thread(
                service.events()
                .patch(calendarId="primary", eventId=event_id, body=updates)
                .execute
            )
            start_str = result["start"].get("dateTime", result["start"].get("date", ""))
            end_str = result["end"].get("dateTime", result["end"].get("date", ""))
            event = CalendarEvent(
                id=result.get("id"),
                summary=result.get("summary", ""),
                description=result.get("description", ""),
                start=datetime.fromisoformat(start_str),
                end=datetime.fromisoformat(end_str),
                location=result.get("location", ""),
            )
            return ServiceResult(success=True, data=event)
        except Exception as e:
            logger.exception("Failed to update event")
            return ServiceResult(success=False, error=str(e))
