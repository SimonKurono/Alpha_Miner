from __future__ import annotations

import asyncio

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.hypothesis_generation.workflow import build_root_hypothesis_workflow
from alpha_miner.tools.io_utils import write_json, write_jsonl


def test_feature2_golden_trajectory_deterministic(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingestion_run_id = "ing_golden"
    market_path = tmp_path / f"data/processed/ingestion/{ingestion_run_id}/market_normalized.jsonl"
    text_path = tmp_path / f"data/processed/ingestion/{ingestion_run_id}/text_normalized.jsonl"

    write_jsonl(
        market_path,
        [
            {"symbol": "AAPL", "date": "2024-01-01", "close": 100.0, "volume": 1000},
            {"symbol": "MSFT", "date": "2024-01-01", "close": 200.0, "volume": 1000},
            {"symbol": "NVDA", "date": "2024-01-01", "close": 300.0, "volume": 1000},
        ],
    )
    write_jsonl(
        text_path,
        [
            {"symbol": "AAPL", "doc_type": "news", "date": "2024-01-01", "title": "a", "source": "gdelt", "url": "u1"},
            {"symbol": "MSFT", "doc_type": "news", "date": "2024-01-01", "title": "b", "source": "gdelt", "url": "u2"},
        ],
    )

    quality_path = write_json(
        f"artifacts/{ingestion_run_id}/ingestion_quality.json",
        {
            "run_id": ingestion_run_id,
            "market_symbol_coverage": 1.0,
            "text_symbol_coverage": 0.66,
            "market_row_count": 3,
            "text_row_count": 2,
            "null_rate_by_field": {},
            "warnings": [],
            "failures": [],
            "passed": True,
        },
    )

    write_json(
        f"artifacts/{ingestion_run_id}/ingestion_manifest.json",
        {
            "run_id": ingestion_run_id,
            "market_path": str(market_path),
            "text_path": str(text_path),
            "quality_path": quality_path,
            "row_counts": {"market": 3, "text": 2},
            "raw_artifacts": {},
            "created_at": "2026-02-23T00:00:00Z",
        },
    )

    async def _run():
        runner = InMemoryRunner(agent=build_root_hypothesis_workflow(), app_name="eval_feature2")
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s1",
        )
        async for _ in runner.run_async(
            user_id="u1",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="run")]),
            state_delta={
                "run.request": {
                    "run_id": "f2_eval_golden",
                    "ingestion_run_id": ingestion_run_id,
                    "model_policy": "deterministic_only",
                }
            },
        ):
            pass

        final_session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id=session.id,
        )
        return final_session.state

    state = asyncio.run(_run())
    ids = {h["hypothesis_id"] for h in state.get("hypothesis.final", [])}

    assert state["run.meta"]["status"] in {"success", "partial_success"}
    assert {"fundamental_h1", "sentiment_h1", "valuation_h1"}.issubset(ids)
