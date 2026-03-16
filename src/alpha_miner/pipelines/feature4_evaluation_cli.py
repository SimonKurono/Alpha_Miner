"""CLI entrypoint for Alpha Miner Feature 4 evaluation workflow."""

from __future__ import annotations

import argparse
import asyncio
import json

from google.genai import types

from alpha_miner.agents.evaluation.workflow import build_root_evaluation_workflow
from alpha_miner.pipelines.runtime_utils import build_runner


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alpha Miner Feature 4 evaluation workflow")
    parser.add_argument("--config", default="configs/feature4_evaluation.yaml", help="Path to YAML config")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--ingestion-run-id", required=True)
    parser.add_argument("--factor-run-id", required=True)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--benchmark", default=None)
    parser.add_argument("--rebalance-freq", choices=["weekly", "monthly"], default=None)
    parser.add_argument("--train-window-days", type=int, default=None)
    parser.add_argument("--test-window-days", type=int, default=None)
    parser.add_argument("--transaction-cost-bps", type=float, default=None)
    parser.add_argument("--promotion-profile", choices=["moderate", "strict", "lenient"], default=None)
    parser.add_argument("--max-runtime-sec", type=int, default=None)
    parser.add_argument("--user-id", default="local_user")
    parser.add_argument("--session-id", default="feature4")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> int:
    root_agent = build_root_evaluation_workflow(config_path=args.config)
    runner = build_runner(root_agent, fallback_app_name="alpha_miner_feature4")

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
    }
    if args.run_id:
        request["run_id"] = args.run_id
    if args.start_date is not None:
        request["start_date"] = args.start_date
    if args.end_date is not None:
        request["end_date"] = args.end_date
    if args.benchmark is not None:
        request["benchmark"] = args.benchmark
    if args.rebalance_freq is not None:
        request["rebalance_freq"] = args.rebalance_freq
    if args.train_window_days is not None:
        request["train_window_days"] = args.train_window_days
    if args.test_window_days is not None:
        request["test_window_days"] = args.test_window_days
    if args.transaction_cost_bps is not None:
        request["transaction_cost_bps"] = args.transaction_cost_bps
    if args.promotion_profile is not None:
        request["promotion_profile"] = args.promotion_profile
    if args.max_runtime_sec is not None:
        request["max_runtime_sec"] = args.max_runtime_sec

    message = types.Content(role="user", parts=[types.Part(text="Run feature4 evaluation")])
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

    print("\n=== Feature 4 Summary ===")
    print(
        json.dumps(
            {
                "run_meta": state.get("run.meta"),
                "manifest": state.get("artifacts.evaluation.manifest"),
                "result_count": len(state.get("evaluation.results", [])),
                "promoted_count": sum(
                    1 for row in state.get("evaluation.results", []) if bool(row.get("promoted", False))
                ),
                "errors": state.get("errors.evaluation", []),
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
