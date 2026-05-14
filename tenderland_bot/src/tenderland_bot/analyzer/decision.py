"""Decision: применить бизнес-правила к результатам matcher → pass / review / fail.

Правила (из `docs/data-layers-architecture.md` раздел 4.4):

  pass    — score ≥ 80 у топ-кандидата + нет критических fail'ов (required spec не прошёл)
  review  — 60 ≤ score < 80, или есть unmapped/missing > 30% всех специй
  fail    — нет кандидата со score ≥ 60, или у всех кандидатов есть critical fails

Дополнительный сигнал — `tender_status=1` (активный) уже отфильтрован в SEARCHER.
Если тендер слишком "сырой" (мало specs, низкая confidence) — review с пояснением.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from .matcher import MatchCandidate


class Decision(str, enum.Enum):
    PASS = "pass"
    REVIEW = "review"
    FAIL = "fail"


@dataclass
class DecisionResult:
    decision: Decision
    reason: str
    best_match_id: str | None = None
    best_score: float = 0.0
    flags: list[str] = None     # warnings: ["low_spec_coverage", "all_critical_fails", ...]

    def __post_init__(self):
        if self.flags is None:
            self.flags = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reason": self.reason,
            "best_match_id": self.best_match_id,
            "best_score": self.best_score,
            "flags": self.flags,
        }


# Параметры решающих правил — можно конфигурировать через config/decision_rules.toml
PASS_MIN_SCORE = 80.0
REVIEW_MIN_SCORE = 60.0
MAX_UNMAPPED_RATIO = 0.30      # >30% unmapped specs → review даже при высоком score
MIN_TOTAL_SPECS = 3            # < 3 specs всего → review (мало данных)


def decide(candidates: list[MatchCandidate], total_extracted_specs: int = 0) -> DecisionResult:
    """Применить правила к ранжированному списку кандидатов.

    :param candidates: уже sorted desc по score
    :param total_extracted_specs: сколько specs изначально вытащили из ТЗ
    """
    flags: list[str] = []

    if not candidates:
        return DecisionResult(
            decision=Decision.FAIL,
            reason="no candidate products in catalog for this tender",
            flags=["no_candidates"],
        )

    best = candidates[0]
    flags = []

    # Низкое покрытие specs — мало данных в принципе
    if total_extracted_specs < MIN_TOTAL_SPECS:
        flags.append("low_spec_coverage")

    # Много unmapped в топ-кандидате — наша таксономия не покрывает
    if best.spec_matches:
        unmapped_ratio = best.unmapped_count / len(best.spec_matches)
        if unmapped_ratio > MAX_UNMAPPED_RATIO:
            flags.append(f"high_unmapped_ratio={unmapped_ratio:.0%}")

    # Критические fail-ы — required spec не прошёл
    critical_fails = sum(
        1 for sm in best.spec_matches
        if sm.status == "fail" and sm.required
    )
    if critical_fails > 0:
        flags.append(f"critical_fails={critical_fails}")

    # === Главное решающее правило ===

    if best.score >= PASS_MIN_SCORE and critical_fails == 0 and "low_spec_coverage" not in flags:
        return DecisionResult(
            decision=Decision.PASS,
            reason=f"{best.brand} {best.model} score {best.score:.0f}/100, {best.reasoning}",
            best_match_id=best.product_id,
            best_score=best.score,
            flags=flags,
        )

    if best.score >= REVIEW_MIN_SCORE or "low_spec_coverage" in flags:
        return DecisionResult(
            decision=Decision.REVIEW,
            reason=(
                f"{best.brand} {best.model} score {best.score:.0f}/100, "
                f"{best.reasoning}. Flags: {', '.join(flags) or 'none'}"
            ),
            best_match_id=best.product_id,
            best_score=best.score,
            flags=flags,
        )

    return DecisionResult(
        decision=Decision.FAIL,
        reason=(
            f"best candidate {best.brand} {best.model} score {best.score:.0f}/100 "
            f"too low. {best.reasoning}"
        ),
        best_match_id=best.product_id,
        best_score=best.score,
        flags=flags,
    )
