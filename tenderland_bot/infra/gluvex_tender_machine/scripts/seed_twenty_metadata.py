#!/usr/bin/env python3
"""
Gluvex Tender Machine — идемпотентный seed кастомных полей Twenty CRM.

Запуск:
  source /opt/gluvex/secrets/.env
  TWENTY_API_URL=https://crm.gluvex.com TWENTY_API_TOKEN=$TWENTY_API_TOKEN \\
    python3 seed_twenty_metadata.py

Что делает:
  - Загружает список objects из /rest/metadata/objects
  - Для каждого определённого поля проверяет: существует ли уже на нужном объекте.
  - Если нет — создаёт через POST /rest/metadata/fields.
  - Если есть — пропускает (можно перезапускать сколько угодно раз).

Источник полей: tenderland_bot/ARCHITECTURE.md разделы 5.1 и 8.3.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error

API_URL = os.environ.get("TWENTY_API_URL", "https://crm.gluvex.com").rstrip("/")
API_TOKEN = os.environ.get("TWENTY_API_TOKEN")

if not API_TOKEN:
    sys.exit("error: TWENTY_API_TOKEN env var is required")


# --- описание желаемых кастомных полей ---
# имя поля -> (объект, label, type, isUnique, description)
FIELDS = [
    # Company — реквизиты юрлица для дедупа
    ("company", "inn", "ИНН", "TEXT", True, "ИНН — первичный ключ для дедупа компаний из тендеров"),
    ("company", "ogrn", "ОГРН", "TEXT", False, "ОГРН/ОГРНИП юрлица"),
    ("company", "kpp", "КПП", "TEXT", False, "КПП юрлица"),
]


def http(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{API_URL}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = resp.read().decode("utf-8")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {method} {path}: {body_text}") from None


def list_objects() -> dict[str, dict]:
    """Возвращает {nameSingular: object_dict}"""
    resp = http("GET", "/rest/metadata/objects")
    objs = resp.get("data", {}).get("objects", []) if isinstance(resp, dict) else resp
    if isinstance(resp, list):
        objs = resp
    return {o["nameSingular"]: o for o in objs if isinstance(o, dict)}


def list_fields(object_id: str) -> dict[str, dict]:
    """Возвращает {field name: field_dict} для заданного объекта"""
    resp = http("GET", f"/rest/metadata/objects/{object_id}")
    obj = resp.get("data", {}).get("object", resp) if isinstance(resp, dict) else resp
    fields = []
    if isinstance(obj, dict):
        fields = obj.get("fields", []) or obj.get("fieldsList", [])
    return {f["name"]: f for f in fields if isinstance(f, dict)}


def create_field(object_id: str, name: str, label: str, type_: str, is_unique: bool, description: str) -> dict:
    body = {
        "name": name,
        "label": label,
        "type": type_,
        "objectMetadataId": object_id,
        "isNullable": True,
        "isUnique": is_unique,
        "description": description,
    }
    return http("POST", "/rest/metadata/fields", body)


def main() -> int:
    print(f"==> Twenty Metadata API: {API_URL}")
    objects = list_objects()
    print(f"    {len(objects)} objects loaded")

    created = 0
    skipped = 0
    failed = 0

    for object_name, name, label, type_, is_unique, description in FIELDS:
        obj = objects.get(object_name)
        if not obj:
            print(f"  ✗ object '{object_name}' not found, skipping field '{name}'")
            failed += 1
            continue

        object_id = obj["id"]
        existing = list_fields(object_id)
        if name in existing:
            print(f"  • {object_name}.{name:25s} already exists, skip")
            skipped += 1
            continue

        try:
            create_field(object_id, name, label, type_, is_unique, description)
            print(f"  ✓ {object_name}.{name:25s} created  ({type_}{', unique' if is_unique else ''})")
            created += 1
        except RuntimeError as e:
            print(f"  ✗ {object_name}.{name:25s} FAILED: {e}")
            failed += 1

    print()
    print(f"==> created: {created}  skipped: {skipped}  failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
