from __future__ import annotations

from alpha_miner.tools.factors.dsl_parser import parse_factor_expression
from alpha_miner.tools.factors.validators import validate_factor_ast


def test_validate_accepts_supported_fields_functions():
    ast = parse_factor_expression("WinsorizedSum(Rank(returns_1d), Normalize(volume))")
    report = validate_factor_ast(ast)
    assert report.passed is True
    assert report.errors == []


def test_validate_rejects_unsupported_function():
    ast = parse_factor_expression("Mean(returns_1d)")
    report = validate_factor_ast(ast)
    assert report.passed is False
    assert any("Unsupported function" in err for err in report.errors)


def test_validate_rejects_unsupported_field():
    ast = parse_factor_expression("Rank(revenue_growth)")
    report = validate_factor_ast(ast)
    assert report.passed is False
    assert any("Unsupported data field" in err for err in report.errors)
