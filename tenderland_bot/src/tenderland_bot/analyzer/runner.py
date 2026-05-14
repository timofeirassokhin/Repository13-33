"""Runner: end-to-end оркестрация анализатора одного тендера.

Связывает все компоненты analyzer в единую pipeline:

  unzip → classify → extract (DOCX/PDF/HTML/DOC) → value-parse → match → decide → persist

Использует:
  - `unpacker.unpack_tender_archive`  — распаковка zip-архива
  - `classifier.classify_files`        — определение типа каждого файла
  - `extractor.extract_from_docx`      — DOCX → ExtractedSpec[]
  - (TODO) extract_from_pdf, extract_from_html, extract_from_doc
  - `matcher.match_tender_to_catalog`  — extracted ↔ product catalog
  - `decision.decide`                  — pass/review/fail
  - `manifest.AnalyzerManifest`        — JSON-результат на диск

CLI: см. `__main__.py` команда `analyze` — уже использует все компоненты
кроме matcher/decision (пока БД catalog'а не интегрирована).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .classifier import FileCategory, classify_files
from .decision import Decision, DecisionResult, decide
from .extractor import ExtractedSpec, ExtractionResult, extract_from_docx
from .manifest import AnalyzerManifest
from .matcher import MatchCandidate, match_tender_to_catalog
from .unpacker import UnpackResult, unpack_tender_archive

log = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Итоговый результат анализа одного тендера."""

    tender_id: str
    unpack: UnpackResult
    manifest: AnalyzerManifest
    extracted_specs: list[ExtractedSpec] = field(default_factory=list)
    candidates: list[MatchCandidate] = field(default_factory=list)
    decision: DecisionResult | None = None

    @property
    def decision_value(self) -> str:
        return self.decision.decision.value if self.decision else "not_decided"


# Тип callback'а для подгрузки catalog'а — caller передаёт функцию
# (категория, brand-hint) → список продуктов-кандидатов из БД.
CatalogProvider = Callable[[list[str], str | None], list[dict[str, Any]]]


def analyze_one_tender(
    archive_path: Path,
    output_root: Path,
    *,
    catalog_provider: CatalogProvider | None = None,
    tender_id: str | None = None,
    write_manifest: bool = True,
) -> AnalysisResult:
    """Прогнать один тендерный архив через весь pipeline.

    :param archive_path: путь к zip-архиву тендера (типично `Z:\\tenders\\<topic>\\DDMMYY\\*.zip`)
    :param output_root: корневая папка для распаковки + analysis manifests
    :param catalog_provider: callable, который вернёт список кандидатов из каталога.
            Если None — matching пропускается, decision = FAIL ("catalog unavailable").
            Сигнатура: `provider(categories: list[str], brand_hint: str | None) -> list[dict]`
            где dict — product row с ключами {id, brand, model, category, base_specs, ...}.
    :param tender_id: если None — выводится из имени архива (`*__TL12345.zip`)
    :param write_manifest: записать ли манифест в `output_root/../analysis/<id>.json`
    """

    # 1) Unpack
    unpack = unpack_tender_archive(archive_path, output_root, tender_id=tender_id)
    primary = unpack.primary_files()

    # 2) Classify
    classified = classify_files(primary)

    # 3) Extract specs из аналитических файлов
    extracted: list[ExtractedSpec] = []
    extractor_notes: list[str] = []
    product_name_hint = ""
    okpd2_code = ""

    for cat in (FileCategory.TZ, FileCategory.QUOTATION_REQUEST):
        for item in classified.get(cat, []):
            ext = item.path.suffix.lower()
            if ext == ".docx":
                er = extract_from_docx(item.path)
                if er.error:
                    extractor_notes.append(f"[{cat.value}] {item.name}: ERR {er.error}")
                    continue
                extracted.extend(er.specs)
                if not product_name_hint and er.product_name:
                    product_name_hint = er.product_name
                if not okpd2_code and er.ktru_okpd2_code:
                    okpd2_code = er.ktru_okpd2_code
                extractor_notes.append(
                    f"[{cat.value}] {item.name}: {er.strategy_used}, "
                    f"{len(er.specs)} specs"
                )
            elif ext == ".pdf":
                extractor_notes.append(f"[{cat.value}] {item.name}: PDF extractor TODO")
            elif ext in (".doc", ".rtf"):
                extractor_notes.append(
                    f"[{cat.value}] {item.name}: legacy {ext} — LibreOffice convert TODO"
                )
            elif ext == ".html":
                extractor_notes.append(f"[{cat.value}] {item.name}: HTML extractor TODO")

    # 4) Build manifest
    manifest = AnalyzerManifest.build(
        tender_id=unpack.tender_id,
        source_archive=unpack.source_zip,
        unpacked_dir=unpack.output_dir,
        classified=classified,
        nested_zips_unpacked=unpack.nested_zips_unpacked,
        failed_unpack_entries=unpack.failed_entries,
        signature_files_count=len(unpack.signature_files),
    )

    # Положить extracted specs прямо в манифест
    if extracted:
        manifest.extracted_specs.append({
            "product_name": product_name_hint,
            "okpd2": okpd2_code,
            "specs_count": len(extracted),
            "specs": [s.to_dict() for s in extracted],
        })
    manifest.extractor_notes.extend(extractor_notes)

    # 5) Match against catalog (если catalog_provider задан и есть specs)
    candidates: list[MatchCandidate] = []
    if catalog_provider and extracted:
        from .matcher import categories_for_okpd2
        cats = categories_for_okpd2(okpd2_code) if okpd2_code else []
        log.info(
            "matching tender %s: okpd2=%r → categories=%s; product_name_hint=%r",
            unpack.tender_id, okpd2_code, cats, product_name_hint[:80],
        )
        try:
            candidate_products = catalog_provider(cats, product_name_hint)
            log.info("catalog returned %d candidates", len(candidate_products))
            candidates = match_tender_to_catalog(extracted, candidate_products, top_n=5)
        except Exception as exc:
            extractor_notes.append(f"catalog/match failed: {exc}")
            log.exception("catalog/match failed for tender %s", unpack.tender_id)

    # 6) Decision
    decision = decide(candidates, total_extracted_specs=len(extracted))

    # Положить candidates+decision в манифест
    if candidates:
        manifest.extractor_notes.append(
            f"top match: {candidates[0].brand} {candidates[0].model} score {candidates[0].score:.0f}"
        )
    manifest.extractor_notes.append(f"DECISION: {decision.decision.value} — {decision.reason}")

    # 7) Persist manifest
    if write_manifest:
        manifest_path = unpack.output_dir.parent / "analysis" / f"{unpack.tender_id}.json"
        manifest.write(manifest_path)
        log.info("manifest written: %s", manifest_path)

    return AnalysisResult(
        tender_id=unpack.tender_id,
        unpack=unpack,
        manifest=manifest,
        extracted_specs=extracted,
        candidates=candidates,
        decision=decision,
    )
