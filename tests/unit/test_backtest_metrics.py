from __future__ import annotations

from alpha_miner.tools.backtesting.metrics import compute_ic, compute_turnover, information_ratio, sharpe_ratio


def test_sharpe_and_information_ratio_basic_positive():
    returns = [0.01, 0.015, -0.005, 0.012, 0.008]
    active = [0.004, 0.005, -0.002, 0.003, 0.002]

    sharpe = sharpe_ratio(returns, "weekly")
    ir = information_ratio(active, "weekly")

    assert sharpe > 0.0
    assert ir > 0.0


def test_compute_ic_returns_high_for_aligned_ranks():
    scores = [
        {"date": "2024-01-02", "symbol": "AAPL", "score": 0.9},
        {"date": "2024-01-02", "symbol": "MSFT", "score": 0.5},
        {"date": "2024-01-02", "symbol": "NVDA", "score": 0.1},
    ]
    forward = [
        {"date": "2024-01-02", "symbol": "AAPL", "forward_return": 0.03},
        {"date": "2024-01-02", "symbol": "MSFT", "forward_return": 0.01},
        {"date": "2024-01-02", "symbol": "NVDA", "forward_return": -0.02},
    ]

    ic = compute_ic(scores, forward)
    assert ic > 0.9


def test_compute_turnover_series_and_monthly_max():
    weights = [
        {"date": "2024-01-05", "weights": {"AAPL": 0.5, "MSFT": -0.5}},
        {"date": "2024-01-12", "weights": {"AAPL": 0.4, "MSFT": -0.4, "NVDA": 0.0}},
        {"date": "2024-02-02", "weights": {"AAPL": 0.0, "MSFT": -0.5, "NVDA": 0.5}},
    ]

    out = compute_turnover(weights)

    assert out["turnover_mean"] >= 0.0
    assert out["turnover_monthly_max"] >= 0.0
    assert len(out["series"]) == 3
