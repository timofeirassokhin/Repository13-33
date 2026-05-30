"""Dump structure of working vs broken autosearches for diagnostics."""
import json
import sys
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"


def show_tree(node, ind=0):
    pad = "  " * ind
    if isinstance(node, dict):
        if "and" in node:
            print(pad + f"AND group ({len(node['and'])}):")
            for s in node["and"]:
                show_tree(s, ind + 1)
        elif "or" in node:
            print(pad + f"OR group ({len(node['or'])}):")
            for s in node["or"]:
                show_tree(s, ind + 1)
        else:
            n = node.get("name", "?")
            t = node.get("type", "?")
            ui = node.get("text", "")
            extra = ""
            if "include" in node or "exclude" in node:
                inc = node.get("include") or ""
                exc = node.get("exclude") or ""
                if isinstance(inc, list):
                    inc = " ".join(str(x) for x in inc)
                if isinstance(exc, list):
                    exc = " ".join(str(x) for x in exc)
                extra = f" inc={len(inc)}ch exc={len(exc)}ch"
                if inc:
                    snippet = inc.replace("\n", " ")[:80]
                    extra += f" inc[:80]={snippet!r}"
            elif "from" in node or "to" in node:
                extra = f" from={node.get('from')} to={node.get('to')}"
            elif "value" in node:
                extra = f" value={node.get('value')}"
            print(pad + f"- name={n} type={t} ui={ui!r}{extra}")


def show_full_text_filter(name, fname):
    print("=" * 80)
    print(f"{name} ({fname})")
    print("=" * 80)
    cfg = json.loads((DOCS / fname).read_text(encoding="utf-8-sig"))
    show_tree(cfg["filters"])
    print(f"interval: {cfg.get('interval')}")
    print()


def main():
    show_full_text_filter("AGILENT (рабочий)", "autosearch_96702.json")
    show_full_text_filter("ФИЛЬТРЫ МЕМБРАННЫЕ (рабочий)", "autosearch_96701.json")
    show_full_text_filter("ОБОРУДОВАНИЕ (рабочий)", "autosearch_96700.json")
    show_full_text_filter("Тендеры_приборы_аналитики_строгий (НЕ работает на текущих)", "autosearch_367099.json")
    show_full_text_filter("Расходники_строгий_актуальный (НЕ работает на текущих)", "autosearch_367104.json")

    # Show actual INCLUDE of Agilent for reference
    cfg = json.loads((DOCS / "autosearch_96702.json").read_text(encoding="utf-8-sig"))
    print("=" * 80)
    print("AGILENT INCLUDE (полный текст)")
    print("=" * 80)
    for sub in cfg["filters"]["and"]:
        if isinstance(sub, dict) and sub.get("type") == "text":
            print(sub.get("include") or "")
            print()
            print("---EXCLUDE---")
            print(sub.get("exclude") or "")


if __name__ == "__main__":
    main()
