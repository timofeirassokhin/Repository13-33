"""CLI: tenderland_bot.document_extractor

Examples:
  python -m tenderland_bot.document_extractor extract path/to/file.pdf
  python -m tenderland_bot.document_extractor extract path/to/file.docx --json
  python -m tenderland_bot.document_extractor batch <dir>
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .core import extract_document


def _print_summary(out, json_mode: bool = False) -> None:
    if json_mode:
        d = out.to_dict()
        # обрезаем текст в JSON-mode для читаемости
        if len(d.get("text", "")) > 2000:
            d["text_preview"] = d["text"][:2000] + "...[truncated]"
            del d["text"]
        print(json.dumps(d, ensure_ascii=False, indent=2))
        return

    print(f"=== {out.source_file.name} ===")
    print(f"  type:       {out.file_type}")
    print(f"  extractor:  {out.extractor_name}")
    if out.error:
        print(f"  ERROR:      {out.error}")
        return
    print(f"  pages:      {out.pages_count}")
    print(f"  paragraphs: {len(out.paragraphs)}")
    print(f"  tables:     {len(out.tables)}")
    if out.tables:
        for i, t in enumerate(out.tables[:5]):
            print(f"    table[{i}] shape={t.shape} page={t.page}")
    print(f"  text size:  {len(out.text)} chars")
    if out.text:
        print(f"  text preview (first 300ch):")
        print("    " + out.text[:300].replace("\n", "\n    "))
    if out.notes:
        print(f"  notes:")
        for n in out.notes:
            print(f"    - {n}")
    if out.metadata:
        print(f"  metadata: {out.metadata}")


def cmd_extract(args: argparse.Namespace) -> int:
    out = extract_document(Path(args.file))
    _print_summary(out, json_mode=args.json)
    return 0 if out.error is None else 1


def cmd_batch(args: argparse.Namespace) -> int:
    d = Path(args.dir)
    if not d.is_dir():
        print(f"not a directory: {d}", file=sys.stderr)
        return 1

    exts = (".pdf", ".docx", ".doc", ".rtf", ".html", ".htm", ".xlsx", ".xlsm")
    files = sorted([f for f in d.rglob("*") if f.is_file() and f.suffix.lower() in exts])
    print(f"Found {len(files)} files")
    for f in files:
        try:
            out = extract_document(f)
            marker = "X" if out.error else "+"
            print(f"  [{marker}] {f.relative_to(d)}  → {out.extractor_name}  "
                  f"text={len(out.text)}ch tables={len(out.tables)} "
                  f"{out.error or ''}")
        except Exception as exc:
            print(f"  [!] {f.relative_to(d)}  EXCEPTION: {exc}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    parser = argparse.ArgumentParser(prog="python -m tenderland_bot.document_extractor")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ext = sub.add_parser("extract", help="Extract one file (PDF/DOC/DOCX/HTML/XLSX)")
    p_ext.add_argument("file")
    p_ext.add_argument("--json", action="store_true", help="JSON output")
    p_ext.set_defaults(func=cmd_extract)

    p_batch = sub.add_parser("batch", help="Extract every supported file in a directory tree")
    p_batch.add_argument("dir")
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
