from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.evaluation.workflow import build_root_evaluation_workflow
from alpha_miner.tools.io_utils import write_json, write_jsonl


def _seed_feature4_artifacts(tmp_path: Path, ingestion_run_id: str, factor_run_id: str):
    market_path = tmp_path / f"data/processed/ingestion/{ingestion_run_id}/market_normalized.jsonl"

    symbols = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "SPY"]
    rows: list[dict] = []

    start = date(2024, 1, 1)
    for d in range(180):
        day = (start + timedelta(days=d)).isoformat()
        for i, sym in enumerate(symbols):
            close = 100.0 + (0.15 * d) + (i * 0.5)
            rows.append(
                {
                    "symbol": sym,
                    "date": day,
                    "close": close,
                    "volume": 1_000_000 + (i * 1000) + d,
                    "returns_1d": 0.001 * ((i % 3) - 1),
                    "returns_5d": 0.002 * (1 - (i % 3)),
                    "market_cap": 100_000_000_000 + (i * 1_000_000),
                }
            )

    write_jsonl(market_path, rows)

    write_json(
        f"artifacts/{ingestion_run_id}/ingestion_manifest.json",
        {
            "run_id": ingestion_run_id,
            "market_path": str(market_path),
            "text_path": "data/processed/ingestion/demo/text_normalized.jsonl",
            "quality_path": f"artifacts/{ingestion_run_id}/ingestion_quality.json",
            "row_counts": {"market": len(rows), "text": 0},
            "raw_artifacts": {},
            "created_at": "2026-02-24T00:00:00Z",
        },
    )

    write_json(
        f"artifacts/{factor_run_id}/factors.json",
        {
            "run_id": factor_run_id,
            "candidate_count": 2,
            "accepted_count": 2,
            "rejected_count": 0,
            "candidates": [
                {
                    "factor_id": "fct_001",
                    "expression": "Rank(returns_1d)",
                    "source_hypothesis_id": "h1",
                    "alignment_score": 0.6,
                    "originality_score": 0.9,
                    "complexity_score": 6,
                    "passed_constraints": True,
                    "reject_reasons": [],
                },
                {
                    "factor_id": "fct_002",
                    "expression": "Normalize(volume) - Rank(returns_5d)",
                    "source_hypothesis_id": "h2",
                    "alignment_score": 0.6,
                    "originality_score": 0.9,
                    "complexity_score": 8,
                    "passed_constraints": True,
                    "reject_reasons": [],
                },
            ],
            "accepted": [],
            "rejected": [],
        },
    )

    write_json(
        f"artifacts/{factor_run_id}/factor_validation.json",
        {
            "run_id": factor_run_id,
            "rows": [
                {"factor_id": "fct_001", "expression": "Rank(returns_1d)", "passed": True, "errors": [], "stage": "dsl_validation"},
                {
                    "factor_id": "fct_002",
                    "expression": "Normalize(volume) - Rank(returns_5d)",
                    "passed": True,
                    "errors": [],
                    "stage": "dsl_validation",
                },
            ],
            "summary": {"candidate_count": 2, "accepted_count": 2, "rejected_count": 0},
        },
    )

    write_json(
        f"artifacts/{factor_run_id}/factor_manifest.json",
        {
            "run_id": factor_run_id,
            "ingestion_run_id": ingestion_run_id,
            "hypothesis_run_id": "hyp_demo",
            "factors_path": f"artifacts/{factor_run_id}/factors.json",
            "validation_path": f"artifacts/{factor_run_id}/factor_validation.json",
        },
    )


def test_feature4_evaluation_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingestion_run_id = "ing_demo"
    factor_run_id = "f3_demo"
    eval_run_id = "f4_demo"
    _seed_feature4_artifacts(tmp_path, ingestion_run_id, factor_run_id)

    async def _run() -> dict:
        runner = InMemoryRunner(agent=build_root_evaluation_workflow(), app_name="test_feature4")
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
                    "run_id": eval_run_id,
                    "ingestion_run_id": ingestion_run_id,
                    "factor_run_id": factor_run_id,
                    "train_window_days": 60,
                    "test_window_days": 20,
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

    manifest_path = state.get("artifacts.evaluation.manifest")
    assert manifest_path is not None
    assert Path(manifest_path).exists()

    payload = json.loads(Path(f"artifacts/{eval_run_id}/evaluation_results.json").read_text(encoding="utf-8"))
    assert payload["result_count"] >= 1
    assert all("sharpe" in row for row in payload["results"])
