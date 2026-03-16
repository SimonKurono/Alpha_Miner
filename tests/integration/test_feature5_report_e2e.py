from __future__ import annotations

import asyncio
import json
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.report_generation.workflow import build_root_report_workflow
from alpha_miner.tools.io_utils import write_json


def _seed_feature5_artifacts(evaluation_run_id: str):
    write_json(
        f"artifacts/{evaluation_run_id}/evaluation_results.json",
        {
            "run_id": evaluation_run_id,
            "ingestion_run_id": "ing_demo",
            "factor_run_id": "f3_demo",
            "result_count": 3,
            "promoted_count": 1,
            "results": [
                {
                    "factor_id": "fct_001",
                    "expression": "Rank(returns_1d)",
                    "sharpe": 0.9,
                    "information_ratio": 0.4,
                    "ic_mean": 0.02,
                    "turnover_monthly_max": 0.5,
                    "oos_score": 0.7,
                    "decay_score": 0.9,
                    "promoted": True,
                    "reject_reasons": [],
                },
                {
                    "factor_id": "fct_002",
                    "expression": "Normalize(volume)",
                    "sharpe": 0.7,
                    "information_ratio": 0.3,
                    "ic_mean": 0.015,
                    "turnover_monthly_max": 1.2,
                    "oos_score": 0.6,
                    "decay_score": 0.8,
                    "promoted": False,
                    "reject_reasons": ["turnover_above_bar"],
                },
                {
                    "factor_id": "fct_003",
                    "expression": "Rank(close)",
                    "sharpe": 0.2,
                    "information_ratio": 0.1,
                    "ic_mean": 0.005,
                    "turnover_monthly_max": 0.2,
                    "oos_score": 0.3,
                    "decay_score": 0.4,
                    "promoted": False,
                    "reject_reasons": ["sharpe_below_bar"],
                },
            ],
        },
    )

    write_json(
        f"artifacts/{evaluation_run_id}/evaluation_metrics_timeseries.json",
        {
            "run_id": evaluation_run_id,
            "rows": [
                {"date": "2024-01-05", "factor_id": "fct_001", "net_return": 0.01},
                {"date": "2024-01-12", "factor_id": "fct_001", "net_return": 0.02},
            ],
            "row_count": 2,
        },
    )

    write_json(
        f"artifacts/{evaluation_run_id}/evaluation_manifest.json",
        {
            "run_id": evaluation_run_id,
            "ingestion_run_id": "ing_demo",
            "factor_run_id": "f3_demo",
            "results_path": f"artifacts/{evaluation_run_id}/evaluation_results.json",
            "timeseries_path": f"artifacts/{evaluation_run_id}/evaluation_metrics_timeseries.json",
            "created_at": "2026-02-24T00:00:00Z",
        },
    )


def test_feature5_report_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    evaluation_run_id = "f4_demo"
    report_run_id = "f5_demo"
    _seed_feature5_artifacts(evaluation_run_id)

    async def _run() -> dict:
        runner = InMemoryRunner(agent=build_root_report_workflow(), app_name="test_feature5")
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
                    "run_id": report_run_id,
                    "ingestion_run_id": "ing_demo",
                    "factor_run_id": "f3_demo",
                    "evaluation_run_id": evaluation_run_id,
                    "report_mode": "deterministic_first",
                    "factor_selection_policy": "promoted_plus_top_fallback",
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

    manifest_path = state.get("artifacts.report.manifest")
    assert manifest_path is not None
    assert Path(manifest_path).exists()

    payload = json.loads(Path(f"artifacts/{report_run_id}/research_note.json").read_text(encoding="utf-8"))
    quality = json.loads(Path(f"artifacts/{report_run_id}/report_quality.json").read_text(encoding="utf-8"))

    assert len(payload.get("selected_factors", [])) >= 1
    assert quality.get("passed") is True
