from __future__ import annotations

from typing import Any

from src.agent.intent import Intent
from src.models.calendar import CalendarEvent
from src.models.files import SortResult, SortRule
from src.models.notes import NoteMetadata


def format_auth_required(auth_url: str) -> str:
    return (
        "Для работы нужна авторизация Google.\n\n"
        f'<a href="{auth_url}">Нажмите для авторизации</a>\n\n'
        "После авторизации вернитесь в этот чат."
    )


def format_auth_expired() -> str:
    return (
        "Сессия Google истекла. Используйте /login для повторной авторизации."
    )


def format_event(event: CalendarEvent) -> str:
    start = event.start.strftime("%d.%m.%Y %H:%M")
    end = event.end.strftime("%H:%M")
    lines = [f"<b>{event.summary}</b>", f"  {start} — {end}"]
    if event.location:
        lines.append(f"  {event.location}")
    if event.description:
        lines.append(f"  <i>{event.description[:100]}</i>")
    return "\n".join(lines)


def format_agenda(events: list[CalendarEvent]) -> str:
    if not events:
        return "На этот период событий нет."
    lines = ["<b>Ваши события:</b>\n"]
    for i, event in enumerate(events, 1):
        lines.append(f"{i}. {format_event(event)}")
    return "\n\n".join(lines)


def format_note_metadata(note: NoteMetadata) -> str:
    tags = " ".join(f"#{t}" for t in note.tags) if note.tags else ""
    date = note.updated_at.strftime("%d.%m.%Y") if note.updated_at else ""
    return f"<b>{note.title}</b>  {tags}\n  <i>{date}</i>"


def format_notes_list(notes: list[NoteMetadata]) -> str:
    if not notes:
        return "Заметок не найдено."
    lines = ["<b>Ваши заметки:</b>\n"]
    for i, note in enumerate(notes, 1):
        lines.append(f"{i}. {format_note_metadata(note)}")
    return "\n\n".join(lines)


def format_sort_result(result: SortResult) -> str:
    lines = [f"<b>Сортировка завершена</b>\n"]
    if result.moved:
        lines.append(f"Перемещено: {len(result.moved)}")
        for name, dest in result.moved[:10]:
            lines.append(f"  {name} → {dest}")
        if len(result.moved) > 10:
            lines.append(f"  ...и ещё {len(result.moved) - 10}")
    if result.skipped:
        lines.append(f"\nПропущено: {len(result.skipped)}")
    if result.errors:
        lines.append(f"\nОшибки: {len(result.errors)}")
        for err in result.errors[:5]:
            lines.append(f"  {err}")
    return "\n".join(lines)


def format_rules_list(rules: list[SortRule]) -> str:
    if not rules:
        return "Правил сортировки нет. Используйте /add_rule для добавления."
    lines = ["<b>Правила сортировки:</b>\n"]
    for i, rule in enumerate(rules, 1):
        patterns = ", ".join(rule.extension_patterns) or ", ".join(rule.mime_patterns) or "—"
        lines.append(
            f"{i}. <b>{rule.name}</b>\n"
            f"   Паттерны: {patterns}\n"
            f"   Папка: {rule.destination_folder_name or rule.destination_folder_id}"
        )
    return "\n\n".join(lines)


def format_result(intent: Intent, result: Any) -> str:
    if not result.success:
        return f"Ошибка: {result.error}"

    match intent:
        case Intent.CREATE_EVENT:
            return f"Событие создано: {format_event(result.data)}"
        case Intent.VIEW_AGENDA:
            return format_agenda(result.data)
        case Intent.DELETE_EVENT:
            return "Событие удалено."
        case Intent.CREATE_NOTE:
            return f"Заметка создана: <b>{result.data.title}</b>"
        case Intent.SEARCH_NOTES | Intent.LIST_NOTES:
            return format_notes_list(result.data)
        case Intent.DELETE_NOTE:
            return "Заметка удалена."
        case Intent.SORT_FOLDER:
            return format_sort_result(result.data)
        case Intent.ADD_SORT_RULE:
            return f"Правило добавлено: <b>{result.data.name}</b>"
        case Intent.LIST_SORT_RULES:
            return format_rules_list(result.data)
        case _:
            return "Готово."
