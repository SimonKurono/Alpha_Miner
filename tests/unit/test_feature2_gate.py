from __future__ import annotations

from alpha_miner.tools.hypothesis.gating import apply_hypothesis_gate


def test_feature2_gate_fails_on_low_text_coverage():
    report = apply_hypothesis_gate(
        quality={
            "passed": True,
            "market_symbol_coverage": 1.0,
            "text_symbol_coverage": 0.10,
            "warnings": ["Low text symbol coverage: 10.00%"],
        },
        text_coverage_min=0.20,
        market_coverage_min=0.85,
    )

    assert report["passed"] is False
    assert any("Text symbol coverage below minimum" in item for item in report["failures"])


def test_feature2_gate_passes_when_thresholds_met():
    report = apply_hypothesis_gate(
        quality={
            "passed": True,
            "market_symbol_coverage": 0.90,
            "text_symbol_coverage": 0.25,
            "warnings": [],
        },
        text_coverage_min=0.20,
        market_coverage_min=0.85,
    )

    assert report["passed"] is True
    assert report["failures"] == []
