from __future__ import annotations

from alpha_miner.tools.reporting.selection import select_report_factors


def _rows() -> list[dict]:
    return [
        {
            "factor_id": "a",
            "expression": "Rank(returns_1d)",
            "promoted": True,
            "sharpe": 1.0,
            "information_ratio": 0.5,
            "ic_mean": 0.02,
            "oos_score": 0.7,
            "decay_score": 0.9,
        },
        {
            "factor_id": "b",
            "expression": "Normalize(volume)",
            "promoted": False,
            "sharpe": 0.9,
            "information_ratio": 0.4,
            "ic_mean": 0.015,
            "oos_score": 0.6,
            "decay_score": 0.8,
        },
        {
            "factor_id": "c",
            "expression": "Rank(close)",
            "promoted": False,
            "sharpe": 0.4,
            "information_ratio": 0.2,
            "ic_mean": 0.01,
            "oos_score": 0.5,
            "decay_score": 0.6,
        },
    ]


def test_selection_promoted_only():
    out = select_report_factors(_rows(), policy="promoted_only", top_fallback_count=3)
    assert [r["factor_id"] for r in out] == ["a"]


def test_selection_promoted_plus_fallback_when_none_promoted():
    rows = _rows()
    for row in rows:
        row["promoted"] = False
    out = select_report_factors(rows, policy="promoted_plus_top_fallback", top_fallback_count=2)
    assert len(out) == 2
    assert out[0]["factor_id"] in {"a", "b"}


def test_selection_top3_always():
    out = select_report_factors(_rows(), policy="top3_always", top_fallback_count=2)
    assert len(out) == 2
