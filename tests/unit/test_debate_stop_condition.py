from __future__ import annotations

from alpha_miner.agents.hypothesis_generation.consensus_synthesis_agent import (
    compute_consensus_score,
    compute_disagreements,
)
from alpha_miner.agents.hypothesis_generation.schemas import HypothesisCandidate


def _candidate(hid: str, role: str, horizon: int = 21, direction: str = "long_only") -> HypothesisCandidate:
    return HypothesisCandidate(
        hypothesis_id=hid,
        thesis=f"Thesis {hid}",
        horizon_days=horizon,
        direction=direction,
        evidence_summary="evidence",
        supporting_symbols=["AAPL", "MSFT"],
        originating_roles=[role],
        confidence=0.6,
        score_total=0.0,
    )


def test_consensus_score_high_when_roles_agree():
    candidates = [
        _candidate("h1", "fundamental", 21, "long_only"),
        _candidate("h2", "sentiment", 21, "long_only"),
        _candidate("h3", "valuation", 21, "long_only"),
    ]
    disagreements = compute_disagreements(candidates)
    score = compute_consensus_score(candidates, disagreements)
    assert disagreements == []
    assert score >= 0.75


def test_consensus_score_penalized_by_disagreements():
    candidates = [
        _candidate("h1", "fundamental", 5, "long_short"),
        _candidate("h2", "sentiment", 21, "long_only"),
    ]
    disagreements = compute_disagreements(candidates)
    score = compute_consensus_score(candidates, disagreements)
    assert len(disagreements) >= 1
    assert score < 0.75
