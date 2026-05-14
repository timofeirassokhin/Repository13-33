"""Общий dispatcher: file → ExtractionOutput.

Выбирает backend по расширению. Если нужного нет — error, без silent fallback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Одна таблица из документа."""

    rows: list[list[str]] = field(default_factory=list)
    page: int | None = None        # для PDF — номер страницы
    title: str = ""                # caption если найден
    bbox: tuple[float, float, float, float] | None = None  # PDF coordinates

    @property
    def shape(self) -> tuple[int, int]:
        return (len(self.rows), len(self.rows[0]) if self.rows else 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "page": self.page,
            "title": self.title,
            "shape": list(self.shape),
        }


@dataclass
class ExtractionOutput:
    """Унифицированный результат извлечения."""

    source_file: Path
    file_type: str                     # "pdf" | "docx" | "doc" | "html" | "xlsx" | ...
    pages_count: int = 0               # для PDF — кол-во страниц
    text: str = ""                     # cleaned plain text (все страницы / параграфы)
    paragraphs: list[str] = field(default_factory=list)
    tables: list[ExtractedTable] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extractor_name: str = ""           # 'pdfplumber' | 'python-docx' | 'selectolax' | ...
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": str(self.source_file),
            "file_type": self.file_type,
            "pages_count": self.pages_count,
            "text": self.text,
            "paragraphs_count": len(self.paragraphs),
            "tables_count": len(self.tables),
            "tables": [t.to_dict() for t in self.tables],
            "metadata": self.metadata,
            "extractor_name": self.extractor_name,
            "notes": self.notes,
            "error": self.error,
        }


def extract_document(path: Path) -> ExtractionOutput:
    """Главный entrypoint — конвертировать файл в structured form.

    :raises ValueError: если расширение неизвестно
    """
    if not path.exists():
        return ExtractionOutput(
            source_file=path, file_type="unknown",
            error=f"file not found: {path}",
        )

    ext = path.suffix.lower()

    if ext == ".pdf":
        from .pdf_extractor import extract_from_pdf
        return extract_from_pdf(path)
    if ext == ".docx":
        from .docx_extractor import extract_from_docx_file
        return extract_from_docx_file(path)
    if ext in (".doc", ".rtf"):
        from .doc_extractor import extract_from_doc
        return extract_from_doc(path)
    if ext in (".html", ".htm"):
        from .html_extractor import extract_from_html
        return extract_from_html(path)
    if ext in (".xlsx", ".xlsm"):
        from .xlsx_extractor import extract_from_xlsx
        return extract_from_xlsx(path)

    return ExtractionOutput(
        source_file=path, file_type=ext.lstrip("."),
        error=f"unsupported file type: {ext}",
    )
