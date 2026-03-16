"""Quality checks for Feature 5 research notes."""

from __future__ import annotations


REQUIRED_HEADINGS = [
    "# ",
    "## Executive Summary",
    "## Methodology",
    "## Selected Factors",
    "## Key Risks",
    "## Disclaimer",
    "## Appendix Metrics",
]

REQUIRED_DISCLAIMER_PHRASE = "educational and research tool"


def validate_research_note(markdown_text: str, payload: dict) -> dict:
    failures: list[str] = []
    warnings: list[str] = []

    text = markdown_text or ""
    for heading in REQUIRED_HEADINGS:
        if heading not in text:
            failures.append(f"Missing required heading: {heading}")

    disclaimer = str(payload.get("disclaimer", "")).lower()
    if REQUIRED_DISCLAIMER_PHRASE not in disclaimer:
        failures.append("Disclaimer missing required educational/research phrase")

    selected_factors = list(payload.get("selected_factors", []))
    if not selected_factors:
        failures.append("No selected factors in report payload")

    for row in selected_factors:
        turnover = float(row.get("turnover_monthly_max", 0.0))
        if turnover > 0.80:
            warnings.append(
                f"High turnover risk in factor {row.get('factor_id', '')}: {turnover:.3f}"
            )

    passed = len(failures) == 0
    return {
        "passed": passed,
        "failures": failures,
        "warnings": warnings,
    }
