"""Complexity, originality, and alignment scoring for Feature 3 factors."""

from __future__ import annotations

import re

from alpha_miner.tools.factors.ast_nodes import AstNode, ast_depth, ast_serialize, iter_ast_nodes
from alpha_miner.tools.factors.dsl_parser import parse_factor_expression


def compute_complexity_score(ast: AstNode) -> int:
    n_nodes = 0
    n_function_calls = 0
    n_binary_ops = 0

    for node in iter_ast_nodes(ast):
        n_nodes += 1
        if node.node_type == "FunctionCall":
            n_function_calls += 1
        if node.node_type == "BinaryOp":
            n_binary_ops += 1

    depth = ast_depth(ast)
    return int(n_nodes + (2 * n_function_calls) + n_binary_ops + max(0, depth - 3))


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _serialize_expr(expr: str) -> str:
    ast = parse_factor_expression(expr)
    return ast_serialize(ast)


def compute_originality_score(expr: str, library_exprs: list[str]) -> float:
    if not library_exprs:
        return 1.0

    target = _serialize_expr(expr)
    nearest_distance = None
    nearest_len = 1

    for baseline in library_exprs:
        try:
            baseline_ser = _serialize_expr(baseline)
        except Exception:  # noqa: BLE001
            baseline_ser = baseline

        distance = _levenshtein_distance(target, baseline_ser)
        max_len = max(len(target), len(baseline_ser), 1)
        if nearest_distance is None or distance < nearest_distance:
            nearest_distance = distance
            nearest_len = max_len

    if nearest_distance is None:
        return 1.0

    return max(0.0, min(1.0, float(nearest_distance) / float(nearest_len)))


def score_hypothesis_alignment(hypothesis: dict, expr: str) -> float:
    text = " ".join(
        [
            str(hypothesis.get("thesis", "")),
            str(hypothesis.get("evidence_summary", "")),
            str(hypothesis.get("direction", "")),
        ]
    ).lower()
    text_tokens = {tok for tok in re.findall(r"[a-z_]+", text) if len(tok) >= 3}

    expr_tokens = {tok.lower() for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)}
    if not expr_tokens:
        return 0.0

    overlap = len(text_tokens & expr_tokens) / len(expr_tokens)

    alias_map = {
        "returns_1d": {"momentum", "short", "weekly", "week", "return"},
        "returns_5d": {"momentum", "weekly", "return", "drift"},
        "market_cap": {"large", "cap", "valuation", "size"},
        "volume": {"liquidity", "flow", "volume"},
        "close": {"price", "close"},
    }
    alias_hits = 0
    for field, aliases in alias_map.items():
        if field in expr_tokens and (text_tokens & aliases):
            alias_hits += 1

    alias_bonus = min(0.4, alias_hits * 0.1)
    score = min(1.0, overlap * 0.6 + alias_bonus)
    return max(0.0, score)
