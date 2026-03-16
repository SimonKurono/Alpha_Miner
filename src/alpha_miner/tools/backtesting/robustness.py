"""Rolling out-of-sample robustness analysis for Feature 4."""

from __future__ import annotations

from datetime import date, datetime

from alpha_miner.tools.backtesting.portfolio import run_backtest


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def run_rolling_oos(scores: list[dict], prices: list[dict], train_days: int, test_days: int, cfg: dict) -> dict:
    unique_dates = sorted({_as_date(row.get("date")) for row in prices})
    if len(unique_dates) < (train_days + test_days + 2):
        return {
            "window_count": 0,
            "window_metrics": [],
            "aggregate": {"oos_score": 0.0, "oos_sharpe": 0.0, "oos_ir": 0.0, "oos_ic": 0.0},
        }

    windows: list[dict] = []
    step = max(1, test_days)

    for start in range(0, len(unique_dates), step):
        train_start = start
        train_end = train_start + train_days
        test_end = train_end + test_days
        if test_end > len(unique_dates):
            break

        test_dates = set(unique_dates[train_end:test_end])
        if not test_dates:
            continue

        scores_subset = [row for row in scores if _as_date(row.get("date")) in test_dates]
        prices_subset = [row for row in prices if _as_date(row.get("date")) in test_dates]

        result = run_backtest(scores_subset, prices_subset, benchmark=[], cfg=cfg)
        metrics = dict(result["metrics"])
        windows.append(
            {
                "window_index": len(windows),
                "train_start": unique_dates[train_start].isoformat(),
                "train_end": unique_dates[train_end - 1].isoformat(),
                "test_start": unique_dates[train_end].isoformat(),
                "test_end": unique_dates[test_end - 1].isoformat(),
                "metrics": metrics,
            }
        )

    if not windows:
        return {
            "window_count": 0,
            "window_metrics": [],
            "aggregate": {"oos_score": 0.0, "oos_sharpe": 0.0, "oos_ir": 0.0, "oos_ic": 0.0},
        }

    oos_sharpe = sum(w["metrics"].get("sharpe", 0.0) for w in windows) / len(windows)
    oos_ir = sum(w["metrics"].get("information_ratio", 0.0) for w in windows) / len(windows)
    oos_ic = sum(w["metrics"].get("ic_mean", 0.0) for w in windows) / len(windows)

    score = (
        _clamp01(oos_sharpe / 2.0)
        + _clamp01(oos_ir / 1.0)
        + _clamp01(oos_ic / 0.05)
    ) / 3.0

    return {
        "window_count": len(windows),
        "window_metrics": windows,
        "aggregate": {
            "oos_score": score,
            "oos_sharpe": oos_sharpe,
            "oos_ir": oos_ir,
            "oos_ic": oos_ic,
        },
    }
