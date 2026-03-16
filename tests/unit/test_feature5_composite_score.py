from __future__ import annotations

from alpha_miner.tools.reporting.selection import compute_report_composite_score


def test_composite_score_monotonicity():
    weak = {
        "sharpe": 0.2,
        "information_ratio": 0.1,
        "ic_mean": 0.002,
        "oos_score": 0.2,
        "decay_score": 0.3,
    }
    strong = {
        "sharpe": 1.0,
        "information_ratio": 0.6,
        "ic_mean": 0.03,
        "oos_score": 0.7,
        "decay_score": 0.9,
    }

    weak_score = compute_report_composite_score(weak)
    strong_score = compute_report_composite_score(strong)

    assert 0.0 <= weak_score <= 1.0
    assert 0.0 <= strong_score <= 1.0
    assert strong_score > weak_score
