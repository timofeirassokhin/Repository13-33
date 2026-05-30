# -*- coding: utf-8 -*-
"""Фокусный pipeline: выгрузка указанных автопоисков + Tier-2 + Excel.

Использует тот же код что и run_tier2_and_excel.py, но:
- работает только с заданным списком id/topic
- сохраняет в отдельную папку (default: _api_check/focused/<DDMMYY>/)
- Excel выпадает туда же

Запуск:
    PYTHONPATH=src python scripts/run_focused_pipeline.py \\
        --ids 373417=MDX_01_Sequencers,373430=MDX_02_Reagents_Libraries,373451=MDX_03_Oncology_Panels,373453=MDX_04_NIPT_PGT_HLA,373454=MDX_06_Sequencing_Services \\
        --limit 100 \\
        --label mdx_weekly
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import time
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Подгрузим .env
env_path = ROOT / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if v and not os.environ.get(k):
            os.environ[k] = v

from tenderland_bot.api_client import TenderlandClient, TenderlandAPIError
from tenderland_bot.config import load_settings
from tenderland_bot.relevance import Tier2Decision, classify_batch

# Переиспользуем build_excel и progress из run_tier2_and_excel
sys.path.insert(0, str(ROOT / "scripts"))
from run_tier2_and_excel import build_excel  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--ids", required=True,
                   help="id=topic,id=topic,... (например 373417=MDX_01_Sequencers)")
    p.add_argument("--limit", type=int, default=100,
                   help="максимум тендеров на тему (default 100)")
    p.add_argument("--label", default="focused",
                   help="имя подпапки в _api_check/<label>/<DDMMYY>/")
    return p.parse_args()


def collect(client, ids: list[tuple[int, str]], limit: int, out_dir: Path) -> list[tuple[str, str, dict]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks: list[tuple[str, str, dict]] = []
    for aid, topic in ids:
        try:
            task = client.create_export(autosearch_id=aid, limit=limit, batch_size=min(limit, 100))
            total = task.total_count
            items = []
            if total > 0:
                for it in client.iter_export(task.id, min(total, limit), batch_size=min(limit, 100)):
                    items.append(it)
            (out_dir / f"{aid}_{topic}.json").write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  {aid:>7} {topic:<35} total={total:>4} sampled={len(items)}")
            for it in items:
                t = it.get("tender") or {}
                tid = t.get("regNumber") or it.get("ordinalNumber", "?")
                tasks.append((f"{topic}::{tid}", topic, t))
        except TenderlandAPIError as e:
            print(f"  {aid} {topic} ERR {e.code}: {e.description}")
        time.sleep(0.15)
    return tasks


def main():
    args = parse_args()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY не найден в .env / окружении")
        sys.exit(2)

    ids: list[tuple[int, str]] = []
    for pair in args.ids.split(","):
        pair = pair.strip()
        sid, topic = pair.split("=", 1)
        ids.append((int(sid), topic))

    stamp = date.today().isoformat()
    out_dir = ROOT / "_api_check" / args.label / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f">> Сбор {len(ids)} автопоисков -&gt; {out_dir}")
    s = load_settings()
    with TenderlandClient(api_key=s.api_key, base_url=s.base_url, timeout=s.http_timeout) as c:
        t0 = time.time()
        tasks = collect(c, ids, args.limit, out_dir)
        print(f"   собрано {len(tasks)} тендеров за {time.time()-t0:.1f} сек")
        stats = c.get_statistic()
        print(f"   API quota: {stats.get('dailyQueryCount')}/{stats.get('dailyQueryLimit')} req, "
              f"{stats.get('dailyDataTransferredCount')}/{stats.get('dailyDataTransferredLimit')} units")

    if not tasks:
        print("   нечего классифицировать — выходим")
        return

    print(f"\n>> Tier-2 на {len(tasks)} тендерах ...")
    t0 = time.time()
    state = {"in": 0, "out": 0, "cost": 0.0}

    def progress(i, total, d):
        state["in"] += d.input_tokens
        state["out"] += d.output_tokens
        state["cost"] += d.cost_usd
        if i % 10 == 0 or i == total:
            print(f"   [{i:>4}/{total}] conf={d.confidence:.2f} {d.relevance:<6} "
                  f"in={state['in']:>6} out={state['out']:>6} cost=${state['cost']:.4f}")

    decisions = classify_batch(tasks, progress_cb=progress)
    elapsed = time.time() - t0
    print(f"   готово за {elapsed:.1f} сек, total cost: ${state['cost']:.4f}")

    # Сохраним сырые решения
    (out_dir / f"decisions_{stamp}.json").write_text(
        json.dumps([d.model_dump() for d in decisions], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    xlsx_path = out_dir / f"Tenderland_{args.label}_{stamp}.xlsx"
    meta = {
        "total_in": len(tasks),
        "model": decisions[0].model if decisions else "n/a",
        "elapsed_sec": elapsed,
        "in_tokens": state["in"],
        "out_tokens": state["out"],
        "cost_usd": state["cost"],
    }
    build_excel(decisions, tasks, xlsx_path, meta)

    high = sum(1 for d in decisions if d.confidence >= 0.90 and d.customer_class != "blacklist")
    mid = sum(1 for d in decisions if 0.75 <= d.confidence < 0.90 and d.customer_class != "blacklist")
    drop = sum(1 for d in decisions if d.confidence < 0.75 or d.customer_class == "blacklist")

    print()
    print(f"  HIGH (>=0.90): {high}")
    print(f"  MID  (0.75-0.90): {mid}")
    print(f"  DROP: {drop}")
    print()
    print(f"Excel: {xlsx_path}")


if __name__ == "__main__":
    main()
