"""Authenticated SOTAX Campus brochure downloader.

Логинится через TYPO3 felogin POST endpoint (`/user_section/login`),
получает `fe_typo_user` cookie, идёт по всем 4 разделам downloads
(brochures, application_notes, certificates, others), парсит eID=dumpFile
ссылки и качает все PDF.

Использование:
  python tools/sotax_brochure_grabber.py \\
      --user brynza@gmail.com --pass 4ofakind \\
      --out /tmp/sotax_pdfs

Файлы сохраняются как f<ID>_<title-slug>.pdf — token из URL прячется.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import unquote

import requests

BASE = "https://www.sotax.com"
LOGIN_URL = f"{BASE}/user_section/login"
SECTIONS = [
    "/sotax_group/downloads/brochures",
    "/sotax_group/downloads/application_notes",
    "/sotax_group/downloads/certificates",
    "/sotax_group/downloads/others",
]

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def slugify(s: str, maxlen: int = 80) -> str:
    s = re.sub(r"[®©™]", "", s)
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"[^\w\-_.]", "", s, flags=re.UNICODE)
    return s[:maxlen]


def login(session: requests.Session, user: str, password: str) -> bool:
    """Returns True if login succeeded (fe_typo_user cookie set)."""
    # 1. GET login page (warm cookies)
    session.get(LOGIN_URL, headers={"User-Agent": UA})
    # 2. POST credentials
    data = {
        "user": user,
        "pass": password,
        "logintype": "login",
        "pid": "448",
        "redirect_url": "",
        "tx_felogin_pi1[noredirect]": "0",
    }
    r = session.post(
        LOGIN_URL,
        data=data,
        headers={"User-Agent": UA, "Referer": LOGIN_URL},
        allow_redirects=True,
    )
    # fe_typo_user cookie indicates authenticated session
    fe = session.cookies.get("fe_typo_user")
    print(f"  login response status: {r.status_code}", file=sys.stderr)
    print(f"  fe_typo_user cookie: {fe[:16] + '...' if fe else 'NONE'}", file=sys.stderr)
    return fe is not None


def extract_brochures(html: str) -> list[dict]:
    """Returns list of {file_id, token, title, url} entries."""
    items: list[dict] = []
    seen_ids: set[str] = set()
    # Pattern: href links + nearby text/title
    # TYPO3 typically wraps each download in <a href="..."><span>Title</span>...
    # We'll match each href and try to find an associated title in surrounding HTML.
    # Format: <a href="/index.php?eID=dumpFile&t=f&f=NNN&token=HEX"...><div class="column ce-uploads-fileName">TITLE</div>...
    # Note: `&` is NOT HTML-encoded as `&amp;` in this CMS rendering
    for m in re.finditer(
        r'<a[^>]*href="(/index\.php\?eID=dumpFile&(?:amp;)?t=f&(?:amp;)?f=(\d+)&(?:amp;)?token=([a-f0-9]+))"[^>]*>([\s\S]{0,2500}?)</a>',
        html,
    ):
        url_raw, fid, token, body = m.groups()
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        url = unescape(url_raw)
        # Try ce-uploads-fileName div first (TYPO3 uploads CType)
        title_m = re.search(r'class="[^"]*ce-uploads-fileName[^"]*"[^>]*>([^<]+)', body)
        if title_m:
            title = unescape(title_m.group(1)).strip()
        else:
            # Fallback: strip tags from body
            clean = re.sub(r"<[^>]+>", " ", body)
            clean = re.sub(r"\s+", " ", clean).strip()
            title = unescape(clean[:160]) if clean else f"file_{fid}"
        items.append({
            "file_id": fid,
            "token": token,
            "title": title,
            "url": BASE + url,
        })
    return items


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", "--pass", dest="password", required=True)
    ap.add_argument("--out", required=True, help="Output directory for PDFs")
    ap.add_argument("--sections", nargs="*", default=SECTIONS)
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip PDF download, just list")
    ap.add_argument("--max", type=int, default=0,
                    help="Max PDFs to download (0=all)")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = UA

    print(f"=== Logging in as {args.user} ===", file=sys.stderr)
    if not login(session, args.user, args.password):
        print("ERROR: login failed (no fe_typo_user cookie)", file=sys.stderr)
        return 2

    all_items: list[dict] = []
    by_section: dict[str, list[dict]] = {}

    for section in args.sections:
        print(f"\n=== Scanning {section} ===", file=sys.stderr)
        r = session.get(BASE + section, timeout=30)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}, skip", file=sys.stderr)
            continue
        items = extract_brochures(r.text)
        for it in items:
            it["section"] = section.split("/")[-1]
        by_section[section] = items
        all_items.extend(items)
        print(f"  Found {len(items)} downloads", file=sys.stderr)

    # Dedup by file_id (some files appear in multiple sections)
    seen = set()
    deduped: list[dict] = []
    for it in all_items:
        if it["file_id"] in seen:
            continue
        seen.add(it["file_id"])
        deduped.append(it)

    print(f"\n=== Total unique downloads: {len(deduped)} ===", file=sys.stderr)

    # Save manifest
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps({"items": deduped, "by_section": {k: len(v) for k, v in by_section.items()}},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"Manifest → {manifest_path}", file=sys.stderr)

    if args.dry_run:
        print("DRY-RUN: skipping downloads", file=sys.stderr)
        return 0

    downloaded = 0
    skipped = 0
    failed = 0
    to_dl = deduped[:args.max] if args.max > 0 else deduped

    for i, it in enumerate(to_dl, 1):
        name = f"f{it['file_id']}__{slugify(it['title'])}.pdf"
        out_path = out_dir / name
        if out_path.exists() and out_path.stat().st_size > 1000:
            skipped += 1
            continue

        try:
            r = session.get(it["url"], timeout=60, stream=True)
            ctype = r.headers.get("Content-Type", "")
            if r.status_code != 200:
                print(f"  [{i}/{len(to_dl)}] HTTP {r.status_code}: {it['title'][:50]}", file=sys.stderr)
                failed += 1
                continue
            if "pdf" not in ctype.lower() and not r.content.startswith(b"%PDF"):
                # Save anyway with .bin extension
                print(f"  [{i}/{len(to_dl)}] WARN: not PDF (ctype={ctype}), saving as .bin: {it['title'][:50]}", file=sys.stderr)
                out_path = out_path.with_suffix(".bin")

            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
            size = out_path.stat().st_size
            print(f"  [{i}/{len(to_dl)}] {size:>9,}B  {name}", file=sys.stderr)
            downloaded += 1
            time.sleep(0.4)  # be polite
        except Exception as e:
            print(f"  [{i}/{len(to_dl)}] ERROR: {e}: {it['title'][:50]}", file=sys.stderr)
            failed += 1

    print(f"\n=== DONE: {downloaded} downloaded, {skipped} skipped, {failed} failed ===",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
