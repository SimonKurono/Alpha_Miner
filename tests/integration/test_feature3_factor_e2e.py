from __future__ import annotations

import asyncio
import json
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.factor_construction.workflow import build_root_factor_workflow
from alpha_miner.tools.io_utils import write_json


def _seed_artifacts(base: Path, ingestion_run_id: str, hypothesis_run_id: str):
    write_json(
        base / f"artifacts/{ingestion_run_id}/ingestion_manifest.json",
        {
            "run_id": ingestion_run_id,
            "market_path": "data/processed/ingestion/demo/market_normalized.jsonl",
            "text_path": "data/processed/ingestion/demo/text_normalized.jsonl",
            "quality_path": f"artifacts/{ingestion_run_id}/ingestion_quality.json",
            "row_counts": {"market": 100, "text": 10},
            "raw_artifacts": {},
            "created_at": "2026-02-23T00:00:00Z",
        },
    )

    write_json(
        base / f"artifacts/{hypothesis_run_id}/hypotheses.json",
        {
            "run_id": hypothesis_run_id,
            "ingestion_run_id": ingestion_run_id,
            "hypotheses": [
                {
                    "hypothesis_id": "fundamental_h1",
                    "thesis": "Momentum and filings can predict next-month performance.",
                    "horizon_days": 21,
                    "direction": "long_only",
                    "evidence_summary": "Recent filings and positive returns often persist.",
                    "supporting_symbols": ["AAPL", "MSFT"],
                    "originating_roles": ["fundamental"],
                    "confidence": 0.62,
                    "score_total": 0.6,
                },
                {
                    "hypothesis_id": "sentiment_h1",
                    "thesis": "News momentum can drive short-term moves.",
                    "horizon_days": 5,
                    "direction": "long_short",
                    "evidence_summary": "Positive news flow correlates with short-term returns.",
                    "supporting_symbols": ["NVDA", "AMZN"],
                    "originating_roles": ["sentiment"],
                    "confidence": 0.58,
                    "score_total": 0.55,
                },
            ],
        },
    )


def test_feature3_factor_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    ingestion_run_id = "ing_demo"
    hypothesis_run_id = "hyp_demo"
    run_id = "f3_demo"

    _seed_artifacts(tmp_path, ingestion_run_id=ingestion_run_id, hypothesis_run_id=hypothesis_run_id)

    async def _run():
        runner = InMemoryRunner(agent=build_root_factor_workflow(), app_name="test_feature3")
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
                    "run_id": run_id,
                    "ingestion_run_id": ingestion_run_id,
                    "hypothesis_run_id": hypothesis_run_id,
                    "target_factor_count": 10,
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
    manifest_path = state.get("artifacts.factor.manifest")
    assert manifest_path is not None
    assert Path(manifest_path).exists()

    factors = json.loads(Path(f"artifacts/{run_id}/factors.json").read_text(encoding="utf-8"))
    validation = json.loads(Path(f"artifacts/{run_id}/factor_validation.json").read_text(encoding="utf-8"))

    assert factors["candidate_count"] >= 10
    assert len(factors["candidates"]) >= 10
    assert len(validation["rows"]) >= 10
