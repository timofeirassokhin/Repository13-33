"""LLM-driven intent parser. Пользовательский текст → структурированный JSON.

Используем LiteLLM `creative` (alias на claude-sonnet-4.5). Schema:

  {
    "action": "search" | "stats" | "help" | "unclear",
    "brand": str | null,           # точное название из списка известных
    "category": str | null,        # точный enum из product_category_t
    "keywords": [str, ...],        # ключевые слова для substring-match
    "has_pdf": bool | null,
    "has_ru": bool | null,
    "limit": int,                  # default 10
    "send_pdfs": bool,             # надо ли сразу отдать PDF файлы
    "explanation_ru": str          # одно предложение что бот понял
  }
"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .settings import Settings


# Эти списки попадают в system prompt — чтобы LLM выбирал точные значения,
# а не выдумывал свои.
KNOWN_BRANDS = [
    "Agilent Technologies", "Shimadzu", "Thermo Fisher Scientific",
    "AB Sciex", "Waters", "Bruker", "PerkinElmer", "Analytik Jena",
    "Sartorius", "Memmert", "Heidolph", "Binder", "BANDELIN",
    "Metrohm", "Huber", "BRAND", "Retsch", "SOTAX", "CAMAG",
    "Sigma Laborzentrifugen", "Lauda", "KNF", "SHP Steriltechnik",
    "Schmidt+Haensch", "HTA", "Hawach", "Sciencix", "Macherey-Nagel",
    "DWK Life Sciences", "Vitlab", "LLG Labware", "DAIHAN",
    "Illumina", "MGI Tech", "Genemind", "Oxford Nanopore", "PacBio",
    "Element Biosciences", "IDT", "Twist Biosciences", "Roche KAPA",
    "AmoyDx", "Burning Rock", "Pillar Biosciences",
    "Сесана", "Геноскан", "Хеликон",  # RU brands
    "Gluvex",
]

KNOWN_CATEGORIES = [
    # Аналитика
    "hplc_system", "hplc_pump", "hplc_autosampler", "hplc_column_oven",
    "hplc_detector", "gc_system", "gc_module", "mass_spectrometer",
    "aas_system", "icp_oes", "icp_ms", "uv_vis_spectrometer",
    "ftir_spectrometer", "nir_spectrometer",
    # Расходка хроматографии
    "hplc_column", "gc_column", "vial", "syringe_filter", "spe_cartridge",
    # NGS
    "sequencer_platform", "sequencer_flowcell", "sequencer_reagent_kit",
    "ngs_library_prep_kit", "ngs_target_capture_panel", "ngs_amplicon_panel",
    "pcr_kit", "realtime_pcr_kit", "dna_extraction_kit", "rna_extraction_kit",
    # Общелаб
    "centrifuge", "shaker_vortex", "incubator", "drying_oven", "climate_chamber",
    "biological_safety_cabinet", "laminar_hood", "balance", "titrator",
    # Прочее
    "consumable", "spare_part", "accessory", "software", "service", "other",
]


SYSTEM_PROMPT = f"""Ты — парсер запросов для каталога лабораторного оборудования Gluvex.
Принимаешь произвольный русский (или английский) текст от пользователя,
возвращаешь СТРОГИЙ JSON без markdown-fence, без пояснений вне JSON.

Доступные бренды (выбирать exact name):
{', '.join(KNOWN_BRANDS)}

Доступные категории (enum product_category_t):
{', '.join(KNOWN_CATEGORIES)}

Схема ответа:
{{
  "action": "search" | "stats" | "help" | "unclear",
  "brand": <exact brand name | null>,
  "category": <exact category enum | null>,
  "keywords": [<строки для substring-match>],
  "has_pdf": <true | false | null>,
  "has_ru": <true | false | null>,
  "limit": <число, default 10>,
  "send_pdfs": <true если пользователь явно просит файлы | false>,
  "explanation_ru": "<одно русское предложение что ты понял>"
}}

Правила:
- "тройные квадруполы Шимадзу" → brand="Shimadzu", category="mass_spectrometer", keywords=["triple","quadrupole","qqq"]
- "ВЭЖХ Agilent с РУ" → brand="Agilent Technologies", category="hplc_system", has_ru=true
- "брошюры на Orbitrap" → keywords=["orbitrap"], send_pdfs=true, has_pdf=true
- "что у нас по Sciex есть" → action="stats" с brand="AB Sciex" (Sciex → AB Sciex!)
- "/start", "помощь", "что ты умеешь" → action="help"
- Если непонятно → action="unclear", explanation_ru объясняет почему

Keywords — это ВАЖНЫЕ english/русские термины для поиска. Не включай туда название
бренда (оно уже в brand) и общие слова (прибор, оборудование, и т.п.).

Возвращай ТОЛЬКО JSON, никакого markdown."""


class IntentParser:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "IntentParser":
        self._client = httpx.AsyncClient(
            timeout=60,
            headers={
                "Authorization": f"Bearer {self._settings.litellm_master_key}",
                "Content-Type": "application/json",
            },
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()

    async def parse(self, user_text: str) -> dict[str, Any]:
        assert self._client is not None
        url = f"{self._settings.litellm_base_url}/chat/completions"
        payload = {
            "model": self._settings.litellm_intent_model,
            "temperature": self._settings.litellm_intent_temp,
            "max_tokens": self._settings.litellm_intent_max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text},
            ],
        }
        r = await self._client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"].strip()
        # на случай если модель всё-таки обернула в ```json
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.MULTILINE)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            return {
                "action": "unclear",
                "brand": None,
                "category": None,
                "keywords": [],
                "has_pdf": None,
                "has_ru": None,
                "limit": 10,
                "send_pdfs": False,
                "explanation_ru": f"Не смог разобрать запрос (LLM вернул не-JSON: {e}).",
                "_raw": content[:500],
            }
