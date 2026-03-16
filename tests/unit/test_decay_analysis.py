from __future__ import annotations

from alpha_miner.tools.backtesting.decay import run_decay_analysis


def test_decay_analysis_detects_degradation():
    rows = []
    for i in range(30):
        rows.append({"date": f"2024-01-{i+1:02d}", "net_return": 0.02})
    for i in range(30):
        rows.append({"date": f"2024-02-{i+1:02d}", "net_return": 0.01})
    for i in range(30):
        rows.append({"date": f"2024-03-{i+1:02d}", "net_return": -0.005})

    out = run_decay_analysis(rows)

    assert out["slice_stats"]["early"] > out["slice_stats"]["late"]
    assert out["decay_score"] <= 1.0
