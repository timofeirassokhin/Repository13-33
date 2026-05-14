"""PDF → text + tables через pdfplumber.

Fallback: если страница не имеет текстового слоя (скан) — помечаем как
`needs_ocr=True` в metadata. OCR через pytesseract — отдельная фаза
(требует tesseract в контейнере + языковые пакеты ru+en).
"""
from __future__ import annotations

import logging
from pathlib import Path

from .core import ExtractedTable, ExtractionOutput

log = logging.getLogger(__name__)


def extract_from_pdf(path: Path, *, ocr_fallback: bool = False) -> ExtractionOutput:
    """Извлечь текст + таблицы из PDF.

    :param path: путь к PDF
    :param ocr_fallback: попытаться tesseract если страница без текстового слоя
    """
    out = ExtractionOutput(source_file=path, file_type="pdf", extractor_name="pdfplumber")

    try:
        import pdfplumber
    except ImportError:
        out.error = "pdfplumber not installed (pip install pdfplumber)"
        return out

    try:
        pdf = pdfplumber.open(str(path))
    except Exception as exc:
        out.error = f"failed to open PDF: {exc}"
        log.warning("PDF open failed for %s: %s", path, exc)
        return out

    text_parts: list[str] = []
    needs_ocr_pages: list[int] = []

    with pdf:
        out.pages_count = len(pdf.pages)
        out.metadata["title"] = (pdf.metadata or {}).get("Title", "")
        out.metadata["author"] = (pdf.metadata or {}).get("Author", "")

        for page_idx, page in enumerate(pdf.pages, start=1):
            page_text = ""
            try:
                page_text = page.extract_text() or ""
            except Exception as exc:
                out.notes.append(f"page {page_idx} text extraction failed: {exc}")

            if not page_text.strip():
                needs_ocr_pages.append(page_idx)
            else:
                text_parts.append(page_text)

            # Tables — pdfplumber automatic detection
            try:
                page_tables = page.extract_tables() or []
                for tbl in page_tables:
                    if not tbl or len(tbl) < 2:
                        continue
                    # Clean Nones to empty strings
                    rows = [[(c or "").strip() for c in row] for row in tbl]
                    out.tables.append(ExtractedTable(rows=rows, page=page_idx))
            except Exception as exc:
                out.notes.append(f"page {page_idx} tables extraction failed: {exc}")

    out.text = "\n\n".join(text_parts).strip()
    out.paragraphs = [p.strip() for p in out.text.split("\n\n") if p.strip()]
    out.metadata["needs_ocr_pages"] = needs_ocr_pages

    if needs_ocr_pages and ocr_fallback:
        out.notes.append(f"OCR fallback requested for {len(needs_ocr_pages)} pages")
        try:
            _ocr_fallback(path, needs_ocr_pages, out)
        except Exception as exc:
            out.notes.append(f"OCR fallback failed: {exc}")

    if needs_ocr_pages and not ocr_fallback:
        out.notes.append(
            f"{len(needs_ocr_pages)} pages have no text layer (likely scanned). "
            f"Re-run with ocr_fallback=True if needed."
        )

    return out


def _ocr_fallback(path: Path, pages: list[int], out: ExtractionOutput) -> None:
    """OCR через pytesseract + pdf2image. Импорты ленивые."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        out.notes.append("pytesseract/pdf2image not installed for OCR")
        return

    images = convert_from_path(str(path), dpi=200, first_page=min(pages), last_page=max(pages))
    ocr_parts: list[str] = []
    for img, page_idx in zip(images, pages):
        try:
            txt = pytesseract.image_to_string(img, lang="rus+eng")
            if txt.strip():
                ocr_parts.append(f"[page {page_idx} OCR]\n{txt.strip()}")
        except Exception as exc:
            out.notes.append(f"OCR page {page_idx} failed: {exc}")

    if ocr_parts:
        out.text += "\n\n" + "\n\n".join(ocr_parts)
        out.notes.append(f"OCR added {len(ocr_parts)} pages of text")
