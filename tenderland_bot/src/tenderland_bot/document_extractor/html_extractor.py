"""HTML → text + tables через selectolax.

Особое назначение в нашем pipeline — **извещения ФЗ-44** (`Печатная форма
извещения <number>.html` в каждом tender package). Они содержат полную
форму закупки с **таблицей характеристик товара** в structured HTML.

При обычном HTML — генерируется текст + список таблиц.
При формате ФЗ-44 — секция "Описание объекта закупки" извлекается отдельно
(сейчас по ключевым словам, в будущем — через XSD-аккуратный парсер).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .core import ExtractedTable, ExtractionOutput

log = logging.getLogger(__name__)


def extract_from_html(path: Path) -> ExtractionOutput:
    """Извлечь текст + таблицы из HTML."""
    out = ExtractionOutput(source_file=path, file_type="html", extractor_name="selectolax")

    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        out.error = "selectolax not installed (pip install selectolax)"
        return out

    try:
        raw = path.read_bytes()
        # Угадываем кодировку: utf-8 → cp1251 fallback (zakupki часто cp1251)
        for enc in ("utf-8", "cp1251", "windows-1251", "koi8-r"):
            try:
                html_text = raw.decode(enc)
                out.metadata["encoding"] = enc
                break
            except UnicodeDecodeError:
                continue
        else:
            html_text = raw.decode("utf-8", errors="replace")
            out.metadata["encoding"] = "utf-8-fallback"
    except Exception as exc:
        out.error = f"failed to read HTML: {exc}"
        return out

    tree = HTMLParser(html_text)

    # Title
    title_el = tree.css_first("title")
    if title_el:
        out.metadata["title"] = title_el.text(strip=True)

    # === Tables ===
    for tbl in tree.css("table"):
        rows: list[list[str]] = []
        for tr in tbl.css("tr"):
            cells = [_clean(td.text() or "") for td in tr.css("td, th")]
            if any(c for c in cells):
                rows.append(cells)
        if rows and len(rows) >= 2:
            out.tables.append(ExtractedTable(rows=rows))

    # === Plain text ===
    # Удаляем теги <script> <style> <noscript> для чистоты
    for selector in ("script", "style", "noscript"):
        for node in tree.css(selector):
            node.decompose()

    text = tree.body.text(separator="\n", strip=True) if tree.body else tree.text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    out.text = text.strip()
    out.paragraphs = [p.strip() for p in re.split(r"\n\s*\n", out.text) if p.strip()]

    # === ФЗ-44 specific: "Описание объекта закупки" section ===
    desc_block = _extract_fz44_object_description(text)
    if desc_block:
        out.metadata["fz44_object_description"] = desc_block
        out.notes.append(f"ФЗ-44 'Описание объекта закупки' extracted: {len(desc_block)}ch")

    return out


def _clean(s: str) -> str:
    s = s.replace("\xa0", " ").strip()
    s = re.sub(r"\s+", " ", s)
    return s


_FZ44_HEADERS = (
    "Описание объекта закупки",
    "Объект закупки",
    "Характеристики объекта закупки",
)


def _extract_fz44_object_description(text: str) -> str:
    """Выделить блок "Описание объекта закупки" если он есть в тексте."""
    for header in _FZ44_HEADERS:
        idx = text.find(header)
        if idx >= 0:
            # Берём максимум 5000 символов после заголовка (или до следующего раздела)
            chunk = text[idx:idx + 5000]
            # Обрезаем по следующему "разделу" (заголовок ВСЕ ПРОПИСНЫЕ или "Раздел N")
            end_match = re.search(r"\n\s*(?:Раздел\s+[IVX0-9]+|[А-ЯЁ]{6,}[\.\:]|Подпись)", chunk[len(header):])
            if end_match:
                chunk = chunk[: len(header) + end_match.start()]
            return chunk.strip()
    return ""
