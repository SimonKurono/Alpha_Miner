from __future__ import annotations

import asyncio
import json
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.report_generation.workflow import build_root_report_workflow
from alpha_miner.tools.io_utils import write_json


def test_feature5_golden_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    evaluation_run_id = "f4_golden"
    write_json(
        f"artifacts/{evaluation_run_id}/evaluation_results.json",
        {
            "run_id": evaluation_run_id,
            "ingestion_run_id": "ing_golden",
            "factor_run_id": "f3_golden",
            "result_count": 3,
            "promoted_count": 0,
            "results": [
                {
                    "factor_id": "fct_a",
                    "expression": "Normalize(volume)",
                    "sharpe": 0.7,
                    "information_ratio": 0.4,
                    "ic_mean": 0.02,
                    "turnover_monthly_max": 0.9,
                    "oos_score": 0.8,
                    "decay_score": 0.9,
                    "promoted": False,
                    "reject_reasons": ["turnover_above_bar"],
                },
                {
                    "factor_id": "fct_b",
                    "expression": "Rank(returns_5d)",
                    "sharpe": 0.6,
                    "information_ratio": 0.3,
                    "ic_mean": 0.015,
                    "turnover_monthly_max": 0.7,
                    "oos_score": 0.6,
                    "decay_score": 0.8,
                    "promoted": False,
                    "reject_reasons": ["sharpe_below_bar"],
                },
                {
                    "factor_id": "fct_c",
                    "expression": "Rank(close)",
                    "sharpe": 0.2,
                    "information_ratio": 0.1,
                    "ic_mean": 0.005,
                    "turnover_monthly_max": 0.2,
                    "oos_score": 0.2,
                    "decay_score": 0.3,
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
            "rows": [],
            "row_count": 0,
        },
    )
    write_json(
        f"artifacts/{evaluation_run_id}/evaluation_manifest.json",
        {
            "run_id": evaluation_run_id,
            "ingestion_run_id": "ing_golden",
            "factor_run_id": "f3_golden",
            "results_path": f"artifacts/{evaluation_run_id}/evaluation_results.json",
            "timeseries_path": f"artifacts/{evaluation_run_id}/evaluation_metrics_timeseries.json",
            "created_at": "2026-02-24T00:00:00Z",
        },
    )

    async def _run() -> dict:
        runner = InMemoryRunner(agent=build_root_report_workflow(), app_name="eval_feature5")
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
                    "run_id": "f5_golden",
                    "ingestion_run_id": "ing_golden",
                    "factor_run_id": "f3_golden",
                    "evaluation_run_id": evaluation_run_id,
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
    assert state["run.meta"]["status"] in {"success", "partial_success"}

    payload = json.loads(Path("artifacts/f5_golden/research_note.json").read_text(encoding="utf-8"))
    md = Path("artifacts/f5_golden/research_note.md").read_text(encoding="utf-8")

    ids = [row["factor_id"] for row in payload.get("selected_factors", [])]
    assert ids == ["fct_a", "fct_b", "fct_c"]
    assert "No factors met promotion bar" in payload.get("executive_summary", "")
    assert "## Disclaimer" in md
