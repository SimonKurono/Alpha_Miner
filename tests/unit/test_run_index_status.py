from __future__ import annotations

import json
from pathlib import Path

from alpha_miner.ui.run_index import build_run_index


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_status_normalization_for_partial_and_failed_runs(tmp_path):
    artifacts = tmp_path / "artifacts"

    _write_json(
        artifacts / "f1_partial" / "ingestion_manifest.json",
        {
            "run_id": "f1_partial",
            "quality_path": "artifacts/f1_partial/ingestion_quality.json",
            "row_counts": {"market": 100, "text": 4},
            "created_at": "2026-02-26T08:00:00Z",
        },
    )
    _write_json(
        artifacts / "f1_partial" / "ingestion_quality.json",
        {
            "passed": True,
            "warnings": ["Low text coverage"],
            "failures": [],
            "market_symbol_coverage": 1.0,
            "text_symbol_coverage": 0.10,
        },
    )

    _write_json(
        artifacts / "f2_failed" / "hypothesis_manifest.json",
        {
            "run_id": "f2_failed",
            "ingestion_run_id": "f1_partial",
            "quality_gate_path": "artifacts/f2_failed/hypothesis_quality_gate.json",
            "hypotheses_path": "artifacts/f2_failed/hypotheses.json",
            "created_at": "2026-02-26T09:00:00Z",
        },
    )
    _write_json(
        artifacts / "f2_failed" / "hypothesis_quality_gate.json",
        {
            "passed": False,
            "warnings": [],
            "failures": ["text coverage below threshold"],
            "market_symbol_coverage": 1.0,
            "text_symbol_coverage": 0.10,
        },
    )
    _write_json(artifacts / "f2_failed" / "hypotheses.json", {"hypotheses": []})

    payload = build_run_index(artifacts)
    by_id = {row["run_id"]: row for row in payload["runs"]}
    assert by_id["f1_partial"]["status"] == "partial_success"
    assert by_id["f1_partial"]["errors_count"] == 0
    assert by_id["f2_failed"]["status"] == "failed"
    assert by_id["f2_failed"]["errors_count"] >= 1

