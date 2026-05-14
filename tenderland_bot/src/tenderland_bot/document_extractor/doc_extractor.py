"""Legacy .doc / .rtf → текст через LibreOffice headless конвертацию в .docx.

Требует `libreoffice` или `soffice` в PATH. На сервере это часть Docker-образа
catalog-crawler / analyzer (нужно добавить в Dockerfile):

  apt-get install -y libreoffice-core libreoffice-writer

После конвертации — обычный python-docx.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .core import ExtractionOutput

log = logging.getLogger(__name__)


def _find_soffice() -> str | None:
    """Локализовать executable libreoffice/soffice."""
    for candidate in ("soffice", "libreoffice"):
        path = shutil.which(candidate)
        if path:
            return path
    # Стандартные локации Windows
    win_candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in win_candidates:
        if os.path.exists(p):
            return p
    return None


def convert_doc_to_docx(doc_path: Path, output_dir: Path | None = None) -> Path | None:
    """Конвертировать .doc/.rtf → .docx через LibreOffice headless.

    :return: путь к новому .docx или None при ошибке
    """
    soffice = _find_soffice()
    if not soffice:
        log.warning("libreoffice/soffice not found in PATH")
        return None

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="doc_to_docx_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                soffice, "--headless", "--norestore",
                "--convert-to", "docx",
                "--outdir", str(output_dir),
                str(doc_path),
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log.warning("libreoffice conversion failed: %s", result.stderr[:300])
            return None
    except subprocess.TimeoutExpired:
        log.warning("libreoffice timeout converting %s", doc_path)
        return None
    except Exception as exc:
        log.warning("libreoffice error: %s", exc)
        return None

    # LibreOffice сохраняет с тем же stem
    new_path = output_dir / (doc_path.stem + ".docx")
    if new_path.exists():
        return new_path
    return None


def extract_from_doc(path: Path) -> ExtractionOutput:
    """Извлечь текст из .doc / .rtf через LibreOffice → python-docx."""
    out = ExtractionOutput(
        source_file=path,
        file_type=path.suffix.lstrip(".").lower(),
        extractor_name="libreoffice→python-docx",
    )

    converted = convert_doc_to_docx(path)
    if converted is None:
        out.error = (
            "failed to convert .doc to .docx via libreoffice (is libreoffice installed?)"
        )
        return out

    # Используем тот же docx_extractor
    try:
        from .docx_extractor import extract_from_docx_file
        docx_out = extract_from_docx_file(converted)
        # Перенесём результат, сохранив source_file как оригинал
        out.text = docx_out.text
        out.paragraphs = docx_out.paragraphs
        out.tables = docx_out.tables
        out.metadata = docx_out.metadata
        out.metadata["converted_via"] = "libreoffice_headless"
        out.metadata["converted_path"] = str(converted)
        out.notes.extend(docx_out.notes)
        if docx_out.error:
            out.error = docx_out.error
    finally:
        # Прибрать tmpdir
        try:
            tmp_dir = converted.parent
            if tmp_dir.exists() and tmp_dir.name.startswith("doc_to_docx_"):
                shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

    return out
