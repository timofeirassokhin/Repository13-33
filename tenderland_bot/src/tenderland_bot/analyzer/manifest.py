"""Манифест результата анализа одного тендера — JSON-сериализуемый."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .classifier import ClassifiedItem, FileCategory


@dataclass
class ClassifiedFile:
    """Файл в манифесте — относительный путь от output_dir."""

    relative_path: str
    name: str
    category: str
    size_bytes: int
    matched_rule: str = ""

    @classmethod
    def from_classified_item(cls, item: ClassifiedItem, base_dir: Path) -> "ClassifiedFile":
        try:
            rel = item.path.relative_to(base_dir)
        except ValueError:
            rel = item.path
        return cls(
            relative_path=str(rel).replace("\\", "/"),
            name=item.name,
            category=item.category.value,
            size_bytes=item.size_bytes,
            matched_rule=item.matched_rule,
        )


@dataclass
class AnalyzerManifest:
    """Что записывается в `analysis/<TL-id>.json` рядом с архивом."""

    tender_id: str
    source_archive: str
    unpacked_dir: str
    analyzed_at: str  # ISO timestamp
    schema_version: int = 1

    nested_zips_unpacked: int = 0
    failed_unpack_entries: list[str] = field(default_factory=list)
    signature_files_count: int = 0

    files_by_category: dict[str, list[ClassifiedFile]] = field(default_factory=dict)
    summary: dict[str, int] = field(default_factory=dict)

    # Заполняется позже extractor'ом
    extracted_specs: list[dict] = field(default_factory=list)
    extractor_notes: list[str] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        tender_id: str,
        source_archive: Path,
        unpacked_dir: Path,
        classified: dict[FileCategory, list[ClassifiedItem]],
        nested_zips_unpacked: int = 0,
        failed_unpack_entries: list[str] | None = None,
        signature_files_count: int = 0,
    ) -> "AnalyzerManifest":
        files_by_category: dict[str, list[ClassifiedFile]] = {}
        summary: dict[str, int] = {}
        for cat, items in classified.items():
            key = cat.value
            files_by_category[key] = [
                ClassifiedFile.from_classified_item(it, unpacked_dir) for it in items
            ]
            summary[key] = len(items)

        return cls(
            tender_id=tender_id,
            source_archive=str(source_archive),
            unpacked_dir=str(unpacked_dir),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            nested_zips_unpacked=nested_zips_unpacked,
            failed_unpack_entries=failed_unpack_entries or [],
            signature_files_count=signature_files_count,
            files_by_category=files_by_category,
            summary=summary,
        )

    def to_json(self, indent: int = 2) -> str:
        def _dict_factory(items):
            return {k: v for k, v in items}

        return json.dumps(asdict(self, dict_factory=_dict_factory), ensure_ascii=False, indent=indent)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
