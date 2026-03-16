"""Stable interfaces for Feature 4 backtesting tools."""

from __future__ import annotations

from alpha_miner.tools.backtesting.decay import run_decay_analysis
from alpha_miner.tools.backtesting.dsl_executor import compute_factor_scores
from alpha_miner.tools.backtesting.metrics import apply_promotion_rules, compute_ic, compute_turnover
from alpha_miner.tools.backtesting.portfolio import run_backtest
from alpha_miner.tools.backtesting.robustness import run_rolling_oos

__all__ = [
    "compute_factor_scores",
    "run_backtest",
    "compute_ic",
    "compute_turnover",
    "run_rolling_oos",
    "run_decay_analysis",
    "apply_promotion_rules",
]
