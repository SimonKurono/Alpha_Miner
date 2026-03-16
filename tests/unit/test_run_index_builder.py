from __future__ import annotations

import json
from pathlib import Path

from alpha_miner.ui.run_index import build_run_index, write_run_index


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_build_run_index_detects_stage_lineage_and_summary(tmp_path):
    artifacts = tmp_path / "artifacts"

    _write_json(
        artifacts / "f1_demo" / "ingestion_manifest.json",
        {
            "run_id": "f1_demo",
            "quality_path": "artifacts/f1_demo/ingestion_quality.json",
            "row_counts": {"market": 100, "text": 12},
            "created_at": "2026-02-26T10:00:00Z",
        },
    )
    _write_json(
        artifacts / "f1_demo" / "ingestion_quality.json",
        {
            "passed": True,
            "warnings": [],
            "failures": [],
            "market_symbol_coverage": 0.95,
            "text_symbol_coverage": 0.30,
        },
    )

    _write_json(
        artifacts / "f4_demo" / "evaluation_manifest.json",
        {
            "run_id": "f4_demo",
            "ingestion_run_id": "f1_demo",
            "factor_run_id": "f3_demo",
            "results_path": "artifacts/f4_demo/evaluation_results.json",
            "created_at": "2026-02-26T11:00:00Z",
        },
    )
    _write_json(
        artifacts / "f4_demo" / "evaluation_results.json",
        {
            "result_count": 10,
            "promoted_count": 2,
        },
    )

    payload = build_run_index(artifacts)
    runs = payload["runs"]
    assert len(runs) == 2
    assert runs[0]["run_id"] == "f4_demo"
    assert runs[0]["stage"] == "feature4_evaluation"
    assert runs[0]["lineage"]["ingestion_run_id"] == "f1_demo"
    assert runs[0]["summary"]["result_count"] == 10

    f1 = [row for row in runs if row["run_id"] == "f1_demo"][0]
    assert f1["status"] == "success"
    assert f1["summary"]["quality_passed"] is True
    assert f1["summary"]["text_coverage"] == 0.30


def test_write_run_index_persists_json(tmp_path):
    artifacts = tmp_path / "artifacts"
    _write_json(
        artifacts / "f5_demo" / "report_manifest.json",
        {
            "run_id": "f5_demo",
            "evaluation_run_id": "f4_demo",
            "quality_path": "artifacts/f5_demo/report_quality.json",
            "report_payload_path": "artifacts/f5_demo/research_note.json",
            "created_at": "2026-02-26T12:00:00Z",
        },
    )
    _write_json(artifacts / "f5_demo" / "report_quality.json", {"passed": True, "warnings": [], "failures": []})
    _write_json(artifacts / "f5_demo" / "research_note.json", {"selected_factors": []})

    path = write_run_index(artifacts)
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["runs"][0]["run_id"] == "f5_demo"

