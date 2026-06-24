"""CLI: `python -m tenderland_bot.analyzer analyze <archive.zip>`.

Минимальная команда для smoke-теста на реальных архивах.
Позже расширим до полноценного pipeline (extractor + matcher).
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .classifier import classify_files, FileCategory
from .extractor import ExtractionResult, extract_from_docx
from .manifest import AnalyzerManifest
from .unpacker import unpack_tender_archive


def cmd_analyze(args: argparse.Namespace) -> int:
    archive = Path(args.archive)
    output_root = Path(args.output_root)

    result = unpack_tender_archive(archive, output_root)

    primary = result.primary_files()
    classified = classify_files(primary)

    # Подписи — отдельная категория, добавим в манифест для полноты
    from .classifier import ClassifiedItem
    for sig in result.signature_files:
        classified.setdefault(FileCategory.SIGNATURE, []).append(
            ClassifiedItem(
                path=sig,
                category=FileCategory.SIGNATURE,
                matched_rule="prefix:EDS_",
                size_bytes=sig.stat().st_size if sig.exists() else 0,
            )
        )

    manifest = AnalyzerManifest.build(
        tender_id=result.tender_id,
        source_archive=result.source_zip,
        unpacked_dir=result.output_dir,
        classified=classified,
        nested_zips_unpacked=result.nested_zips_unpacked,
        failed_unpack_entries=result.failed_entries,
        signature_files_count=len(result.signature_files),
    )

    # Запускаем DOCX extractor на TZ / QUOTATION_REQUEST файлах (только .docx)
    if not args.skip_extract:
        extraction_targets = []
        for cat in (FileCategory.TZ, FileCategory.QUOTATION_REQUEST):
            for item in classified.get(cat, []):
                if item.path.suffix.lower() == ".docx":
                    extraction_targets.append((cat, item.path))

        for cat, p in extraction_targets:
            er = extract_from_docx(p)
            if er.error:
                manifest.extractor_notes.append(
                    f"[{cat.value}] {p.name}: ERROR {er.error}"
                )
                continue
            entry = er.to_dict()
            entry["source_category"] = cat.value
            # Превратим путь в относительный для манифеста
            try:
                entry["source_file"] = str(p.relative_to(result.output_dir)).replace("\\", "/")
            except ValueError:
                pass
            manifest.extracted_specs.append(entry)
            manifest.extractor_notes.append(
                f"[{cat.value}] {p.name}: {er.strategy_used}, {len(er.specs)} specs"
            )

    if args.manifest_out:
        manifest_path = Path(args.manifest_out)
    else:
        # По умолчанию — рядом с output_dir в подпапку analysis/
        manifest_path = result.output_dir.parent / "analysis" / f"{result.tender_id}.json"

    manifest.write(manifest_path)

    # Краткое human-readable резюме в stdout
    print(f"=== {result.tender_id} ===")
    print(f"source:   {result.source_zip.name}")
    print(f"unpacked: {result.output_dir}")
    print(f"manifest: {manifest_path}")
    print(f"files:    {len(primary)} primary + {len(result.signature_files)} signature")
    print(f"nested:   {result.nested_zips_unpacked} zips unpacked")
    if result.failed_entries:
        print(f"errors:   {len(result.failed_entries)}")
    print()
    for cat, items in sorted(classified.items(), key=lambda x: x[0].value):
        print(f"  [{cat.value:<18}] x{len(items)}")
        for it in items:
            marker = "*" if cat.is_analyzable else " "
            print(f"    {marker} {it.name}")

    if manifest.extracted_specs:
        print()
        print(f"extracted_specs: {len(manifest.extracted_specs)} document(s)")
        for entry in manifest.extracted_specs:
            print(
                f"  - {entry['strategy_used']:<12} "
                f"specs={len(entry['specs']):<3} "
                f"product='{entry.get('product_name','')[:60]}' "
                f"okpd2='{entry.get('ktru_okpd2_code','')}'"
            )
    return 0


def cmd_analyze_dir(args: argparse.Namespace) -> int:
    """Пройти по всем zip'ам в директории и проанализировать каждый."""
    directory = Path(args.directory)
    output_root = Path(args.output_root)

    zips = sorted(directory.glob("*.zip"))
    if not zips:
        print(f"no .zip files in {directory}", file=sys.stderr)
        return 1

    exit_code = 0
    for z in zips:
        try:
            ns = argparse.Namespace(
                archive=str(z),
                output_root=str(output_root),
                manifest_out=None,
                skip_extract=args.skip_extract,
            )
            rc = cmd_analyze(ns)
            if rc != 0:
                exit_code = rc
        except Exception as exc:
            print(f"!! failed {z.name}: {exc}", file=sys.stderr)
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    # На Windows консольный stdout по умолчанию cp1252 — ломается на кириллице.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(prog="python -m tenderland_bot.analyzer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_one = sub.add_parser("analyze", help="Analyze a single tender zip archive")
    p_one.add_argument("archive", help="Path to tender zip archive")
    p_one.add_argument(
        "--output-root",
        default="./unpacked",
        help="Root dir for unpacked tender contents (default: ./unpacked)",
    )
    p_one.add_argument(
        "--manifest-out",
        default=None,
        help="Explicit path for manifest JSON (default: <output_root>/../analysis/<TL-id>.json)",
    )
    p_one.add_argument(
        "--skip-extract",
        action="store_true",
        help="Only unpack + classify, skip DOCX content extraction",
    )
    p_one.set_defaults(func=cmd_analyze)

    p_dir = sub.add_parser("analyze-dir", help="Analyze every .zip in a directory")
    p_dir.add_argument("directory", help="Directory containing tender zip files")
    p_dir.add_argument("--output-root", default="./unpacked")
    p_dir.add_argument("--skip-extract", action="store_true")
    p_dir.set_defaults(func=cmd_analyze_dir)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
