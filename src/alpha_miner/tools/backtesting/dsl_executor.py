"""DSL score execution with cross-sectional semantics for Feature 4."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Iterable

from alpha_miner.tools.factors.ast_nodes import BinaryOp, ExpressionRoot, FunctionCall, Identifier, NumberLiteral, UnaryOp
from alpha_miner.tools.factors.dsl_parser import parse_factor_expression


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _safe_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return 0.0


def _percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = pos - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _winsorize(values: dict[str, float], lower_q: float = 0.05, upper_q: float = 0.95) -> dict[str, float]:
    arr = sorted(values.values())
    if not arr:
        return {}
    lo = _percentile(arr, lower_q)
    hi = _percentile(arr, upper_q)
    return {k: min(hi, max(lo, v)) for k, v in values.items()}


def _rank(values: dict[str, float]) -> dict[str, float]:
    items = sorted(values.items(), key=lambda kv: kv[1])
    n = len(items)
    if n == 0:
        return {}
    if n == 1:
        key = items[0][0]
        return {key: 0.5}

    out: dict[str, float] = {}
    idx = 0
    while idx < n:
        j = idx
        while j + 1 < n and items[j + 1][1] == items[idx][1]:
            j += 1
        avg_rank = (idx + j) / 2.0
        pct = avg_rank / float(n - 1)
        for k in range(idx, j + 1):
            out[items[k][0]] = pct
        idx = j + 1
    return out


def _normalize(values: dict[str, float]) -> dict[str, float]:
    n = len(values)
    if n == 0:
        return {}
    mean = sum(values.values()) / n
    var = sum((v - mean) ** 2 for v in values.values()) / n
    std = var ** 0.5
    if std <= 1e-12:
        return {k: 0.0 for k in values}
    return {k: (v - mean) / std for k, v in values.items()}


def _apply_binary(op: str, left: dict[str, float], right: dict[str, float], symbols: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for sym in symbols:
        l = left.get(sym, 0.0)
        r = right.get(sym, 0.0)
        if op == "+":
            out[sym] = l + r
        elif op == "-":
            out[sym] = l - r
        elif op == "*":
            out[sym] = l * r
        elif op == "/":
            out[sym] = 0.0 if abs(r) <= 1e-12 else l / r
        else:
            out[sym] = 0.0
    return out


def _eval_node(node, frame: dict[str, dict]) -> dict[str, float]:
    symbols = sorted(frame.keys())

    if isinstance(node, ExpressionRoot):
        return _eval_node(node.expr, frame)

    if isinstance(node, Identifier):
        return {sym: _safe_float(frame[sym].get(node.name)) for sym in symbols}

    if isinstance(node, NumberLiteral):
        return {sym: node.value for sym in symbols}

    if isinstance(node, UnaryOp):
        operand = _eval_node(node.operand, frame)
        if node.op == "-":
            return {sym: -operand.get(sym, 0.0) for sym in symbols}
        return operand

    if isinstance(node, BinaryOp):
        left = _eval_node(node.left, frame)
        right = _eval_node(node.right, frame)
        return _apply_binary(node.op, left, right, symbols)

    if isinstance(node, FunctionCall):
        if node.name == "Rank":
            values = _eval_node(node.args[0], frame)
            return _rank(values)
        if node.name == "Normalize":
            values = _eval_node(node.args[0], frame)
            return _normalize(values)
        if node.name == "WinsorizedSum":
            acc = {sym: 0.0 for sym in symbols}
            for arg in node.args:
                vals = _winsorize(_eval_node(arg, frame))
                for sym in symbols:
                    acc[sym] += vals.get(sym, 0.0)
            return acc

    return {sym: 0.0 for sym in symbols}


def compute_factor_scores(market_rows: list[dict], expression: str) -> list[dict]:
    ast = parse_factor_expression(expression)

    by_date: dict[date, list[dict]] = defaultdict(list)
    for row in market_rows:
        by_date[_as_date(row.get("date"))].append(row)

    out: list[dict] = []
    for day in sorted(by_date):
        rows = by_date[day]
        frame = {str(r.get("symbol", "")).upper(): r for r in rows if r.get("symbol")}
        if not frame:
            continue
        scores = _eval_node(ast, frame)
        for symbol in sorted(scores):
            out.append(
                {
                    "date": day.isoformat(),
                    "symbol": symbol,
                    "score": float(scores[symbol]),
                }
            )

    out.sort(key=lambda r: (r["date"], r["symbol"]))
    return out


def filter_rows_by_date(rows: Iterable[dict], start_date: date | None, end_date: date | None) -> list[dict]:
    out: list[dict] = []
    for row in rows:
        day = _as_date(row.get("date"))
        if start_date and day < start_date:
            continue
        if end_date and day > end_date:
            continue
        out.append(row)
    return out
