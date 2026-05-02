"""Парсеры файлов в plain text / markdown.

Каждая функция принимает Path и возвращает str (markdown). Падает при ошибке.
"""
from __future__ import annotations

from pathlib import Path


def parse_pdf(path: Path) -> str:
    import fitz  # pymupdf
    doc = fitz.open(path)
    parts = []
    for page in doc:
        text = page.get_text("text").strip()
        if text:
            parts.append(text)
    doc.close()
    return "\n\n".join(parts)


def parse_docx(path: Path) -> str:
    from docx import Document  # python-docx
    doc = Document(path)
    parts = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        # Заголовки → markdown
        style = (para.style.name or "").lower() if para.style else ""
        if "heading 1" in style:
            parts.append(f"# {text}")
        elif "heading 2" in style:
            parts.append(f"## {text}")
        elif "heading 3" in style:
            parts.append(f"### {text}")
        else:
            parts.append(text)
    return "\n\n".join(parts)


def parse_epub(path: Path) -> str:
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup
    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        try:
            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "html.parser")
            # Сохраняем структуру через простой markdown
            for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "blockquote"]):
                txt = tag.get_text(" ", strip=True)
                if not txt:
                    continue
                if tag.name == "h1":
                    parts.append(f"# {txt}")
                elif tag.name == "h2":
                    parts.append(f"## {txt}")
                elif tag.name in ("h3", "h4"):
                    parts.append(f"### {txt}")
                elif tag.name == "blockquote":
                    parts.append(f"> {txt}")
                else:
                    parts.append(txt)
        except Exception:
            continue
    return "\n\n".join(parts)


def parse_rtf(path: Path) -> str:
    from striprtf.striprtf import rtf_to_text
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return rtf_to_text(raw, errors="ignore")


def parse_txt(path: Path) -> str:
    import chardet
    raw_bytes = path.read_bytes()
    detected = chardet.detect(raw_bytes)
    encoding = detected.get("encoding") or "utf-8"
    return raw_bytes.decode(encoding, errors="replace")


def parse_md(path: Path) -> str:
    return parse_txt(path)


PARSERS = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".epub": parse_epub,
    ".rtf": parse_rtf,
    ".txt": parse_txt,
    ".md": parse_md,
    ".markdown": parse_md,
}


def parse_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext not in PARSERS:
        raise ValueError(f"Unsupported file extension: {ext}")
    return PARSERS[ext](path).strip()
