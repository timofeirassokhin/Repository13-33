"""Build a compact human-readable summary of an autosearch config.

Outputs structure with UI labels — works around terminal encoding issues.
"""
import json
import sys
from pathlib import Path

DOCS = Path(__file__).parent.parent / "docs"


def coerce_text(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def walk(node, depth=0):
    indent = "  " * depth
    out = []
    if not isinstance(node, dict):
        return out
    if "and" in node:
        out.append(f"{indent}AND ({len(node['and'])}):")
        for sub in node["and"]:
            out.extend(walk(sub, depth + 1))
    elif "or" in node:
        out.append(f"{indent}OR ({len(node['or'])}):")
        for sub in node["or"]:
            out.extend(walk(sub, depth + 1))
    else:
        sn = node.get("name", "?")
        ui = node.get("text", "")
        typ = node.get("type", "?")
        line = f"{indent}- [{sn}] ({typ}) UI=«{ui}»"
        if typ == "text":
            inc = coerce_text(node.get("include"))
            exc = coerce_text(node.get("exclude"))
            line += f"  INC={len(inc)}ch  EXC={len(exc)}ch"
        elif typ == "range":
            line += f"  from={node.get('from')}  to={node.get('to')}"
        elif typ == "value":
            line += f"  value={node.get('value')}"
        elif typ == "tree_list":
            inc = coerce_text(node.get("include"))
            exc = coerce_text(node.get("exclude"))
            line += f"  INC={len(inc)}ch (tree-list ids)  EXC={len(exc)}ch"
        out.append(line)
    return out


def summary(autosearch_id: int, name_label: str, status_emoji: str = "❌"):
    path = DOCS / f"autosearch_{autosearch_id}.json"
    if not path.exists():
        return f"\n## {status_emoji} {name_label} (id {autosearch_id})\n\nFILE NOT FOUND: {path}\n"
    cfg = json.loads(path.read_text(encoding="utf-8-sig"))
    lines = [f"\n## {status_emoji} {name_label} (id {autosearch_id})\n"]
    lines.append("Текущая структура фильтров:\n```")
    lines.extend(walk(cfg["filters"]))
    lines.append(f"interval: {cfg.get('interval')}")
    lines.append("```")
    return "\n".join(lines)


def main():
    targets = [
        (96702, "Agilent (РАБОЧИЙ — образец)", "✅"),
        (96701, "Фильтры мембранные (РАБОЧИЙ — образец)", "✅"),
        (96700, "Оборудование (РАБОЧИЙ — образец)", "✅"),
        (367074, "Все_приборы_аналитики_строгий (СЛОМАН)", "❌"),
        (367099, "Тендеры_приборы_аналитики_строгий (СЛОМАН)", "❌"),
        (367084, "Расходники_хроматограф_строгий (СЛОМАН)", "❌"),
        (367104, "Расходники_хроматограф_строгий актуальный (СЛОМАН)", "❌"),
        (367007, "архив ВЭЖХиМС (СЛОМАН — старый широкий)", "⚠️"),
    ]
    for aid, name, emoji in targets:
        print(summary(aid, name, emoji))


if __name__ == "__main__":
    main()
