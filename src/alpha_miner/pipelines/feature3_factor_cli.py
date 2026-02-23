"""CLI entrypoint for Alpha Miner Feature 3 factor construction workflow."""

from __future__ import annotations

import argparse
import asyncio
import json

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.factor_construction.workflow import build_root_factor_workflow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alpha Miner Feature 3 factor workflow")
    parser.add_argument("--config", default="configs/feature3_factor.yaml", help="Path to YAML config")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--ingestion-run-id", required=True)
    parser.add_argument("--hypothesis-run-id", required=True)
    parser.add_argument("--target-factor-count", type=int, default=None)
    parser.add_argument("--max-runtime-sec", type=int, default=None)
    parser.add_argument("--originality-min", type=float, default=None)
    parser.add_argument("--complexity-max", type=int, default=None)
    parser.add_argument("--user-id", default="local_user")
    parser.add_argument("--session-id", default="feature3")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    root_agent = build_root_factor_workflow(config_path=args.config)
    runner = InMemoryRunner(agent=root_agent, app_name="alpha_miner_feature3")

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
        "hypothesis_run_id": args.hypothesis_run_id,
    }
    if args.run_id:
        request["run_id"] = args.run_id
    if args.target_factor_count is not None:
        request["target_factor_count"] = args.target_factor_count
    if args.max_runtime_sec is not None:
        request["max_runtime_sec"] = args.max_runtime_sec
    if args.originality_min is not None:
        request["originality_min"] = args.originality_min
    if args.complexity_max is not None:
        request["complexity_max"] = args.complexity_max

    message = types.Content(role="user", parts=[types.Part(text="Run feature3 factor construction")])
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

    print("\n=== Feature 3 Summary ===")
    print(
        json.dumps(
            {
                "run_meta": state.get("run.meta"),
                "manifest": state.get("artifacts.factor.manifest"),
                "candidate_count": len(state.get("factors.candidates", [])),
                "accepted_count": len(state.get("factors.accepted", [])),
                "rejected_count": len(state.get("factors.rejected", [])),
                "errors": state.get("errors.factor", []),
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
