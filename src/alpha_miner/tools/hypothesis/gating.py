"""Gate checks for Feature 2 readiness."""

from __future__ import annotations

from typing import Any


def apply_hypothesis_gate(
    quality: dict[str, Any],
    text_coverage_min: float,
    market_coverage_min: float = 0.85,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []

    quality_passed = bool(quality.get("passed", False))
    market_cov = float(quality.get("market_symbol_coverage", 0.0) or 0.0)
    text_cov = float(quality.get("text_symbol_coverage", 0.0) or 0.0)

    if not quality_passed:
        failures.append("Feature 1 quality report indicates failed ingestion gate")

    if market_cov < market_coverage_min:
        failures.append(
            f"Market symbol coverage below minimum: {market_cov:.2f} < {market_coverage_min:.2f}"
        )

    if text_cov < text_coverage_min:
        failures.append(
            f"Text symbol coverage below minimum: {text_cov:.2f} < {text_coverage_min:.2f}"
        )

    for message in quality.get("warnings", []):
        warnings.append(f"Ingestion warning: {message}")

    return {
        "passed": len(failures) == 0,
        "market_symbol_coverage": market_cov,
        "text_symbol_coverage": text_cov,
        "failures": failures,
        "warnings": warnings,
    }
