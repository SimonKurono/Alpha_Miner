"""Portfolio construction and backtest execution for Feature 4."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from alpha_miner.tools.backtesting.metrics import (
    compute_cagr,
    compute_max_drawdown,
    compute_turnover,
    information_ratio,
    sharpe_ratio,
    spearman_correlation,
)


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _select_rebalance_dates(dates: list[date], freq: str) -> list[date]:
    if not dates:
        return []

    out: list[date] = []
    seen = set()
    for day in sorted(dates):
        if freq == "monthly":
            key = (day.year, day.month)
        else:
            key = (day.isocalendar().year, day.isocalendar().week)
        if key in seen:
            continue
        seen.add(key)
        out.append(day)
    return out


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def run_backtest(scores: list[dict], prices: list[dict], benchmark: list[dict], cfg: dict) -> dict:
    rebalance_freq = str(cfg.get("rebalance_freq", "weekly"))
    benchmark_symbol = str(cfg.get("benchmark", "SPY")).upper()
    tc_bps = float(cfg.get("transaction_cost_bps", 10.0))

    close_by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for row in prices:
        day = _as_date(row.get("date"))
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        close_by_date[day][symbol] = float(row.get("close", 0.0) or 0.0)

    benchmark_close_by_date: dict[date, float] = {}
    for row in benchmark:
        day = _as_date(row.get("date"))
        if str(row.get("symbol", "")).upper() != benchmark_symbol:
            continue
        benchmark_close_by_date[day] = float(row.get("close", 0.0) or 0.0)

    score_by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for row in scores:
        day = _as_date(row.get("date"))
        symbol = str(row.get("symbol", "")).upper()
        if not symbol:
            continue
        score_by_date[day][symbol] = float(row.get("score", 0.0) or 0.0)

    common_dates = sorted(set(close_by_date.keys()) & set(score_by_date.keys()))
    rebalance_dates = _select_rebalance_dates(common_dates, rebalance_freq)

    period_rows: list[dict] = []
    weight_rows: list[dict] = []

    prev_weights: dict[str, float] = {}

    for idx in range(len(rebalance_dates) - 1):
        d0 = rebalance_dates[idx]
        d1 = rebalance_dates[idx + 1]

        s_map = score_by_date[d0]
        c0 = close_by_date[d0]
        c1 = close_by_date[d1]

        symbols = sorted(set(s_map) & set(c0) & set(c1))
        if len(symbols) < 4:
            continue

        ranked = sorted(symbols, key=lambda s: s_map[s])
        q = max(1, len(ranked) // 5)
        short_syms = ranked[:q]
        long_syms = ranked[-q:]

        returns = {s: (c1[s] / c0[s] - 1.0) if abs(c0[s]) > 1e-12 else 0.0 for s in symbols}

        gross = _avg([returns[s] for s in long_syms]) - _avg([returns[s] for s in short_syms])

        curr_weights = {s: 1.0 / q for s in long_syms}
        curr_weights.update({s: curr_weights.get(s, 0.0) - (1.0 / q) for s in short_syms})

        all_syms = set(prev_weights) | set(curr_weights)
        turnover = 0.5 * sum(abs(curr_weights.get(s, 0.0) - prev_weights.get(s, 0.0)) for s in all_syms)
        cost = (tc_bps / 10000.0) * turnover
        net = gross - cost

        b0 = benchmark_close_by_date.get(d0, c0.get(benchmark_symbol, 0.0))
        b1 = benchmark_close_by_date.get(d1, c1.get(benchmark_symbol, 0.0))
        if abs(b0) > 1e-12:
            benchmark_ret = b1 / b0 - 1.0
        else:
            benchmark_ret = 0.0

        ic = spearman_correlation(
            [s_map[s] for s in symbols],
            [returns[s] for s in symbols],
        )

        period_rows.append(
            {
                "date": d1.isoformat(),
                "gross_return": gross,
                "net_return": net,
                "benchmark_return": benchmark_ret,
                "active_return": net - benchmark_ret,
                "turnover": turnover,
                "ic": ic,
            }
        )
        weight_rows.append({"date": d0.isoformat(), "weights": curr_weights})
        prev_weights = curr_weights

    net_returns = [row["net_return"] for row in period_rows]
    gross_returns = [row["gross_return"] for row in period_rows]
    active_returns = [row["active_return"] for row in period_rows]
    ic_values = [row["ic"] for row in period_rows]

    turnover_stats = compute_turnover(weight_rows)

    metrics = {
        "period_count": len(period_rows),
        "sharpe": sharpe_ratio(net_returns, rebalance_freq),
        "information_ratio": information_ratio(active_returns, rebalance_freq),
        "ic_mean": _avg(ic_values),
        "turnover_mean": turnover_stats["turnover_mean"],
        "turnover_monthly_max": turnover_stats["turnover_monthly_max"],
        "net_return_cagr": compute_cagr(net_returns, rebalance_freq),
        "max_drawdown": compute_max_drawdown(net_returns),
        "gross_return_mean": _avg(gross_returns),
        "net_return_mean": _avg(net_returns),
    }

    return {
        "metrics": metrics,
        "timeseries": period_rows,
        "weights": weight_rows,
        "turnover": turnover_stats,
    }
