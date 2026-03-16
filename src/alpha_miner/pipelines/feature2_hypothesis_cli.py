"""CLI entrypoint for Alpha Miner Feature 2 hypothesis workflow."""

from __future__ import annotations

import argparse
import asyncio
import json

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.hypothesis_generation.workflow import build_root_hypothesis_workflow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alpha Miner Feature 2 hypothesis workflow")
    parser.add_argument("--config", default="configs/feature2_hypothesis.yaml", help="Path to YAML config")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--ingestion-run-id", required=True)
    parser.add_argument("--target-hypothesis-count", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=int, default=None)
    parser.add_argument("--risk-profile", choices=["risk_averse", "risk_neutral"], default=None)
    parser.add_argument("--text-coverage-min", type=float, default=None)
    parser.add_argument(
        "--model-policy",
        choices=["claude_with_fallback", "claude_only", "deterministic_only"],
        default=None,
    )
    parser.add_argument("--primary-model", default=None)
    parser.add_argument("--max-debate-rounds", type=int, default=None)
    parser.add_argument("--user-id", default="local_user")
    parser.add_argument("--session-id", default="feature2")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    root_agent = build_root_hypothesis_workflow(config_path=args.config)
    runner = InMemoryRunner(agent=root_agent, app_name="alpha_miner_feature2")

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

    request: dict[str, object] = {"ingestion_run_id": args.ingestion_run_id}
    if args.run_id:
        request["run_id"] = args.run_id
    if args.target_hypothesis_count is not None:
        request["target_hypothesis_count"] = args.target_hypothesis_count
    if args.max_runtime_sec is not None:
        request["max_runtime_sec"] = args.max_runtime_sec
    if args.risk_profile:
        request["risk_profile"] = args.risk_profile
    if args.text_coverage_min is not None:
        request["text_coverage_min"] = args.text_coverage_min
    if args.model_policy:
        request["model_policy"] = args.model_policy
    if args.primary_model:
        request["primary_model"] = args.primary_model
    if args.max_debate_rounds is not None:
        request["max_debate_rounds"] = args.max_debate_rounds

    message = types.Content(role="user", parts=[types.Part(text="Run feature2 hypothesis generation")])
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

    print("\n=== Feature 2 Summary ===")
    print(
        json.dumps(
            {
                "run_meta": state.get("run.meta"),
                "manifest": state.get("artifacts.hypothesis.manifest"),
                "gate": state.get("hypothesis.gate"),
                "hypothesis_count": len(state.get("hypothesis.final", [])),
                "errors": state.get("errors.hypothesis", []),
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
