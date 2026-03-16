from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_miner.ui.run_index import write_run_index


def test_run_index_includes_strict_chain_when_present():
    root = Path(__file__).resolve().parents[2]
    artifacts = root / "artifacts"

    required = [
        artifacts / "f1_strict_s2_20260225" / "ingestion_manifest.json",
        artifacts / "f2_strict_20260225" / "hypothesis_manifest.json",
        artifacts / "f3_strict_20260225" / "factor_manifest.json",
        artifacts / "f4_strict_20260225" / "evaluation_manifest.json",
        artifacts / "f5_strict_20260225" / "report_manifest.json",
    ]
    if not all(path.exists() for path in required):
        pytest.skip("Strict canonical artifact set not available in this environment")

    index_path = write_run_index(artifacts)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    run_ids = {row["run_id"] for row in payload.get("runs", [])}

    assert "f1_strict_s2_20260225" in run_ids
    assert "f2_strict_20260225" in run_ids
    assert "f3_strict_20260225" in run_ids
    assert "f4_strict_20260225" in run_ids
    assert "f5_strict_20260225" in run_ids

