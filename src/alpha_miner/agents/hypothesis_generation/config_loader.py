"""Config loader for Feature 2 hypothesis generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = "configs/feature2_hypothesis.yaml"


def load_feature2_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "target_hypothesis_count": 3,
                "max_runtime_sec": 300,
                "risk_profile": "risk_neutral",
                "text_coverage_min": 0.20,
                "model_policy": "gemini_with_search",
                "primary_model": "claude-3-5-sonnet-v2@20241022",
                "gemini_model": "gemini-2.5-flash",
                "enable_google_search_tool": True,
                "max_debate_rounds": 2,
            }
        }
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
