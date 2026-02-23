"""Run configuration custom agent for Feature 1."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.config_loader import (
    load_feature1_config,
    resolve_dates,
    resolve_symbols_from_config,
)
from alpha_miner.agents.data_ingestion.schemas import RunConfig, RunMeta


class RunConfigAgent(StatefulCustomAgent):
    """Builds `run.config` and `run.meta` from request + defaults."""

    config_path: str = "configs/feature1_ingestion.yaml"

    async def _run_async_impl(self, ctx: InvocationContext):
        config = load_feature1_config(self.config_path)
        defaults = config.get("defaults", {})

        request = ctx.session.state.get("run.request", {})

        run_id = str(request.get("run_id") or uuid4().hex[:12])
        default_start, default_end = resolve_dates(config)
        start_date = date.fromisoformat(str(request.get("start_date", default_start.isoformat())))
        end_date = date.fromisoformat(str(request.get("end_date", default_end.isoformat())))

        symbols = request.get("symbols") or resolve_symbols_from_config(config, limit=100)

        run_config = RunConfig(
            run_id=run_id,
            start_date=start_date,
            end_date=end_date,
            symbols=[str(s).upper() for s in symbols],
            benchmark=str(request.get("benchmark", defaults.get("benchmark", "SPY"))),
            max_runtime_sec=int(request.get("max_runtime_sec", defaults.get("max_runtime_sec", 300))),
            risk_profile=str(request.get("risk_profile", defaults.get("risk_profile", "risk_neutral"))),
        )

        run_meta = RunMeta(
            run_id=run_id,
            status="running",
            runtime_budget_sec=run_config.max_runtime_sec,
        )

        delta = {
            "run.config": run_config.model_dump(mode="json"),
            "run.meta": run_meta.model_dump(mode="json"),
            "errors.ingestion": [],
        }
        yield self._state_event(
            ctx,
            delta,
            text=f"RunConfigAgent prepared run_id={run_id} symbols={len(run_config.symbols)}",
        )
