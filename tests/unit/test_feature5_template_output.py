from __future__ import annotations

from alpha_miner.tools.reporting.templating import build_research_note_markdown


def test_template_renders_required_sections_in_order():
    payload = {
        "run_id": "f5_test",
        "title": "Alpha Miner Research Note",
        "as_of_date": "2026-02-24",
        "executive_summary": "summary",
        "methodology": "method",
        "selected_factors": [
            {
                "factor_id": "f1",
                "expression": "Rank(returns_1d)",
                "promoted": True,
                "sharpe": 1.0,
                "information_ratio": 0.5,
                "ic_mean": 0.02,
                "turnover_monthly_max": 0.4,
                "oos_score": 0.7,
                "decay_score": 0.8,
                "composite_score": 0.75,
                "risk_tags": [],
            }
        ],
        "key_risks": ["risk1"],
        "disclaimer": "educational and research tool",
        "appendix_metrics": {"k": 1},
    }

    md = build_research_note_markdown(payload)

    assert "## Executive Summary" in md
    assert "## Methodology" in md
    assert "## Selected Factors" in md
    assert "## Key Risks" in md
    assert "## Disclaimer" in md
    assert "## Appendix Metrics" in md
