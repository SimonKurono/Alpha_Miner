"""Run configuration custom agent for Feature 4."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.evaluation.config_loader import load_feature4_config
from alpha_miner.agents.evaluation.schemas import ErrorEvent, Feature4RunConfig, RunMeta


class EvalRunConfigAgent(StatefulCustomAgent):
    config_path: str = "configs/feature4_evaluation.yaml"

    async def _run_async_impl(self, ctx: InvocationContext):
        config = load_feature4_config(self.config_path)
        defaults = config.get("defaults", {})
        request = dict(ctx.session.state.get("run.request", {}))

        run_id = str(request.get("run_id") or uuid4().hex[:12])
        ingestion_run_id = str(request.get("ingestion_run_id") or defaults.get("ingestion_run_id", "")).strip()
        factor_run_id = str(request.get("factor_run_id") or defaults.get("factor_run_id", "")).strip()

        errors: list[dict] = []
        run_stop = False
        status = "running"

        if not ingestion_run_id or not factor_run_id:
            run_stop = True
            status = "failed"
            errors.append(
                ErrorEvent(
                    source="run_config",
                    error_type="missing_upstream_run_ids",
                    message="Feature 4 requires ingestion_run_id and factor_run_id",
                    is_fatal=True,
                ).model_dump(mode="json")
            )

        start_date = request.get("start_date")
        end_date = request.get("end_date")

        run_config = Feature4RunConfig(
            run_id=run_id,
            ingestion_run_id=ingestion_run_id or "missing",
            factor_run_id=factor_run_id or "missing",
            start_date=(date.fromisoformat(str(start_date)) if start_date else None),
            end_date=(date.fromisoformat(str(end_date)) if end_date else None),
            benchmark=str(request.get("benchmark", defaults.get("benchmark", "SPY"))),
            rebalance_freq=str(request.get("rebalance_freq", defaults.get("rebalance_freq", "weekly"))),
            train_window_days=int(request.get("train_window_days", defaults.get("train_window_days", 252))),
            test_window_days=int(request.get("test_window_days", defaults.get("test_window_days", 63))),
            transaction_cost_bps=float(
                request.get("transaction_cost_bps", defaults.get("transaction_cost_bps", 10.0))
            ),
            promotion_profile=str(request.get("promotion_profile", defaults.get("promotion_profile", "moderate"))),
            max_runtime_sec=int(request.get("max_runtime_sec", defaults.get("max_runtime_sec", 300))),
        )

        run_meta = RunMeta(run_id=run_id, status=status, runtime_budget_sec=run_config.max_runtime_sec)

        yield self._state_event(
            ctx,
            {
                "run.config": run_config.model_dump(mode="json"),
                "run.meta": run_meta.model_dump(mode="json"),
                "errors.evaluation": errors,
                "run.control.stop": run_stop,
                "evaluation.current_index": 0,
                "evaluation.results": [],
                "evaluation.timeseries": [],
            },
            text=(
                f"EvalRunConfigAgent prepared run_id={run_id} "
                f"ingestion={run_config.ingestion_run_id} factor={run_config.factor_run_id} stop={run_stop}"
            ),
        )
