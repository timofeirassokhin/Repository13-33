"""Tender analyzer — распаковка архива, классификация файлов, извлечение ТЗ.

Этот модуль работает только с локальными zip-архивами, скачанными fetcher'ом.
Не дёргает Tenderland API. См. ../../HANDOFF_TO_ANALYZER.md (контракт от fetcher'а).
"""
from __future__ import annotations

from .classifier import FileCategory, classify_files
from .manifest import AnalyzerManifest, ClassifiedFile
from .unpacker import UnpackResult, unpack_tender_archive

__all__ = [
    "AnalyzerManifest",
    "ClassifiedFile",
    "FileCategory",
    "UnpackResult",
    "classify_files",
    "unpack_tender_archive",
]
