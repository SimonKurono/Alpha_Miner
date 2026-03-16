"""Performance decay analysis for Feature 4."""

from __future__ import annotations


def _avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def run_decay_analysis(returns: list[dict]) -> dict:
    if not returns:
        return {
            "slice_stats": {"early": 0.0, "mid": 0.0, "late": 0.0},
            "decay_slope": 0.0,
            "decay_score": 0.0,
        }

    net = [float(row.get("net_return", 0.0)) for row in returns]
    n = len(net)
    third = max(1, n // 3)

    early = net[:third]
    mid = net[third : min(2 * third, n)]
    late = net[min(2 * third, n) :]

    early_m = _avg(early)
    mid_m = _avg(mid)
    late_m = _avg(late)

    decay_slope = late_m - early_m

    if early_m > 1e-9:
        ratio = late_m / early_m
        decay_score = max(0.0, min(1.0, ratio))
    elif late_m >= early_m:
        decay_score = 0.5
    else:
        decay_score = 0.0

    return {
        "slice_stats": {
            "early": early_m,
            "mid": mid_m,
            "late": late_m,
        },
        "decay_slope": decay_slope,
        "decay_score": decay_score,
    }
