from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from src.agent.intent import Intent, ParsedCommand
from src.agent.responses import format_auth_required, format_auth_expired, format_result
from src.models.calendar import AgendaQuery, CalendarEvent
from src.models.common import ServiceResult, UserContext
from src.models.files import SortRule, SortStrategy
from src.models.notes import Note, NoteSearchQuery
from src.services.google_auth import AuthenticationError

if TYPE_CHECKING:
    from src.services.calendar_service import CalendarService
    from src.services.file_sorter_service import FileSorterService
    from src.services.google_auth import GoogleAuthService
    from src.services.notes_service import NotesService

logger = logging.getLogger(__name__)

# System intents that don't require Google auth
_SYSTEM_INTENTS = {Intent.LOGIN, Intent.LOGOUT, Intent.HELP, Intent.START}


class AgentDispatcher:
    def __init__(
        self,
        auth_service: GoogleAuthService,
        calendar_service: CalendarService,
        notes_service: NotesService,
        file_sorter_service: FileSorterService,
    ) -> None:
        self._auth = auth_service
        self._calendar = calendar_service
        self._notes = notes_service
        self._files = file_sorter_service

    async def dispatch(self, command: ParsedCommand, user_ctx: UserContext) -> str:
        # Auth gate
        if command.intent not in _SYSTEM_INTENTS and not user_ctx.google_authenticated:
            auth_url = self._auth.get_auth_url(user_ctx.telegram_user_id)
            return format_auth_required(auth_url)

        try:
            handler = self._get_handler(command.intent)
            if handler is None:
                return "Неизвестная команда. Используйте /help."
            result = await handler(command, user_ctx)
            return format_result(command.intent, result)
        except AuthenticationError:
            return format_auth_expired()
        except Exception as e:
            logger.exception("Dispatch error for %s", command.intent)
            return f"Произошла ошибка: {e}"

    def _get_handler(
        self, intent: Intent
    ) -> Callable[[ParsedCommand, UserContext], Coroutine[Any, Any, ServiceResult]] | None:  # type: ignore[type-arg]
        handlers: dict[Intent, Any] = {
            Intent.CREATE_EVENT: self._handle_create_event,
            Intent.VIEW_AGENDA: self._handle_view_agenda,
            Intent.DELETE_EVENT: self._handle_delete_event,
            Intent.CREATE_NOTE: self._handle_create_note,
            Intent.SEARCH_NOTES: self._handle_search_notes,
            Intent.LIST_NOTES: self._handle_list_notes,
            Intent.DELETE_NOTE: self._handle_delete_note,
            Intent.SORT_FOLDER: self._handle_sort_folder,
            Intent.ADD_SORT_RULE: self._handle_add_rule,
            Intent.LIST_SORT_RULES: self._handle_list_rules,
        }
        return handlers.get(intent)

    # Calendar handlers
    async def _handle_create_event(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        event = CalendarEvent(**cmd.params)
        return await self._calendar.create_event(ctx.telegram_user_id, event)

    async def _handle_view_agenda(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        query = AgendaQuery(**cmd.params)
        return await self._calendar.get_agenda(ctx.telegram_user_id, query)

    async def _handle_delete_event(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        return await self._calendar.delete_event(
            ctx.telegram_user_id, cmd.params["event_id"]
        )

    # Notes handlers
    async def _handle_create_note(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        note = Note(**cmd.params)
        return await self._notes.create_note(ctx.telegram_user_id, note)

    async def _handle_search_notes(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        query = NoteSearchQuery(**cmd.params)
        return await self._notes.search_notes(ctx.telegram_user_id, query)

    async def _handle_list_notes(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        return await self._notes.list_notes(ctx.telegram_user_id)

    async def _handle_delete_note(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        return await self._notes.delete_note(
            ctx.telegram_user_id, cmd.params["note_id"]
        )

    # Files handlers
    async def _handle_sort_folder(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        folder_id = cmd.params.get("folder_id", self._files._settings.default_sort_root)
        strategy = SortStrategy(cmd.params.get("strategy", "by_type"))
        return await self._files.sort_folder(ctx.telegram_user_id, folder_id, strategy)

    async def _handle_add_rule(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        rule = SortRule(**cmd.params)
        return await self._files.add_rule(ctx.telegram_user_id, rule)

    async def _handle_list_rules(
        self, cmd: ParsedCommand, ctx: UserContext
    ) -> ServiceResult:  # type: ignore[type-arg]
        return await self._files.list_rules(ctx.telegram_user_id)
