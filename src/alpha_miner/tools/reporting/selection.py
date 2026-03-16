"""Deterministic factor scoring and selection for Feature 5 reporting."""

from __future__ import annotations


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def compute_report_composite_score(result_row: dict) -> float:
    sharpe = _clamp(float(result_row.get("sharpe", 0.0)) / 2.0)
    ir = _clamp(float(result_row.get("information_ratio", 0.0)) / 1.0)
    ic = _clamp(float(result_row.get("ic_mean", 0.0)) / 0.05)
    oos = _clamp(float(result_row.get("oos_score", 0.0)))
    decay = _clamp(float(result_row.get("decay_score", 0.0)))
    return (0.30 * sharpe) + (0.20 * ir) + (0.20 * ic) + (0.15 * oos) + (0.15 * decay)


def rank_results_with_composite(results: list[dict]) -> list[dict]:
    ranked: list[dict] = []
    for row in results:
        item = dict(row)
        item["composite_score"] = compute_report_composite_score(item)
        ranked.append(item)
    ranked.sort(key=lambda r: float(r.get("composite_score", 0.0)), reverse=True)
    return ranked


def select_report_factors(results: list[dict], policy: str, top_fallback_count: int = 3) -> list[dict]:
    ranked = rank_results_with_composite(results)
    promoted = [row for row in ranked if bool(row.get("promoted", False))]

    if policy == "promoted_only":
        return promoted

    if policy == "top3_always":
        return ranked[:top_fallback_count]

    # promoted_plus_top_fallback default
    if promoted:
        return promoted
    return ranked[:top_fallback_count]
