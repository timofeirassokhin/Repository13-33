"""Document extractor — самостоятельный агент конвертации документов.

Принимает PDF / DOC / DOCX / HTML / XLSX / RTF файлы → возвращает
структурированный текст + таблицы + метаданные.

Используется:
  - analyzer.runner (Layer 3) — для извлечения characteristics из ТЗ
  - future spec_extractor (Layer 2) — для парсинга brochures в product.base_specs
  - бот-archiver — для индексации в Qdrant/FTS

CLI:
  python -m tenderland_bot.document_extractor extract <file>
  python -m tenderland_bot.document_extractor batch <dir>

Архитектура:
  - 4 формат-специфичных backends (pdf/doc/docx/html/xlsx)
  - общий ExtractionOutput dataclass (text + tables + metadata)
  - LibreOffice headless для legacy .doc / .rtf (требует libreoffice в PATH/контейнере)
  - OCR fallback для PDF без текстового слоя (требует tesseract)
"""
from __future__ import annotations

from .core import ExtractionOutput, ExtractedTable, extract_document
from .pdf_extractor import extract_from_pdf
from .html_extractor import extract_from_html
from .doc_extractor import convert_doc_to_docx, extract_from_doc

__all__ = [
    "ExtractionOutput",
    "ExtractedTable",
    "extract_document",
    "extract_from_pdf",
    "extract_from_html",
    "extract_from_doc",
    "convert_doc_to_docx",
]
