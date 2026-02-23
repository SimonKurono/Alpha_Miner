"""Hypothesis scoring utilities."""

from __future__ import annotations

from typing import Any

from alpha_miner.agents.hypothesis_generation.schemas import HypothesisCandidate


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def score_hypothesis(candidate: HypothesisCandidate | dict[str, Any], risk_profile: str) -> float:
    model = candidate if isinstance(candidate, HypothesisCandidate) else HypothesisCandidate.model_validate(candidate)

    base = 0.55 * float(model.confidence)
    role_diversity = min(1.0, len(set(model.originating_roles)) / 3.0)
    evidence_strength = min(1.0, max(0.0, len(model.evidence_summary.strip()) / 240.0))
    symbol_breadth = min(1.0, len(set(model.supporting_symbols)) / 10.0)

    score = base + 0.20 * role_diversity + 0.15 * evidence_strength + 0.10 * symbol_breadth

    if risk_profile == "risk_averse":
        if model.horizon_days == 5:
            score -= 0.10
        if model.direction == "long_short":
            score -= 0.05

    return _clamp01(score)
