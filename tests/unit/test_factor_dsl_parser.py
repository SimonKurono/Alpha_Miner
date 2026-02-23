from __future__ import annotations

from alpha_miner.tools.factors.ast_nodes import ExpressionRoot, ast_serialize
from alpha_miner.tools.factors.dsl_parser import parse_factor_expression


def test_parse_valid_expression_builds_root_ast():
    ast = parse_factor_expression("Rank(returns_1d) + Normalize(volume)")
    assert isinstance(ast, ExpressionRoot)
    payload = ast_serialize(ast)
    assert "F(Rank" in payload
    assert "F(Normalize" in payload


def test_parse_nested_expression_with_winsorizedsum():
    ast = parse_factor_expression("WinsorizedSum(Rank(close/market_cap), Normalize(returns_5d))")
    payload = ast_serialize(ast)
    assert "F(WinsorizedSum" in payload
    assert "B(/" in payload
