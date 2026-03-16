from __future__ import annotations

from alpha_miner.tools.backtesting.metrics import apply_promotion_rules


def test_moderate_profile_promotes_when_all_bars_met():
    metrics = {
        "sharpe": 0.95,
        "information_ratio": 0.45,
        "ic_mean": 0.02,
        "turnover_monthly_max": 0.50,
    }

    promoted, reasons = apply_promotion_rules(metrics, "moderate")

    assert promoted is True
    assert reasons == []


def test_moderate_profile_rejects_when_multiple_bars_fail():
    metrics = {
        "sharpe": 0.40,
        "information_ratio": 0.10,
        "ic_mean": 0.0,
        "turnover_monthly_max": 1.20,
    }

    promoted, reasons = apply_promotion_rules(metrics, "moderate")

    assert promoted is False
    assert len(reasons) >= 3
