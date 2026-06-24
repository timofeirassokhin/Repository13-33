"""Парсер keyword config MD-файлов в структурированные topic'и.

Формат входа — `config/keywords_*.md` со стандартной структурой:

  ### 5.1. `01_LC_LCMS_GPC_Prep` — ВЭЖХ / УВЭЖХ / ЖХ-МС / ГПХ / Препаративная

  ```text
  жидкостн++хроматограф ВЭЖХ ... =HPLC ...
  ```

Парсер находит:
  * все заголовки 3-го уровня вида `### N.N. \`<topic_name>\` — <описание>`
  * следующий за ним fenced code block (```...```)
  * фиксированный EXCLUDE-блок (обычно один на файл, см. секцию 6/7)

Возвращает:

  Topic(
      name="01_LC_LCMS_GPC_Prep",
      include_text="жидкостн++хроматограф ВЭЖХ ...",
      exclude_text="реактив реагент ...",
      file_path=..., header_line=..., description="..."
  )
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# === регекспы ===

# Заголовок секции:
#   ### 5.1. `01_LC_LCMS_GPC_Prep` — описание
#   ### 6.3. `CER_03_Liquid_Handling_Robotics` — описание
#   ### 6.5. `MDX_05_Service` — сервис ...
# Скобки `*(опц.)*` и emoji-маркеры — допустимы и игнорируются.
_HEADER_RE = re.compile(
    # Topic name может начинаться с буквы (`LAB_01_Climate`, `MDX_01_Sequencers`)
    # или с цифры (`01_LC_LCMS_GPC_Prep`, `02_GC_GCMS`).
    r"^###\s+\d+\.\d+\.\s+`([A-Za-z0-9][A-Za-z0-9_]*)`\s*[—\-–:]?\s*(.*?)(?:\s*\*\([^)]+\)\*)?\s*$",
    re.MULTILINE,
)

# Любой fenced code block (text / typed / без типа)
_CODE_BLOCK_RE = re.compile(r"```[A-Za-z]*\n(.*?)```", re.DOTALL)

# Заголовок EXCLUDE-секции — допустимы оба варианта:
#   `## 6. Общая EXCLUDE-строка` (level 2, как в keywords_config.md)
#   `### 7.1. Базовый EXCLUDE` (level 3, как в трёх других файлах)
_EXCLUDE_HEADER_RE = re.compile(
    r"^##+\s+\d+(?:\.\d+)?\.\s+(?:Базов|Общая|Общий)\w*\s+EXCLUDE",
    re.MULTILINE | re.IGNORECASE,
)


@dataclass
class Topic:
    """Один поисковый topic из MD-файла."""

    name: str                       # "01_LC_LCMS_GPC_Prep"
    include_text: str               # одна строка с keywords для tender_keywords_include
    exclude_text: str = ""          # одна строка для tender_keywords_exclude
    description: str = ""           # текст после "—" в заголовке
    file_path: Path | None = None
    line_number: int = 0
    # Дополнительные метаданные
    is_optional: bool = False       # *(опц.)* в заголовке

    def __repr__(self) -> str:
        return (
            f"Topic(name={self.name!r}, "
            f"include={len(self.include_text)}ch, exclude={len(self.exclude_text)}ch)"
        )


@dataclass
class ParsedConfig:
    """Один MD-файл целиком, со всеми topic'ами и общими EXCLUDE."""

    file_path: Path
    topics: list[Topic] = field(default_factory=list)
    # Общий EXCLUDE применяется ко всем topic'ам в файле, если у topic нет своего.
    base_exclude: str = ""

    def by_name(self, topic_name: str) -> Topic | None:
        for t in self.topics:
            if t.name == topic_name:
                return t
        return None


def _normalize_keywords_line(text: str) -> str:
    """Свести многострочный fenced block в одну строку:
    - убираем переносы строк
    - схлопываем последовательные пробелы
    - чистим края
    """
    # Переводы строк → пробелы
    one_line = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    # Множественные пробелы → один
    one_line = re.sub(r"\s+", " ", one_line)
    return one_line.strip()


def _find_next_code_block(md: str, start_pos: int) -> tuple[str, int] | None:
    """Найти первый ```...``` после позиции `start_pos`.
    Возвращает (содержимое, позиция-конца) или None."""
    m = _CODE_BLOCK_RE.search(md, start_pos)
    if not m:
        return None
    return m.group(1), m.end()


def parse_keywords_md(path: Path) -> ParsedConfig:
    """Распарсить один keywords_config_*.md файл."""
    text = path.read_text(encoding="utf-8")
    config = ParsedConfig(file_path=path)

    # 1. Все секции с topic'ами
    for hm in _HEADER_RE.finditer(text):
        topic_name = hm.group(1)
        rest = hm.group(2).strip()
        is_optional = "опц" in rest.lower() or "опционал" in rest.lower()
        description = re.sub(r"\s*\*\([^)]+\)\*\s*", "", rest).strip()

        # Найти ближайший code block после заголовка
        block = _find_next_code_block(text, hm.end())
        if block is None:
            continue
        include_raw, _ = block
        include_text = _normalize_keywords_line(include_raw)
        if not include_text:
            continue

        topic = Topic(
            name=topic_name,
            include_text=include_text,
            description=description,
            file_path=path,
            line_number=text[: hm.start()].count("\n") + 1,
            is_optional=is_optional,
        )
        config.topics.append(topic)

    # 2. Базовый EXCLUDE — code block после "### N.N. Базовый/Общий EXCLUDE"
    exh = _EXCLUDE_HEADER_RE.search(text)
    if exh is not None:
        block = _find_next_code_block(text, exh.end())
        if block is not None:
            config.base_exclude = _normalize_keywords_line(block[0])

    # 3. Простановка EXCLUDE на topic'ы — все получают base_exclude как fallback
    for t in config.topics:
        if not t.exclude_text:
            t.exclude_text = config.base_exclude

    return config


def parse_keywords_dir(config_dir: Path) -> dict[str, Topic]:
    """Распарсить все keywords_config*.md в директории, вернуть mapping topic→Topic.

    Если topic с одинаковым именем встречается в нескольких файлах — last wins,
    но логически такого быть не должно (имена topic'ов уникальны).
    """
    result: dict[str, Topic] = {}
    for md_path in sorted(config_dir.glob("keywords_config*.md")):
        cfg = parse_keywords_md(md_path)
        for t in cfg.topics:
            result[t.name] = t
    return result


# ============================================================================
# Smoke test (запуск напрямую: python -m tenderland_bot.md_parser)
# ============================================================================

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")

    here = Path(__file__).resolve().parents[2] / "config"
    all_topics = parse_keywords_dir(here)
    print(f"Found {len(all_topics)} topics in {here}:")
    for name, t in all_topics.items():
        marker = "  (опц.)" if t.is_optional else ""
        print(
            f"  {name:40} include={len(t.include_text):>5}ch  "
            f"exclude={len(t.exclude_text):>5}ch{marker}  "
            f"({t.file_path.name}:{t.line_number})"
        )
