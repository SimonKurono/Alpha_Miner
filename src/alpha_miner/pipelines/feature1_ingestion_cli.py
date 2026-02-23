"""CLI entrypoint for Alpha Miner Feature 1 ingestion workflow."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.data_ingestion.config_loader import load_feature1_config, resolve_symbols_from_config
from alpha_miner.agents.data_ingestion.workflow import build_root_ingestion_workflow


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Alpha Miner Feature 1 ingestion workflow")
    parser.add_argument("--config", default="configs/feature1_ingestion.yaml", help="Path to YAML config")
    parser.add_argument("--run-id", default=None, help="Optional run id")
    parser.add_argument("--start-date", default=None, help="Override start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="Override end date (YYYY-MM-DD)")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbol list")
    parser.add_argument("--symbols-file", default=None, help="File with one symbol per line")
    parser.add_argument("--max-runtime-sec", type=int, default=None, help="Override runtime budget")
    parser.add_argument("--risk-profile", choices=["risk_averse", "risk_neutral"], default=None)
    parser.add_argument("--user-id", default="local_user")
    parser.add_argument("--session-id", default="feature1")
    return parser.parse_args()


def _resolve_symbols(args: argparse.Namespace, config_path: str) -> list[str] | None:
    if args.symbols:
        return [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if args.symbols_file:
        rows = Path(args.symbols_file).read_text(encoding="utf-8").splitlines()
        return [r.strip().upper() for r in rows if r.strip()]

    config = load_feature1_config(config_path)
    symbols = resolve_symbols_from_config(config, limit=100)
    return symbols or None


async def _run(args: argparse.Namespace) -> int:
    root_agent = build_root_ingestion_workflow(config_path=args.config)
    runner = InMemoryRunner(agent=root_agent, app_name="alpha_miner_feature1")

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

    request: dict[str, object] = {}
    if args.run_id:
        request["run_id"] = args.run_id
    if args.start_date:
        request["start_date"] = args.start_date
    if args.end_date:
        request["end_date"] = args.end_date
    if args.max_runtime_sec is not None:
        request["max_runtime_sec"] = args.max_runtime_sec
    if args.risk_profile:
        request["risk_profile"] = args.risk_profile

    resolved_symbols = _resolve_symbols(args, args.config)
    if resolved_symbols:
        request["symbols"] = resolved_symbols

    message = types.Content(role="user", parts=[types.Part(text="Run feature1 ingestion")])
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
    breakdown_path = state.get("ingestion.text.coverage_breakdown")
    top_missing_reasons = {}
    if breakdown_path:
        try:
            top_missing_reasons = json.loads(Path(str(breakdown_path)).read_text(encoding="utf-8")).get(
                "top_missing_reasons", {}
            )
        except Exception:  # noqa: BLE001
            top_missing_reasons = {}

    print("\n=== Feature 1 Summary ===")
    print(json.dumps({
        "run_meta": state.get("run.meta"),
        "manifest": state.get("artifacts.ingestion.manifest"),
        "quality": state.get("ingestion.quality"),
        "text_coverage_breakdown": breakdown_path,
        "top_missing_reasons": top_missing_reasons,
        "errors": state.get("errors.ingestion", []),
    }, indent=2))

    return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
