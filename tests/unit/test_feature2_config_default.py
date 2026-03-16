from __future__ import annotations

from alpha_miner.agents.hypothesis_generation.config_loader import load_feature2_config


def test_feature2_config_default_gate_is_strict():
    cfg = load_feature2_config("configs/feature2_hypothesis.yaml")
    assert float(cfg["defaults"]["text_coverage_min"]) == 0.20
