from __future__ import annotations

from alpha_miner.tools.factors.scoring import compute_originality_score


def test_originality_zero_for_identical_expression():
    expr = "Rank(returns_1d)"
    score = compute_originality_score(expr, [expr])
    assert score == 0.0


def test_originality_higher_for_more_different_expression():
    near = compute_originality_score(
        "Rank(returns_1d)",
        ["Rank(returns_5d)"],
    )
    far = compute_originality_score(
        "WinsorizedSum(Rank(close/market_cap), Normalize(volume))",
        ["Rank(returns_5d)"],
    )
    assert far > near
