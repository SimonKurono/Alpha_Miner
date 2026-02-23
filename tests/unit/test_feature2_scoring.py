from __future__ import annotations

from alpha_miner.agents.hypothesis_generation.schemas import HypothesisCandidate
from alpha_miner.tools.hypothesis.scoring import score_hypothesis


def _candidate() -> HypothesisCandidate:
    return HypothesisCandidate(
        hypothesis_id="h1",
        thesis="Test thesis",
        horizon_days=5,
        direction="long_short",
        evidence_summary="Evidence text " * 10,
        supporting_symbols=["AAPL", "MSFT", "NVDA", "AMZN"],
        originating_roles=["fundamental", "sentiment"],
        confidence=0.7,
        score_total=0.0,
    )


def test_score_hypothesis_in_range():
    value = score_hypothesis(_candidate(), risk_profile="risk_neutral")
    assert 0.0 <= value <= 1.0


def test_risk_averse_penalizes_short_horizon_and_long_short():
    neutral = score_hypothesis(_candidate(), risk_profile="risk_neutral")
    cautious = score_hypothesis(_candidate(), risk_profile="risk_averse")
    assert cautious < neutral
