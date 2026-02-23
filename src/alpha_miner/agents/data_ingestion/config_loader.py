"""Config loader for Feature 1 ingestion."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = "configs/feature1_ingestion.yaml"


def load_feature1_config(config_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        return {
            "defaults": {
                "benchmark": "SPY",
                "max_runtime_sec": 300,
                "risk_profile": "risk_neutral",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
            },
            "universe": {"symbols": []},
        }
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_symbols_from_config(config: dict[str, Any], limit: int = 100) -> list[str]:
    symbols = config.get("universe", {}).get("symbols", [])
    clean = [str(s).upper().strip() for s in symbols if str(s).strip()]
    # preserve order and uniqueness
    seen: set[str] = set()
    out: list[str] = []
    for symbol in clean:
        if symbol in seen:
            continue
        seen.add(symbol)
        out.append(symbol)
        if len(out) >= limit:
            break
    return out


def resolve_dates(config: dict[str, Any]) -> tuple[date, date]:
    defaults = config.get("defaults", {})
    start = date.fromisoformat(defaults.get("start_date", "2020-01-01"))
    end = date.fromisoformat(defaults.get("end_date", "2024-12-31"))
    return start, end
