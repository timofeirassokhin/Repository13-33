"""Extract all Drive MCP base64 downloads from tool-results folder into XLSX files.

Scans the agent's tool-results directory, finds download_file_content JSON files,
base64-decodes the `content` field and saves to a target dir using the original `title`.

Usage:
  python tools/extract_drive_downloads.py <tool_results_dir> <output_dir>
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("tool_results_dir")
    parser.add_argument("output_dir")
    args = parser.parse_args(argv)

    src_dir = Path(args.tool_results_dir)
    dst_dir = Path(args.output_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(src_dir.glob("mcp-*-download_file_content-*.txt"))
    print(f"Found {len(files)} download result files")

    saved = 0
    for f in files:
        try:
            data = json.loads(f.read_bytes())
        except Exception as e:
            print(f"  [skip] {f.name}: {e}")
            continue

        title = data.get("title", "")
        content_b64 = data.get("content", "")
        if not title or not content_b64:
            continue

        # Sanitize filename
        safe = title.replace("/", "_").replace("\\", "_").replace(":", "_")
        # Replace spaces with _ for shell-safety
        safe = safe.replace(" ", "_")
        out_path = dst_dir / safe

        try:
            out_path.write_bytes(base64.b64decode(content_b64))
            print(f"  → {safe} ({out_path.stat().st_size:,} bytes)")
            saved += 1
        except Exception as e:
            print(f"  [err] {title}: {e}")

    print(f"\nDone: {saved} files saved to {dst_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
