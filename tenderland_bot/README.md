# tenderland_bot

CLI to pull tender lists from the [Tenderland](https://tenderland.ru) API and dump them
to disk for further analysis.

Part 1 of a planned 2-part system:

1. **This** — fetch + persist (autosearch → Excel/MD list + zip archives of docs).
2. **Next** — separate analyser agent that opens the docs, extracts tech specs,
   and matches them against our instrument catalogue.

## Setup

```bash
# from repo root, reuse the existing .venv
.\.venv\Scripts\activate

cd tenderland_bot
pip install -r requirements.txt
copy .env.example .env
# Edit .env if you want a different output dir than Z:/tenders
```

## Commands

```bash
# Show available autosearches
python -m tenderland_bot list

# Show today's API consumption + limits
python -m tenderland_bot stats

# Export one autosearch by name substring (or by numeric id)
python -m tenderland_bot export Memmert
python -m tenderland_bot export 96704

# Limit to 10 newest, skip zip downloads (cheap dry-run)
python -m tenderland_bot export Memmert --limit 10 --no-files

# Run every autosearch sequentially (will burn through daily limits)
python -m tenderland_bot export-all
```

## Output layout

```
Z:\tenders\
└── Memmert\                          # one folder per autosearch
    ├── Memmert_050526.xlsx           # daily report, Excel
    ├── Memmert_050526.md             # daily report, Markdown
    ├── Memmert_060526.xlsx           # next day's run sits next to it (history)
    ├── Memmert_060526.md
    └── 050526\                       # one folder per day with zip archives
        ├── 0332300328026000039__remont-sterilizatora__TL2530006696.zip
        ├── ...
```

- Each autosearch gets its own top-level folder.
- Reports (XLSX + MD) accumulate at the autosearch root — easy to scan history.
- `DDMMYY/` holds the actual zip archives of tender docs for that day.

## API quota notes

- 1 unit = 1 tender returned **or** 1 file inside a downloaded zip.
- This key has 1000 req + 1000 units/day, 30000/month (paid `API` module tier).
- A typical autosearch with 30 tenders × ~5 files ≈ **180 units**. Roughly 5 autosearches/day before hitting the cap.
- Use `--no-files` for cheap list-only runs (1 unit per tender, ~30 units/autosearch).
- `python -m tenderland_bot stats` shows current usage.

## What's NOT here (yet)

- No daily scheduler / email digest — that's part 1.5.
- No webhook receiver — we're pulling on demand for now.
- No spec extraction or product matching — that's the separate analyser agent (part 2).
