"""Stable interfaces for Feature 5 reporting tools."""

from __future__ import annotations

import json
from pathlib import Path

from alpha_miner.tools.reporting.quality import validate_research_note
from alpha_miner.tools.reporting.selection import compute_report_composite_score, select_report_factors
from alpha_miner.tools.reporting.templating import build_research_note_markdown


def _read_json(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing artifact: {target}")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_evaluation_bundle(evaluation_run_id: str) -> dict:
    manifest = _read_json(f"artifacts/{evaluation_run_id}/evaluation_manifest.json")
    results_payload = _read_json(manifest["results_path"])
    timeseries_payload = _read_json(manifest["timeseries_path"])
    return {
        "manifest": manifest,
        "results": results_payload,
        "timeseries": timeseries_payload,
    }


__all__ = [
    "load_evaluation_bundle",
    "compute_report_composite_score",
    "select_report_factors",
    "build_research_note_markdown",
    "validate_research_note",
]
