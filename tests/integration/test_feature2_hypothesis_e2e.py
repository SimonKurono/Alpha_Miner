from __future__ import annotations

import asyncio
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.hypothesis_generation.workflow import build_root_hypothesis_workflow
from alpha_miner.tools.io_utils import write_json, write_jsonl


def _seed_feature1_artifacts(tmp_path: Path, ingestion_run_id: str, text_coverage: float):
    market_path = tmp_path / f"data/processed/ingestion/{ingestion_run_id}/market_normalized.jsonl"
    text_path = tmp_path / f"data/processed/ingestion/{ingestion_run_id}/text_normalized.jsonl"

    write_jsonl(
        market_path,
        [
            {"symbol": "AAPL", "date": "2024-01-01", "close": 100.0, "volume": 1000, "returns_1d": 0.01, "returns_5d": 0.02, "market_cap": 10_000},
            {"symbol": "MSFT", "date": "2024-01-01", "close": 200.0, "volume": 1200, "returns_1d": 0.01, "returns_5d": 0.02, "market_cap": 20_000},
            {"symbol": "NVDA", "date": "2024-01-01", "close": 300.0, "volume": 1300, "returns_1d": 0.01, "returns_5d": 0.02, "market_cap": 30_000},
        ],
    )

    text_rows = [
        {
            "symbol": "AAPL",
            "doc_type": "news",
            "date": "2024-01-01",
            "title": "AAPL headline",
            "body": "sample",
            "source": "gdelt",
            "url": "https://example.com/aapl",
        }
    ]
    if text_coverage >= 0.20:
        text_rows.append(
            {
                "symbol": "MSFT",
                "doc_type": "news",
                "date": "2024-01-01",
                "title": "MSFT headline",
                "body": "sample",
                "source": "gdelt",
                "url": "https://example.com/msft",
            }
        )

    write_jsonl(text_path, text_rows)

    quality_payload = {
        "run_id": ingestion_run_id,
        "market_symbol_coverage": 1.0,
        "text_symbol_coverage": text_coverage,
        "market_row_count": 3,
        "text_row_count": len(text_rows),
        "null_rate_by_field": {},
        "warnings": [],
        "failures": [],
        "passed": True,
    }
    quality_path = write_json(f"artifacts/{ingestion_run_id}/ingestion_quality.json", quality_payload)

    write_json(
        f"artifacts/{ingestion_run_id}/ingestion_manifest.json",
        {
            "run_id": ingestion_run_id,
            "market_path": str(market_path),
            "text_path": str(text_path),
            "quality_path": quality_path,
            "row_counts": {"market": 3, "text": len(text_rows)},
            "raw_artifacts": {},
            "created_at": "2026-02-23T00:00:00Z",
        },
    )


def _run_feature2(request: dict) -> dict:
    async def _run():
        runner = InMemoryRunner(agent=build_root_hypothesis_workflow(), app_name="test_feature2")
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s1",
        )

        async for _ in runner.run_async(
            user_id="u1",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="run")]),
            state_delta={"run.request": request},
        ):
            pass

        final_session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s1",
        )
        return final_session.state

    return asyncio.run(_run())


def test_feature2_e2e_success(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _seed_feature1_artifacts(tmp_path, ingestion_run_id="ing_ok", text_coverage=0.34)

    state = _run_feature2(
        {
            "run_id": "f2_test_ok",
            "ingestion_run_id": "ing_ok",
            "model_policy": "deterministic_only",
        }
    )

    assert state["run.meta"]["status"] in {"success", "partial_success"}
    assert len(state.get("hypothesis.final", [])) == 3

    manifest_path = state.get("artifacts.hypothesis.manifest")
    assert manifest_path is not None
    assert Path(manifest_path).exists()


def test_feature2_e2e_hard_gate_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _seed_feature1_artifacts(tmp_path, ingestion_run_id="ing_bad", text_coverage=0.10)

    state = _run_feature2(
        {
            "run_id": "f2_test_gate_fail",
            "ingestion_run_id": "ing_bad",
            "model_policy": "deterministic_only",
            "text_coverage_min": 0.20,
        }
    )

    assert state["run.meta"]["status"] == "failed"
    assert any("Text symbol coverage below minimum" in failure for failure in state["hypothesis.gate"]["failures"])
