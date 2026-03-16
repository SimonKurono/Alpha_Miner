"""Run configuration custom agent for Feature 5."""

from __future__ import annotations

from uuid import uuid4

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.config_loader import load_feature5_config
from alpha_miner.agents.report_generation.schemas import ErrorEvent, Feature5RunConfig, RunMeta


class ReportRunConfigAgent(StatefulCustomAgent):
    config_path: str = "configs/feature5_report.yaml"

    async def _run_async_impl(self, ctx: InvocationContext):
        config = load_feature5_config(self.config_path)
        defaults = config.get("defaults", {})
        request = dict(ctx.session.state.get("run.request", {}))

        run_id = str(request.get("run_id") or uuid4().hex[:12])
        ingestion_run_id = str(request.get("ingestion_run_id") or defaults.get("ingestion_run_id", "")).strip()
        factor_run_id = str(request.get("factor_run_id") or defaults.get("factor_run_id", "")).strip()
        evaluation_run_id = str(request.get("evaluation_run_id") or defaults.get("evaluation_run_id", "")).strip()
        hypothesis_run_id = request.get("hypothesis_run_id") or defaults.get("hypothesis_run_id")

        errors: list[dict] = []
        run_stop = False
        status = "running"

        if not evaluation_run_id or not ingestion_run_id or not factor_run_id:
            run_stop = True
            status = "failed"
            errors.append(
                ErrorEvent(
                    source="run_config",
                    error_type="missing_upstream_run_ids",
                    message="Feature 5 requires ingestion_run_id, factor_run_id, and evaluation_run_id",
                    is_fatal=True,
                ).model_dump(mode="json")
            )

        run_config = Feature5RunConfig(
            run_id=run_id,
            ingestion_run_id=ingestion_run_id or "missing",
            factor_run_id=factor_run_id or "missing",
            evaluation_run_id=evaluation_run_id or "missing",
            hypothesis_run_id=(None if not hypothesis_run_id else str(hypothesis_run_id)),
            report_mode=str(request.get("report_mode", defaults.get("report_mode", "deterministic_first"))),
            factor_selection_policy=str(
                request.get("factor_selection_policy", defaults.get("factor_selection_policy", "promoted_plus_top_fallback"))
            ),
            top_fallback_count=int(request.get("top_fallback_count", defaults.get("top_fallback_count", 3))),
            max_runtime_sec=int(request.get("max_runtime_sec", defaults.get("max_runtime_sec", 300))),
        )

        run_meta = RunMeta(run_id=run_id, status=status, runtime_budget_sec=run_config.max_runtime_sec)

        yield self._state_event(
            ctx,
            {
                "run.config": run_config.model_dump(mode="json"),
                "run.meta": run_meta.model_dump(mode="json"),
                "errors.report": errors,
                "run.control.stop": run_stop,
                "report.selected_factors": [],
                "report.payload": {},
                "report.markdown": "",
                "report.quality": {},
            },
            text=(
                f"ReportRunConfigAgent prepared run_id={run_id} "
                f"evaluation={run_config.evaluation_run_id} stop={run_stop}"
            ),
        )
