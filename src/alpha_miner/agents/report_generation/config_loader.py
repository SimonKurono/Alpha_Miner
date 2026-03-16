"""Config loader for Feature 5 report generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = "configs/feature5_report.yaml"


def load_feature5_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "report_mode": "deterministic_first",
                "factor_selection_policy": "promoted_plus_top_fallback",
                "top_fallback_count": 3,
                "max_runtime_sec": 300,
            }
        }
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
