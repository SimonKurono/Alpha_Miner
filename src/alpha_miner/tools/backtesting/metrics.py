"""Core metric computations for Feature 4 backtesting."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
import math


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(max(0.0, var))


def annualization_factor(freq: str) -> float:
    if freq == "monthly":
        return 12.0
    if freq == "weekly":
        return 52.0
    return 252.0


def sharpe_ratio(returns: list[float], freq: str) -> float:
    if not returns:
        return 0.0
    stdev = _std(returns)
    if stdev <= 1e-12:
        return 0.0
    return (_mean(returns) / stdev) * math.sqrt(annualization_factor(freq))


def information_ratio(active_returns: list[float], freq: str) -> float:
    if not active_returns:
        return 0.0
    stdev = _std(active_returns)
    if stdev <= 1e-12:
        return 0.0
    return (_mean(active_returns) / stdev) * math.sqrt(annualization_factor(freq))


def _rank(values: list[float]) -> list[float]:
    indexed = list(enumerate(values))
    indexed.sort(key=lambda x: x[1])
    out = [0.0] * len(values)

    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0
        for k in range(i, j + 1):
            out[indexed[k][0]] = avg_rank
        i = j + 1
    return out


def _pearson(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    am = _mean(a)
    bm = _mean(b)
    num = sum((x - am) * (y - bm) for x, y in zip(a, b))
    dena = math.sqrt(sum((x - am) ** 2 for x in a))
    denb = math.sqrt(sum((y - bm) ** 2 for y in b))
    if dena <= 1e-12 or denb <= 1e-12:
        return 0.0
    return num / (dena * denb)


def spearman_correlation(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ar = _rank(a)
    br = _rank(b)
    return _pearson(ar, br)


def compute_ic(scores: list[dict], forward_returns: list[dict]) -> float:
    by_date_score: dict[date, dict[str, float]] = defaultdict(dict)
    by_date_fwd: dict[date, dict[str, float]] = defaultdict(dict)

    for row in scores:
        by_date_score[_as_date(row.get("date"))][str(row.get("symbol", "")).upper()] = float(row.get("score", 0.0))

    for row in forward_returns:
        by_date_fwd[_as_date(row.get("date"))][str(row.get("symbol", "")).upper()] = float(
            row.get("forward_return", 0.0)
        )

    ics: list[float] = []
    for day in sorted(set(by_date_score) & set(by_date_fwd)):
        s_map = by_date_score[day]
        r_map = by_date_fwd[day]
        symbols = sorted(set(s_map) & set(r_map))
        if len(symbols) < 2:
            continue
        s_vals = [s_map[s] for s in symbols]
        r_vals = [r_map[s] for s in symbols]
        ics.append(spearman_correlation(s_vals, r_vals))

    return _mean(ics)


def compute_turnover(weights: list[dict]) -> dict:
    if not weights:
        return {"turnover_mean": 0.0, "turnover_monthly_max": 0.0, "series": []}

    series: list[dict] = []
    month_buckets: dict[str, list[float]] = defaultdict(list)

    prev: dict[str, float] = {}
    for row in weights:
        day = _as_date(row["date"])
        curr = dict(row.get("weights", {}))
        all_symbols = set(prev) | set(curr)
        one_way = 0.5 * sum(abs(curr.get(s, 0.0) - prev.get(s, 0.0)) for s in all_symbols)
        series.append({"date": day.isoformat(), "turnover": one_way})
        month_buckets[day.strftime("%Y-%m")].append(one_way)
        prev = curr

    mean_turnover = _mean([row["turnover"] for row in series])
    monthly_max = max((_mean(vals) for vals in month_buckets.values()), default=0.0)

    return {
        "turnover_mean": mean_turnover,
        "turnover_monthly_max": monthly_max,
        "series": series,
    }


def compute_cagr(returns: list[float], freq: str) -> float:
    if not returns:
        return 0.0
    equity = 1.0
    for r in returns:
        equity *= (1.0 + r)
    periods = len(returns)
    if periods <= 0 or equity <= 0:
        return 0.0
    years = periods / annualization_factor(freq)
    if years <= 0:
        return 0.0
    return equity ** (1.0 / years) - 1.0


def compute_max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        equity *= (1.0 + r)
        peak = max(peak, equity)
        dd = (equity / peak) - 1.0
        max_dd = min(max_dd, dd)
    return abs(max_dd)


def apply_promotion_rules(metrics: dict, profile: str) -> tuple[bool, list[str]]:
    bars = {
        "moderate": {"sharpe": 0.8, "ir": 0.3, "ic": 0.01, "turnover_monthly_max": 0.80},
        "strict": {"sharpe": 1.0, "ir": 0.5, "ic": 0.02, "turnover_monthly_max": 0.60},
        "lenient": {"sharpe": 0.5, "ir": 0.2, "ic": 0.005, "turnover_monthly_max": 1.0},
    }
    chosen = bars.get(profile, bars["moderate"])

    reasons: list[str] = []
    if float(metrics.get("sharpe", 0.0)) < chosen["sharpe"]:
        reasons.append(f"sharpe_below_bar: {metrics.get('sharpe', 0.0):.3f} < {chosen['sharpe']:.3f}")
    if float(metrics.get("information_ratio", 0.0)) < chosen["ir"]:
        reasons.append(
            f"ir_below_bar: {metrics.get('information_ratio', 0.0):.3f} < {chosen['ir']:.3f}"
        )
    if float(metrics.get("ic_mean", 0.0)) < chosen["ic"]:
        reasons.append(f"ic_below_bar: {metrics.get('ic_mean', 0.0):.3f} < {chosen['ic']:.3f}")
    if float(metrics.get("turnover_monthly_max", 0.0)) > chosen["turnover_monthly_max"]:
        reasons.append(
            "turnover_above_bar: "
            f"{metrics.get('turnover_monthly_max', 0.0):.3f} > {chosen['turnover_monthly_max']:.3f}"
        )

    return len(reasons) == 0, reasons
