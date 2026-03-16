"""CLI entrypoint for Alpha Miner Feature 5 report generation workflow."""

from __future__ import annotations

import argparse
import asyncio
import json

from google.genai import types

from alpha_miner.agents.report_generation.workflow import build_root_report_workflow
from alpha_miner.pipelines.runtime_utils import build_runner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alpha Miner Feature 5 report generation workflow")
    parser.add_argument("--config", default="configs/feature5_report.yaml", help="Path to YAML config")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--ingestion-run-id", required=True)
    parser.add_argument("--factor-run-id", required=True)
    parser.add_argument("--evaluation-run-id", required=True)
    parser.add_argument("--hypothesis-run-id", default=None)
    parser.add_argument(
        "--report-mode",
        choices=["deterministic_first", "llm_first", "deterministic_only"],
        default=None,
    )
    parser.add_argument(
        "--factor-selection-policy",
        choices=["promoted_plus_top_fallback", "promoted_only", "top3_always"],
        default=None,
    )
    parser.add_argument("--top-fallback-count", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=int, default=None)
    parser.add_argument("--user-id", default="local_user")
    parser.add_argument("--session-id", default="feature5")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    root_agent = build_root_report_workflow(config_path=args.config)
    runner = build_runner(root_agent, fallback_app_name="alpha_miner_feature5")

    try:
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=args.user_id,
            session_id=args.session_id,
        )
    except Exception:  # noqa: BLE001
        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id=args.user_id,
            session_id=args.session_id,
        )

    request: dict[str, object] = {
        "ingestion_run_id": args.ingestion_run_id,
        "factor_run_id": args.factor_run_id,
        "evaluation_run_id": args.evaluation_run_id,
    }
    if args.run_id:
        request["run_id"] = args.run_id
    if args.hypothesis_run_id is not None:
        request["hypothesis_run_id"] = args.hypothesis_run_id
    if args.report_mode is not None:
        request["report_mode"] = args.report_mode
    if args.factor_selection_policy is not None:
        request["factor_selection_policy"] = args.factor_selection_policy
    if args.top_fallback_count is not None:
        request["top_fallback_count"] = args.top_fallback_count
    if args.max_runtime_sec is not None:
        request["max_runtime_sec"] = args.max_runtime_sec

    message = types.Content(role="user", parts=[types.Part(text="Run feature5 report generation")])
    async for event in runner.run_async(
        user_id=args.user_id,
        session_id=session.id,
        new_message=message,
        state_delta={"run.request": request},
    ):
        if event.content and event.content.parts and event.content.parts[0].text:
            print(event.content.parts[0].text)

    final_session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=args.user_id,
        session_id=session.id,
    )
    state = final_session.state

    print("\n=== Feature 5 Summary ===")
    print(
        json.dumps(
            {
                "run_meta": state.get("run.meta"),
                "manifest": state.get("artifacts.report.manifest"),
                "selected_count": len(state.get("report.selected_factors", [])),
                "quality": state.get("report.quality", {}),
                "errors": state.get("errors.report", []),
            },
            indent=2,
        )
    )

    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
