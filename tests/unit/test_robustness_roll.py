from __future__ import annotations

from datetime import date, timedelta

from alpha_miner.tools.backtesting.robustness import run_rolling_oos


def _build_rows(days: int = 220) -> tuple[list[dict], list[dict]]:
    start = date(2024, 1, 1)
    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"]

    prices: list[dict] = []
    scores: list[dict] = []

    for d in range(days):
        day = (start + timedelta(days=d)).isoformat()
        for i, sym in enumerate(symbols):
            close = 100.0 + (0.2 * d) + (i * 0.3)
            prices.append({"date": day, "symbol": sym, "close": close})
            scores.append({"date": day, "symbol": sym, "score": float(i)})

    return scores, prices


def test_run_rolling_oos_returns_windows_and_aggregate():
    scores, prices = _build_rows(days=240)
    out = run_rolling_oos(
        scores=scores,
        prices=prices,
        train_days=120,
        test_days=30,
        cfg={"rebalance_freq": "weekly", "transaction_cost_bps": 10.0, "benchmark": "SPY"},
    )

    assert out["window_count"] > 0
    assert "aggregate" in out
    assert 0.0 <= out["aggregate"]["oos_score"] <= 1.0
