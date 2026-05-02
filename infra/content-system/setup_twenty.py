#!/usr/bin/env python3
"""
Создаёт в Twenty CRM custom-objects под контент-систему 13-33.

Запуск (на сервере):
    sudo python3 /opt/stack/Repository13-33/infra/content-system/setup_twenty.py

Скрипт:
  1. Подключается к Twenty (читает TWENTY_API_KEY из .env)
  2. Создаёт объекты Direction, Channel, Topic, Idea, Draft, Publication
  3. Добавляет к каждому объекту все поля (TEXT/NUMBER/BOOLEAN/DATE_TIME)
  4. Создаёт релейшены между ними
  5. Заливает 3 Direction (Душа, Материальный мир, Дух) и 5 Channel (TG/FB/VK/Дзен/Site)

Если на каком-то шаге будет ошибка — скрипт остановится и распечатает её.
Запускать можно повторно — он сначала проверяет, что объекта ещё нет.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ENV_PATH = "/opt/stack/Repository13-33/infra/.env"
META_URL = "https://crm.13-33.pro/metadata"
DATA_URL = "https://crm.13-33.pro/graphql"


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def load_token() -> str:
    text = Path(ENV_PATH).read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("TWENTY_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"TWENTY_API_KEY не найден в {ENV_PATH}")


def gql(url: str, query: str, variables: dict | None = None, token: str = "") -> dict:
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code} from {url}\n{body}")
    except URLError as e:
        sys.exit(f"Network error: {e}")
    if data.get("errors"):
        msg = json.dumps(data["errors"], ensure_ascii=False, indent=2)
        sys.exit(f"GraphQL error на {url}:\n{msg}\n\nПолный ответ:\n{json.dumps(data, ensure_ascii=False, indent=2)}")
    return data["data"]


def log(msg: str) -> None:
    print(f"  {msg}", flush=True)


# ----------------------------------------------------------------------------
# Metadata API operations
# ----------------------------------------------------------------------------

def list_custom_objects(token: str) -> list[dict]:
    """Returns list of custom (non-system) objects."""
    q = """
    {
      objects(paging: { first: 200 }) {
        edges {
          node {
            id
            nameSingular
            namePlural
            isCustom
          }
        }
      }
    }
    """
    try:
        data = gql(META_URL, q, token=token)
    except SystemExit:
        # paging may not be supported — try without
        q2 = "{ objects { edges { node { id nameSingular namePlural isCustom } } } }"
        data = gql(META_URL, q2, token=token)
    return [edge["node"] for edge in data["objects"]["edges"]]


def delete_object(token: str, object_id: str) -> None:
    q = """
    mutation DeleteOneObject($input: DeleteOneObjectInput!) {
      deleteOneObject(input: $input) { id }
    }
    """
    gql(META_URL, q, {"input": {"id": object_id}}, token=token)


def create_object(token: str, name_singular: str, name_plural: str,
                  label_singular: str, label_plural: str,
                  icon: str, description: str) -> str:
    q = """
    mutation CreateOneObject($input: CreateOneObjectInput!) {
      createOneObject(input: $input) {
        id nameSingular
      }
    }
    """
    variables = {
        "input": {
            "object": {
                "nameSingular": name_singular,
                "namePlural": name_plural,
                "labelSingular": label_singular,
                "labelPlural": label_plural,
                "icon": icon,
                "description": description,
                "isLabelSyncedWithName": False,
            }
        }
    }
    data = gql(META_URL, q, variables, token=token)
    return data["createOneObject"]["id"]


FAILED_FIELDS: list[tuple[str, str, str]] = []  # (object_label, field_name, error)


def create_field(token: str, object_id: str, name: str, label: str, field_type: str,
                 options: list[dict] | None = None,
                 default_value=None,
                 object_label: str = "") -> str | None:
    """Create scalar field. field_type is one of: TEXT, NUMBER, BOOLEAN, DATE_TIME, SELECT, MULTI_SELECT.

    Логирует каждую попытку. При ошибке записывает в FAILED_FIELDS и возвращает None,
    скрипт продолжает работу.
    """
    print(f"    + field {name} ({field_type})", flush=True)
    q = """
    mutation CreateOneField($input: CreateOneFieldMetadataInput!) {
      createOneField(input: $input) {
        id name type
      }
    }
    """
    field: dict = {
        "name": name,
        "label": label,
        "type": field_type,
        "objectMetadataId": object_id,
        "isNullable": True,
    }
    if options:
        field["options"] = options
    if default_value is not None:
        field["defaultValue"] = default_value
    variables = {"input": {"field": field}}
    try:
        data = gql(META_URL, q, variables, token=token)
        return data["createOneField"]["id"]
    except SystemExit as e:
        err = str(e)[:300]
        FAILED_FIELDS.append((object_label, name, err))
        print(f"      ⚠️  FAILED: {err.splitlines()[0]}", flush=True)
        return None


def create_relation(token: str, source_object_id: str, target_object_id: str,
                    source_field_name: str, source_field_label: str,
                    target_field_name: str, target_field_label: str,
                    relation_type: str = "MANY_TO_ONE") -> None:
    """Create RELATION field on source pointing to target.

    relation_type: MANY_TO_ONE (default — каждый Source ссылается на одну Target;
                   на стороне Target автоматически создаётся ONE_TO_MANY).
    """
    q = """
    mutation CreateOneField($input: CreateOneFieldMetadataInput!) {
      createOneField(input: $input) {
        id name type
      }
    }
    """
    field = {
        "name": source_field_name,
        "label": source_field_label,
        "type": "RELATION",
        "objectMetadataId": source_object_id,
        "isNullable": True,
        "relationCreationPayload": {
            "targetObjectMetadataId": target_object_id,
            "type": relation_type,
            "targetFieldLabel": target_field_label,
            "targetFieldIcon": "IconList",
        },
    }
    variables = {"input": {"field": field}}
    gql(META_URL, q, variables, token=token)


# ----------------------------------------------------------------------------
# Data API operations
# ----------------------------------------------------------------------------

def create_record(token: str, object_singular: str, data: dict) -> dict:
    """Создаёт одну запись через mutation create{Singular}(data: {Singular}CreateInput).

    Twenty 2.x использует именно такую форму (без 'One'-префикса).
    """
    cap = object_singular[0].upper() + object_singular[1:]
    mutation_name = f"create{cap}"
    q = f"""
    mutation Create($data: {cap}CreateInput!) {{
      {mutation_name}(data: $data) {{ id name }}
    }}
    """
    res = gql(DATA_URL, q, {"data": data}, token=token)
    return res[mutation_name]


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

OUR_OBJECTS = ["direction", "topic", "channel", "idea", "draft", "publication"]


def main() -> None:
    print("=" * 60)
    print("Twenty content-system setup для 13-33")
    print("=" * 60)

    token = load_token()
    print(f"Token loaded ({len(token)} chars)")

    # 1. List existing custom objects
    print("\n[1/4] Проверяю, нет ли существующих объектов с нашими именами...")
    existing = list_custom_objects(token)
    ours_existing = [o for o in existing if o["nameSingular"] in OUR_OBJECTS]
    if ours_existing:
        print(f"  Найдено {len(ours_existing)} объектов:")
        for o in ours_existing:
            print(f"    - {o['nameSingular']} (id={o['id']})")
        print("\n  Они должны быть удалены вручную через UI ИЛИ скрипт удалит их сейчас.")
        ans = input("  Удалить найденные объекты? [yes/NO]: ").strip().lower()
        if ans == "yes":
            for o in ours_existing:
                log(f"deleting {o['nameSingular']}...")
                delete_object(token, o["id"])
            print("  Удалено.")
        else:
            sys.exit("Отмена. Удали в UI и запусти скрипт ещё раз.")

    # 2. Create objects (no relations yet — добавим релейшены отдельной фазой)
    print("\n[2/4] Создаю объекты + scalar поля...")

    # --- Direction
    log("создаю Direction")
    direction_id = create_object(token, "direction", "directions", "Direction", "Directions",
                                  "IconCompass", "Top-level направление контента 13-33")
    create_field(token, direction_id, "slug", "Slug", "TEXT", object_label="Direction")
    create_field(token, direction_id, "description", "Description", "TEXT", object_label="Direction")
    create_field(token, direction_id, "color", "Color", "TEXT", object_label="Direction")
    create_field(token, direction_id, "ornament", "Ornament", "TEXT", object_label="Direction")
    create_field(token, direction_id, "isActive", "Is Active", "BOOLEAN", object_label="Direction")

    # --- Channel
    log("создаю Channel")
    channel_id = create_object(token, "channel", "channels", "Channel", "Channels",
                                "IconBroadcast", "Канал публикации (TG, FB, VK, Дзен, сайт)")
    create_field(token, channel_id, "code", "Code", "TEXT", object_label="Channel")
    create_field(token, channel_id, "channelType", "Channel Type", "TEXT", object_label="Channel")
    create_field(token, channel_id, "handle", "Handle", "TEXT", object_label="Channel")
    create_field(token, channel_id, "charLimit", "Char Limit", "NUMBER", object_label="Channel")
    create_field(token, channel_id, "defaultTone", "Default Tone", "TEXT", object_label="Channel")
    create_field(token, channel_id, "enabled", "Enabled", "BOOLEAN", object_label="Channel")

    # --- Topic (с релейшеном к Direction)
    log("создаю Topic")
    topic_id = create_object(token, "topic", "topics", "Topic", "Topics",
                             "IconTag", "Тема внутри Direction")
    create_field(token, topic_id, "slug", "Slug", "TEXT", object_label="Topic")
    create_field(token, topic_id, "description", "Description", "TEXT", object_label="Topic")
    create_field(token, topic_id, "color", "Color", "TEXT", object_label="Topic")
    create_field(token, topic_id, "ornament", "Ornament", "TEXT", object_label="Topic")
    create_field(token, topic_id, "isActive", "Is Active", "BOOLEAN", object_label="Topic")

    # --- Idea (status → lifecycle, чтобы обойти reserved слово)
    log("создаю Idea")
    idea_id = create_object(token, "idea", "ideas", "Idea", "Ideas",
                            "IconBulb", "Сырая идея для контента")
    create_field(token, idea_id, "description", "Description", "TEXT", object_label="Idea")
    create_field(token, idea_id, "source", "Source", "TEXT", object_label="Idea")
    create_field(token, idea_id, "lifecycle", "Lifecycle", "TEXT", object_label="Idea")
    create_field(token, idea_id, "capturedAt", "Captured At", "DATE_TIME", object_label="Idea")
    create_field(token, idea_id, "processedAt", "Processed At", "DATE_TIME", object_label="Idea")
    create_field(token, idea_id, "referenceUrls", "Reference URLs", "TEXT", object_label="Idea")
    create_field(token, idea_id, "embeddingId", "Embedding ID", "TEXT", object_label="Idea")
    create_field(token, idea_id, "createdByExternalId", "Created By External ID", "TEXT", object_label="Idea")

    # --- Draft (status → lifecycle)
    log("создаю Draft")
    draft_id = create_object(token, "draft", "drafts", "Draft", "Drafts",
                             "IconFileText", "Готовый текст для одного канала")
    create_field(token, draft_id, "body", "Body", "TEXT", object_label="Draft")
    create_field(token, draft_id, "tone", "Tone", "TEXT", object_label="Draft")
    create_field(token, draft_id, "length", "Length", "TEXT", object_label="Draft")
    create_field(token, draft_id, "lifecycle", "Lifecycle", "TEXT", object_label="Draft")
    create_field(token, draft_id, "reviewNotes", "Review Notes", "TEXT", object_label="Draft")
    create_field(token, draft_id, "author", "Author", "TEXT", object_label="Draft")
    create_field(token, draft_id, "llmModel", "LLM Model", "TEXT", object_label="Draft")
    create_field(token, draft_id, "scheduledAt", "Scheduled At", "DATE_TIME", object_label="Draft")
    create_field(token, draft_id, "publishedAt", "Published At", "DATE_TIME", object_label="Draft")
    create_field(token, draft_id, "publicationUrl", "Publication URL", "TEXT", object_label="Draft")
    create_field(token, draft_id, "version", "Version", "NUMBER", object_label="Draft")

    # --- Publication (status → lifecycle)
    log("создаю Publication")
    publication_id = create_object(token, "publication", "publications", "Publication", "Publications",
                                    "IconCalendarTime", "Запланированная или состоявшаяся публикация")
    create_field(token, publication_id, "scheduledAt", "Scheduled At", "DATE_TIME", object_label="Publication")
    create_field(token, publication_id, "lifecycle", "Lifecycle", "TEXT", object_label="Publication")
    create_field(token, publication_id, "resultUrl", "Result URL", "TEXT", object_label="Publication")
    create_field(token, publication_id, "errorMessage", "Error Message", "TEXT", object_label="Publication")
    create_field(token, publication_id, "attemptCount", "Attempt Count", "NUMBER", object_label="Publication")
    create_field(token, publication_id, "engagementViews", "Engagement Views", "NUMBER", object_label="Publication")
    create_field(token, publication_id, "engagementLikes", "Engagement Likes", "NUMBER", object_label="Publication")
    create_field(token, publication_id, "engagementShares", "Engagement Shares", "NUMBER", object_label="Publication")
    create_field(token, publication_id, "engagementComments", "Engagement Comments", "NUMBER", object_label="Publication")
    create_field(token, publication_id, "lastMetricsAt", "Last Metrics At", "DATE_TIME", object_label="Publication")

    # 3. Создаём релейшены
    print("\n[3/4] Создаю релейшены...")
    log("Topic.direction → Direction")
    create_relation(token, topic_id, direction_id, "direction", "Direction", "topics", "Topics")

    log("Idea.topic → Topic")
    create_relation(token, idea_id, topic_id, "topic", "Topic", "ideas", "Ideas")

    log("Idea.direction → Direction")
    create_relation(token, idea_id, direction_id, "direction", "Direction", "ideas", "Ideas")

    log("Draft.idea → Idea")
    create_relation(token, draft_id, idea_id, "idea", "Idea", "drafts", "Drafts")

    log("Draft.topic → Topic")
    create_relation(token, draft_id, topic_id, "topic", "Topic", "drafts", "Drafts")

    log("Draft.channel → Channel")
    create_relation(token, draft_id, channel_id, "channel", "Channel", "drafts", "Drafts")

    log("Publication.draft → Draft")
    create_relation(token, publication_id, draft_id, "draft", "Draft", "publications", "Publications")

    log("Publication.channel → Channel")
    create_relation(token, publication_id, channel_id, "channel", "Channel", "publications", "Publications")

    # 4. Заливаем дефолтные записи
    print("\n[4/4] Заливаю дефолтные записи (3 Direction + 5 Channel)...")

    directions_data = [
        {"name": "Душа",             "slug": "soul",     "color": "coral", "ornament": "mandala_general"},
        {"name": "Материальный мир", "slug": "material", "color": "brick", "ornament": "morris"},
        {"name": "Дух",              "slug": "spirit",   "color": "blue",  "ornament": "mandala_tibetan"},
    ]
    for d in directions_data:
        log(f"Direction: {d['name']}")
        create_record(token, "direction", {**d, "isActive": True})

    channels_data = [
        {"name": "Telegram-канал",  "code": "tg",   "channelType": "telegram", "handle": "@prostranstvo1333",          "charLimit": 4096,   "defaultTone": "2", "enabled": True},
        {"name": "Facebook Page",   "code": "fb",   "channelType": "facebook", "handle": "id=61561590630465",          "charLimit": 63206,  "defaultTone": "2", "enabled": True},
        {"name": "VK группа",       "code": "vk",   "channelType": "vk",       "handle": "club229213865",              "charLimit": 16384,  "defaultTone": "2", "enabled": True},
        {"name": "Дзен",            "code": "dzen", "channelType": "dzen",     "handle": "id=69f4c15949f7d66770f252c0", "charLimit": 100000, "defaultTone": "1", "enabled": True},
        {"name": "Сайт 13-33.pro",  "code": "site", "channelType": "site",     "handle": "13-33.pro",                  "charLimit": 0,      "defaultTone": "1", "enabled": True},
    ]
    for c in channels_data:
        log(f"Channel: {c['name']}")
        create_record(token, "channel", c)

    print("\n" + "=" * 60)
    if FAILED_FIELDS:
        print(f"⚠️  ЗАВЕРШЕНО С ОШИБКАМИ ({len(FAILED_FIELDS)} полей не создалось):")
        for obj, field, err in FAILED_FIELDS:
            print(f"  - {obj}.{field}: {err.splitlines()[0]}")
        print()
        print("Скрипт создал, что смог. Несозданные поля можно добавить руками в UI,")
        print("или сообщи мне точную ошибку выше — поправлю скрипт.")
    else:
        print("ГОТОВО ✓ (без ошибок)")
    print("=" * 60)
    print(f"  direction id: {direction_id}")
    print(f"  channel   id: {channel_id}")
    print(f"  topic     id: {topic_id}")
    print(f"  idea      id: {idea_id}")
    print(f"  draft     id: {draft_id}")
    print(f"  publication id: {publication_id}")
    print()
    print("Проверь в UI Twenty (https://crm.13-33.pro), что появились объекты,")
    print("у Channel — 5 записей с заполненными полями, у Direction — 3.")


if __name__ == "__main__":
    main()
