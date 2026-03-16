from __future__ import annotations

from alpha_miner.tools.reporting.quality import validate_research_note


def _payload(disclaimer: str) -> dict:
    return {
        "disclaimer": disclaimer,
        "selected_factors": [
            {
                "factor_id": "f1",
                "turnover_monthly_max": 1.0,
            }
        ],
    }


def test_quality_gate_fails_when_disclaimer_missing_phrase():
    md = "\n".join(
        [
            "# Alpha Miner Research Note",
            "## Executive Summary",
            "## Methodology",
            "## Selected Factors",
            "## Key Risks",
            "## Disclaimer",
            "## Appendix Metrics",
        ]
    )
    out = validate_research_note(md, _payload("not investment advice"))
    assert out["passed"] is False
    assert any("Disclaimer missing" in item for item in out["failures"])


def test_quality_gate_passes_with_required_phrase():
    md = "\n".join(
        [
            "# Alpha Miner Research Note",
            "## Executive Summary",
            "## Methodology",
            "## Selected Factors",
            "## Key Risks",
            "## Disclaimer",
            "## Appendix Metrics",
        ]
    )
    out = validate_research_note(md, _payload("This is an educational and research tool"))
    assert out["passed"] is True
    assert any("High turnover risk" in item for item in out["warnings"])
