from __future__ import annotations

from alpha_miner.tools.backtesting.dsl_executor import compute_factor_scores


def _sample_market_rows() -> list[dict]:
    rows: list[dict] = []
    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"]
    for i, day in enumerate(["2024-01-02", "2024-01-03"]):
        for j, sym in enumerate(symbols):
            rows.append(
                {
                    "symbol": sym,
                    "date": day,
                    "close": 100.0 + (j * 3.0) + i,
                    "volume": 1_000_000 + (j * 1000) + (i * 500),
                    "market_cap": 1_000_000_000 + (j * 10_000_000),
                    "returns_1d": 0.001 * (j - 2),
                    "returns_5d": 0.002 * (2 - j),
                }
            )
    return rows


def test_compute_factor_scores_cross_sectional_functions():
    rows = _sample_market_rows()
    expr = "Rank(returns_1d) + Normalize(volume)"

    scores = compute_factor_scores(rows, expr)

    assert len(scores) == 10
    assert scores[0]["date"] == "2024-01-02"
    assert all("score" in row for row in scores)
    assert all(isinstance(row["score"], float) for row in scores)


def test_compute_factor_scores_winsorized_sum_and_arithmetic():
    rows = _sample_market_rows()
    expr = "WinsorizedSum(Rank(close/market_cap), Normalize(returns_5d), Rank(volume)) / 2"

    scores = compute_factor_scores(rows, expr)

    assert len(scores) == 10
    by_symbol = {row["symbol"]: row["score"] for row in scores if row["date"] == "2024-01-02"}
    assert set(by_symbol) == {"AAPL", "MSFT", "NVDA", "AMZN", "GOOGL"}
