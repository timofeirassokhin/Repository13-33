"""Download zip archives of tender documentation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from slugify import slugify

from .api_client import TenderlandAPIError, TenderlandClient
from .models import TenderRow


@dataclass
class DownloadResult:
    row: TenderRow
    path: Path | None
    bytes_written: int
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.path is not None


def _safe_name(row: TenderRow) -> str:
    """Build a short, FS-safe filename for a tender's zip."""
    reg = slugify(row.reg_number, max_length=40, separator="-")
    short = slugify(row.name[:60], max_length=60, separator="-")
    parts = [p for p in (reg, short) if p]
    return ("__".join(parts) or "tender")[:120]


def download_all(
    client: TenderlandClient,
    rows: list[TenderRow],
    out_dir: Path,
    *,
    progress: Callable[[int, int, TenderRow], None] | None = None,
    skip_existing: bool = True,
) -> list[DownloadResult]:
    """Download zip archives for every row that has an entity_id.

    Files are placed flat into out_dir as <regnum>__<short-name>__<entity_id>.zip.
    Returns a list of DownloadResult (in input order, including skipped/failed).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[DownloadResult] = []
    total = len(rows)

    for idx, row in enumerate(rows, 1):
        if progress:
            progress(idx, total, row)

        if not row.entity_id:
            results.append(DownloadResult(row, None, 0, error="no entity_id"))
            continue

        fname = f"{_safe_name(row)}__{row.entity_id}.zip"
        dest = out_dir / fname

        if skip_existing and dest.exists() and dest.stat().st_size > 0:
            results.append(DownloadResult(row, dest, dest.stat().st_size))
            # Tag for exporter
            setattr(row, "local_zip", str(dest))
            continue

        try:
            written = client.download_all_files(row.entity_id, dest)
            setattr(row, "local_zip", str(dest))
            results.append(DownloadResult(row, dest, written))
        except TenderlandAPIError as e:
            # Cleanup partial file
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
            results.append(DownloadResult(row, None, 0, error=f"{e.code}: {e.description}"))
        except Exception as e:
            if dest.exists() and dest.stat().st_size == 0:
                dest.unlink(missing_ok=True)
            results.append(DownloadResult(row, None, 0, error=str(e)))

    return results
