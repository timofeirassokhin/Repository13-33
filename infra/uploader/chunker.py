"""Чанкинг текста на куски ~target_size знаков с overlap.

Сохраняет границы абзацев (никогда не режет посредине абзаца, если возможно).
"""
from __future__ import annotations


def chunk_text(text: str, target_size: int = 2000, overlap: int = 200) -> list[str]:
    """Делит текст на куски ~target_size знаков, с перекрытием в overlap знаков.

    Алгоритм:
    1. Делим текст на абзацы (по \\n\\n).
    2. Накапливаем абзацы пока не достигнем target_size.
    3. При следующем chunk берём конец предыдущего (overlap) + новый абзац.

    Если один абзац длиннее target_size — режем его по предложениям.
    """
    if not text or len(text) <= target_size:
        return [text.strip()] if text.strip() else []

    # Разбиваем по двойным переносам (абзацы)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # Сверхдлинный абзац — режем по предложениям
        if len(para) > target_size:
            sentences = _split_sentences(para)
            for sent in sentences:
                if len(current) + len(sent) + 2 > target_size and current:
                    chunks.append(current.strip())
                    current = current[-overlap:] if len(current) > overlap else ""
                    current = (current + " " + sent).strip()
                else:
                    current = (current + " " + sent).strip() if current else sent
            continue

        if len(current) + len(para) + 2 > target_size and current:
            chunks.append(current.strip())
            tail = current[-overlap:] if len(current) > overlap else ""
            current = (tail + "\n\n" + para).strip()
        else:
            current = (current + "\n\n" + para).strip() if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_sentences(text: str) -> list[str]:
    """Грубое разделение на предложения по точкам/восклицательным/вопросительным."""
    import re
    # Разделитель: . ! ? с пробелом или \n после
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p.strip() for p in parts if p.strip()]
