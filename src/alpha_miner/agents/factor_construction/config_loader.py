"""Config loader for Feature 3 factor construction."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = "configs/feature3_factor.yaml"


def load_feature3_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "target_factor_count": 10,
                "max_runtime_sec": 300,
                "originality_min": 0.20,
                "complexity_max": 16,
            }
        }
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
