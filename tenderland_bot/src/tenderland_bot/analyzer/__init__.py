"""Tender analyzer — распаковка архива, классификация файлов, извлечение ТЗ.

Этот модуль работает только с локальными zip-архивами, скачанными fetcher'ом.
Не дёргает Tenderland API. См. ../../HANDOFF_TO_ANALYZER.md (контракт от fetcher'а).
"""
from __future__ import annotations

from .classifier import FileCategory, classify_files
from .decision import Decision, DecisionResult, decide
from .extractor import ExtractedSpec, ExtractionResult, extract_from_docx
from .manifest import AnalyzerManifest, ClassifiedFile
from .matcher import MatchCandidate, SpecMatch, match_tender_to_catalog, match_one_candidate
from .runner import AnalysisResult, analyze_one_tender
from .unpacker import UnpackResult, unpack_tender_archive
from .value_parser import NormalizedValue, parse_value, satisfies

__all__ = [
    "AnalysisResult",
    "AnalyzerManifest",
    "ClassifiedFile",
    "Decision",
    "DecisionResult",
    "ExtractedSpec",
    "ExtractionResult",
    "FileCategory",
    "MatchCandidate",
    "NormalizedValue",
    "SpecMatch",
    "UnpackResult",
    "analyze_one_tender",
    "classify_files",
    "decide",
    "extract_from_docx",
    "match_one_candidate",
    "match_tender_to_catalog",
    "parse_value",
    "satisfies",
    "unpack_tender_archive",
]
