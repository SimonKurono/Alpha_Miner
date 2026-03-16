"""Config loader for Feature 4 evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = "configs/feature4_evaluation.yaml"


def load_feature4_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "benchmark": "SPY",
                "rebalance_freq": "weekly",
                "train_window_days": 252,
                "test_window_days": 63,
                "transaction_cost_bps": 10.0,
                "promotion_profile": "moderate",
                "max_runtime_sec": 300,
            }
        }
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
