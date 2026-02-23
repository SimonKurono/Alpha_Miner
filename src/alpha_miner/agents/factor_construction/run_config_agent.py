"""Run configuration custom agent for Feature 3."""

from __future__ import annotations

from uuid import uuid4

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.config_loader import load_feature3_config
from alpha_miner.agents.factor_construction.schemas import ErrorEvent, Feature3RunConfig, RunMeta


class FactorRunConfigAgent(StatefulCustomAgent):
    config_path: str = "configs/feature3_factor.yaml"

    async def _run_async_impl(self, ctx: InvocationContext):
        config = load_feature3_config(self.config_path)
        defaults = config.get("defaults", {})
        request = dict(ctx.session.state.get("run.request", {}))

        run_id = str(request.get("run_id") or uuid4().hex[:12])
        ingestion_run_id = str(request.get("ingestion_run_id") or defaults.get("ingestion_run_id", "")).strip()
        hypothesis_run_id = str(request.get("hypothesis_run_id") or defaults.get("hypothesis_run_id", "")).strip()

        errors: list[dict] = []
        run_stop = False
        status = "running"

        if not ingestion_run_id or not hypothesis_run_id:
            run_stop = True
            status = "failed"
            errors.append(
                ErrorEvent(
                    source="run_config",
                    error_type="missing_upstream_run_ids",
                    message="Feature 3 requires ingestion_run_id and hypothesis_run_id",
                    is_fatal=True,
                ).model_dump(mode="json")
            )

        run_config = Feature3RunConfig(
            run_id=run_id,
            ingestion_run_id=ingestion_run_id or "missing",
            hypothesis_run_id=hypothesis_run_id or "missing",
            target_factor_count=int(request.get("target_factor_count", defaults.get("target_factor_count", 10))),
            max_runtime_sec=int(request.get("max_runtime_sec", defaults.get("max_runtime_sec", 300))),
            originality_min=float(request.get("originality_min", defaults.get("originality_min", 0.20))),
            complexity_max=int(request.get("complexity_max", defaults.get("complexity_max", 16))),
        )

        run_meta = RunMeta(
            run_id=run_id,
            status=status,
            runtime_budget_sec=run_config.max_runtime_sec,
        )

        yield self._state_event(
            ctx,
            {
                "run.config": run_config.model_dump(mode="json"),
                "run.meta": run_meta.model_dump(mode="json"),
                "errors.factor": errors,
                "run.control.stop": run_stop,
            },
            text=(
                f"FactorRunConfigAgent prepared run_id={run_id} "
                f"ingestion={run_config.ingestion_run_id} hypothesis={run_config.hypothesis_run_id} stop={run_stop}"
            ),
        )
