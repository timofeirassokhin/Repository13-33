"""CLI entry point.

Usage examples:

  # List all autosearches in the cabinet
  python -m tenderland_bot list

  # Show current API limits / usage
  python -m tenderland_bot stats

  # Export one autosearch by name (substring match) — list + download all docs
  python -m tenderland_bot export Memmert

  # Export by exact id, limit to first 20 tenders, no zip downloads
  python -m tenderland_bot export 96704 --limit 20 --no-files

  # Export every autosearch
  python -m tenderland_bot export-all

  # Autosearch CRUD (partial — Create only on Pro tier):
  python -m tenderland_bot autosearch list-topics                  # show topics parsed from config/keywords_*.md
  python -m tenderland_bot autosearch get 96700                    # dump JSON of one autosearch
  python -m tenderland_bot autosearch create-from-md 01_LC_LCMS_GPC_Prep   # create new autosearch from MD config
  python -m tenderland_bot autosearch create-from-md 01_LC_LCMS_GPC_Prep --dry-run   # show payload, don't POST
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

# Force UTF-8 stdout on Windows so Cyrillic doesn't crash cp1252 console.
if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table
from slugify import slugify

from .api_client import Autosearch, TenderlandAPIError, TenderlandClient
from .config import load_settings
from .downloader import download_all
from .exporter import write_excel, write_markdown
from .md_parser import Topic, parse_keywords_dir
from .models import TenderRow
from .payload_builder import build_parameters_from_topic, parameters_summary

app = typer.Typer(add_completion=False, help="Tenderland export CLI.")
autosearch_app = typer.Typer(add_completion=False, help="Manage autosearches via API.")
app.add_typer(autosearch_app, name="autosearch")
console = Console()


def _config_dir() -> Path:
    """Path to the config/ directory with keywords_*.md files."""
    here = Path(__file__).resolve().parents[2]  # tenderland_bot/
    return here / "config"


def _client() -> TenderlandClient:
    s = load_settings()
    return TenderlandClient(api_key=s.api_key, base_url=s.base_url, timeout=s.http_timeout)


def _output_dir() -> Path:
    return load_settings().output_dir


def _today_dir(base: Path) -> Path:
    return base / date.today().strftime("%d%m%y")


def _resolve_autosearch(client: TenderlandClient, query: str) -> Autosearch:
    items = client.list_autosearches()
    # Try numeric id first
    if query.isdigit():
        wanted_id = int(query)
        for it in items:
            if it.id == wanted_id:
                return it
    # Substring match on name (case-insensitive)
    q = query.lower().strip()
    candidates = [it for it in items if q in it.name.lower()]
    if not candidates:
        console.print(f"[red]No autosearch matches '{query}'.[/red] Use 'list' to see all.")
        raise typer.Exit(2)
    if len(candidates) > 1:
        console.print(f"[yellow]Multiple matches for '{query}':[/yellow]")
        for c in candidates:
            console.print(f"  {c.id}\t{c.name}")
        console.print("[yellow]Use the exact id.[/yellow]")
        raise typer.Exit(2)
    return candidates[0]


# ---------------- commands ----------------


@app.command("list")
def cmd_list() -> None:
    """List all autosearches available via the API."""
    with _client() as client:
        items = client.list_autosearches()

    table = Table(title=f"Autosearches: {len(items)}")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Workspace")
    for it in sorted(items, key=lambda x: x.name.lower()):
        table.add_row(str(it.id), it.name, it.workspace_name)
    console.print(table)


@app.command("stats")
def cmd_stats() -> None:
    """Show API limits and today's consumption."""
    with _client() as client:
        s = client.get_statistic()
    table = Table(title="Tenderland API limits")
    table.add_column("Metric")
    table.add_column("Used / Limit", justify="right")
    table.add_row("Requests today", f"{s.get('dailyQueryCount', 0)} / {s.get('dailyQueryLimit', 0)}")
    table.add_row(
        "Data units today",
        f"{s.get('dailyDataTransferredCount', 0)} / {s.get('dailyDataTransferredLimit', 0)}",
    )
    table.add_row(
        "Data units this month",
        f"{s.get('monthlyDataTransferredCount', 0)} / {s.get('monthlyDataTransferredLimit', 0)}",
    )
    console.print(table)


@app.command("export")
def cmd_export(
    autosearch: str = typer.Argument(..., help="Autosearch id or name substring."),
    limit: int = typer.Option(0, "--limit", "-n", help="Max tenders (0 = all)."),
    no_files: bool = typer.Option(False, "--no-files", help="Skip zip downloads."),
    out: Path | None = typer.Option(None, "--out", help="Override output base dir."),
    only_md: bool = typer.Option(False, "--only-md", help="Skip Excel, write Markdown only."),
    only_xlsx: bool = typer.Option(False, "--only-xlsx", help="Skip Markdown, write Excel only."),
) -> None:
    """Export one autosearch: tender list (xlsx + md) + zip archives of docs."""
    base_dir = out or _output_dir()
    base_dir.mkdir(parents=True, exist_ok=True)

    with _client() as client:
        target = _resolve_autosearch(client, autosearch)
        console.print(f"[green]Autosearch:[/green] [bold]{target.name}[/bold] (id {target.id})")

        # Create export task
        task = client.create_export(
            autosearch_id=target.id,
            limit=limit if limit > 0 else None,
            batch_size=100,
        )
        if task.total_count == 0:
            console.print("[yellow]Autosearch returned 0 tenders. Nothing to export.[/yellow]")
            return
        console.print(f"Total tenders to fetch: [bold]{task.total_count}[/bold]")

        # Read all pages
        rows: list[TenderRow] = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            tid = progress.add_task("Reading export pages", total=task.total_count)
            for item in client.iter_export(task.id, task.total_count, batch_size=100):
                rows.append(TenderRow.from_export_item(item))
                progress.update(tid, advance=1)

        console.print(f"Fetched [bold]{len(rows)}[/bold] tenders.")

        # Build output paths.
        # Layout: Z:\tenders\<Autosearch>\<Autosearch>_DDMMYY.{xlsx,md}
        #         Z:\tenders\<Autosearch>\DDMMYY\*.zip
        today = date.today().strftime("%d%m%y")
        slug = slugify(target.name, separator="_", lowercase=False)[:60] or f"autosearch_{target.id}"
        autosearch_dir = base_dir / slug
        autosearch_files_dir = autosearch_dir / today  # only zip archives live here

        # Download zip archives FIRST so we can include local paths in the report
        if not no_files:
            console.print(f"Downloading zip archives → [cyan]{autosearch_files_dir}[/cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=console,
            ) as progress:
                dtid = progress.add_task("Downloading docs", total=len(rows))

                def cb(idx: int, total: int, row: TenderRow) -> None:
                    progress.update(dtid, completed=idx)

                results = download_all(client, rows, autosearch_files_dir, progress=cb)
            ok = sum(1 for r in results if r.ok)
            failed = [r for r in results if not r.ok]
            console.print(f"Archives: [green]{ok}[/green] ok, [red]{len(failed)}[/red] failed")
            for r in failed[:10]:
                console.print(f"  [red]{r.row.reg_number}[/red] — {r.error}")
            if len(failed) > 10:
                console.print(f"  ...и ещё {len(failed) - 10}")

        # Write reports — sit next to the DDMMYY folder, inside the autosearch dir.
        autosearch_dir.mkdir(parents=True, exist_ok=True)
        report_base = autosearch_dir / f"{slug}_{today}"
        if not only_md:
            xlsx_path = write_excel(rows, report_base.with_suffix(".xlsx"), autosearch_name=target.name)
            console.print(f"[green]Excel:[/green] {xlsx_path}")
        if not only_xlsx:
            md_path = write_markdown(rows, report_base.with_suffix(".md"), autosearch_name=target.name)
            console.print(f"[green]Markdown:[/green] {md_path}")

        # Final stats
        s = client.get_statistic()
        console.print(
            f"[dim]API today: {s.get('dailyQueryCount', 0)}/{s.get('dailyQueryLimit', 0)} req, "
            f"{s.get('dailyDataTransferredCount', 0)}/{s.get('dailyDataTransferredLimit', 0)} units[/dim]"
        )


@app.command("export-all")
def cmd_export_all(
    limit: int = typer.Option(0, "--limit", "-n", help="Max tenders per autosearch (0 = all)."),
    no_files: bool = typer.Option(False, "--no-files", help="Skip zip downloads."),
    only_md: bool = typer.Option(False, "--only-md"),
    only_xlsx: bool = typer.Option(False, "--only-xlsx"),
) -> None:
    """Run export for every autosearch sequentially."""
    with _client() as client:
        items = client.list_autosearches()
    console.print(f"Will export [bold]{len(items)}[/bold] autosearches.")
    for it in items:
        console.rule(f"{it.name} (id {it.id})")
        try:
            cmd_export(
                autosearch=str(it.id),
                limit=limit,
                no_files=no_files,
                out=None,
                only_md=only_md,
                only_xlsx=only_xlsx,
            )
        except typer.Exit:
            continue
        except TenderlandAPIError as e:
            console.print(f"[red]API error:[/red] {e}")
            if e.code == "API_REQUEST_LIMIT":
                console.print("[red]Daily limit reached, stopping.[/red]")
                sys.exit(1)


# ---------------- autosearch sub-commands ----------------


@autosearch_app.command("list-topics")
def cmd_autosearch_list_topics() -> None:
    """Show all topics parsed from `config/keywords_*.md` (input for create-from-md)."""
    topics = parse_keywords_dir(_config_dir())
    table = Table(title=f"Topics parsed from {_config_dir()}: {len(topics)}")
    table.add_column("Topic name", style="cyan")
    table.add_column("Source file")
    table.add_column("INCLUDE", justify="right")
    table.add_column("EXCLUDE", justify="right")
    table.add_column("Optional", justify="center")
    for name, t in sorted(topics.items()):
        table.add_row(
            name,
            t.file_path.name if t.file_path else "",
            f"{len(t.include_text)}ch",
            f"{len(t.exclude_text)}ch",
            "*" if t.is_optional else "",
        )
    console.print(table)


@autosearch_app.command("get")
def cmd_autosearch_get(
    autosearch_id: int = typer.Argument(..., help="Autosearch id to fetch."),
    save: Path | None = typer.Option(None, "--save", help="Optional path to save the JSON dump."),
) -> None:
    """Read one autosearch as full JSON (fields, filters, interval)."""
    import json
    with _client() as client:
        data = client.get_autosearch(autosearch_id)
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    if save:
        save.write_text(pretty, encoding="utf-8")
        console.print(f"[green]Saved:[/green] {save}")
    # Always show a summary
    console.print(parameters_summary(data))
    console.print(f"[dim](full JSON is {len(pretty)} chars)[/dim]")


@autosearch_app.command("create-from-md")
def cmd_autosearch_create_from_md(
    topic: str = typer.Argument(..., help="Topic name as defined in keywords_*.md (e.g. '01_LC_LCMS_GPC_Prep')"),
    name: str | None = typer.Option(
        None, "--name",
        help="Override the autosearch display name (default = topic name)",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be POSTed; don't actually create.",
    ),
    only_active: bool = typer.Option(
        True, "--only-active/--all-statuses",
        help="Restrict to tender_status=1 (active). Default: on.",
    ),
) -> None:
    """Create a new autosearch in Tenderland from a topic in keywords_*.md.

    Note: on Pro tier, Update/Delete are not available — repeated runs will create
    DUPLICATES. Cleanup unused ones manually in the UI.
    """
    topics = parse_keywords_dir(_config_dir())
    if topic not in topics:
        console.print(f"[red]Topic {topic!r} not found.[/red] Available:")
        for name_ in sorted(topics):
            console.print(f"  - {name_}")
        raise typer.Exit(2)

    t: Topic = topics[topic]
    console.print(f"[green]Topic:[/green] {t.name}")
    console.print(f"  source: {t.file_path.name}:{t.line_number}")
    console.print(f"  INCLUDE: {len(t.include_text)}ch")
    console.print(f"  EXCLUDE: {len(t.exclude_text)}ch")
    console.print(f"  description: {t.description[:80]!r}")

    parameters = build_parameters_from_topic(
        include_text=t.include_text,
        exclude_text=t.exclude_text,
        only_active_tenders=only_active,
    )
    autosearch_name = name or t.name
    console.print(f"\n[bold]Payload preview:[/bold]")
    console.print(f"  Name = {autosearch_name!r}")
    console.print(parameters_summary(parameters))

    if dry_run:
        console.print("\n[yellow]--dry-run: nothing sent to API.[/yellow]")
        return

    console.print(f"\n[bold]POST /Api/v1/Search/CreateAutosearch ...[/bold]")
    with _client() as client:
        try:
            new_id = client.create_autosearch(
                name=autosearch_name,
                parameters=parameters,
            )
        except TenderlandAPIError as e:
            console.print(f"[red]API error:[/red] [{e.code}] {e.description}")
            raise typer.Exit(1)

    console.print(f"[green]CREATED:[/green] new autosearch id = [bold]{new_id}[/bold]")
    console.print(f"  Name: {autosearch_name!r}")
    console.print(f"\n  Tenderland UI URL (approx): https://tenderland.ru/Cabinet/Autosearch/Edit?id={new_id}")
    console.print(f"\n[dim]Tip: append `[[autosearch]] id={new_id}  topic=\"{topic}\"` to config/autosearches.toml[/dim]")


# ---------------- entrypoint ----------------


def main() -> None:
    app()


if __name__ == "__main__":
    main()
