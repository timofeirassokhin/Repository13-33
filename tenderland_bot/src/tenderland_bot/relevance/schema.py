"""Pydantic-схемы для Tier-2."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    model_match: int = 0
    brand_match: int = 0
    instrument_type: int = 0
    technique: int = 0
    component: int = 0
    name_multiplier: int = 1
    price_bonus: int = 0
    customer_bonus: int = 0


class Tier2Decision(BaseModel):
    """Результат Tier-2-классификации одного тендера."""

    tender_id: str
    topic: str
    relevance: Literal["pass", "review", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    matched_signals: list[str] = Field(default_factory=list)
    customer_class: Literal["whitelist", "blacklist", "gray", "unknown"] = "unknown"
    customer_type: Optional[str] = None
    detected_class: Optional[str] = None
    flags: list[str] = Field(default_factory=list)
    reasoning: str = ""
    # сервисные
    model: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None
