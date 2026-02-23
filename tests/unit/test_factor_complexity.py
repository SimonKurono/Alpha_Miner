from __future__ import annotations

from alpha_miner.tools.factors.dsl_parser import parse_factor_expression
from alpha_miner.tools.factors.scoring import compute_complexity_score


def test_complexity_score_is_deterministic():
    ast = parse_factor_expression("Rank(returns_1d) + Normalize(volume)")
    s1 = compute_complexity_score(ast)
    s2 = compute_complexity_score(ast)
    assert s1 == s2
    assert s1 > 0


def test_complex_expression_scores_higher_than_simple_expression():
    simple = parse_factor_expression("Rank(returns_1d)")
    complex_expr = parse_factor_expression(
        "WinsorizedSum(Rank(close/market_cap), Normalize(returns_5d)) + (Rank(volume) * 0.5)"
    )
    assert compute_complexity_score(complex_expr) > compute_complexity_score(simple)
