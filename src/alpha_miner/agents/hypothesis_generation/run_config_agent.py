"""Run configuration custom agent for Feature 2."""

from __future__ import annotations

from uuid import uuid4

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.config_loader import load_feature2_config
from alpha_miner.agents.hypothesis_generation.schemas import ErrorEvent, Feature2RunConfig, RunMeta


class HypothesisRunConfigAgent(StatefulCustomAgent):
    """Builds `run.config` and `run.meta` from request + defaults."""

    config_path: str = "configs/feature2_hypothesis.yaml"

    async def _run_async_impl(self, ctx: InvocationContext):
        config = load_feature2_config(self.config_path)
        defaults = config.get("defaults", {})
        request = dict(ctx.session.state.get("run.request", {}))

        run_id = str(request.get("run_id") or uuid4().hex[:12])
        ingestion_run_id = str(request.get("ingestion_run_id") or defaults.get("ingestion_run_id", "")).strip()

        errors: list[dict] = []
        run_stop = False
        status = "running"
        if not ingestion_run_id:
            run_stop = True
            status = "failed"
            errors.append(
                ErrorEvent(
                    source="run_config",
                    error_type="missing_ingestion_run_id",
                    message="Feature 2 requires ingestion_run_id in run request or config defaults",
                    is_fatal=True,
                ).model_dump(mode="json")
            )

        run_config = Feature2RunConfig(
            run_id=run_id,
            ingestion_run_id=ingestion_run_id or "missing",
            target_hypothesis_count=int(request.get("target_hypothesis_count", defaults.get("target_hypothesis_count", 3))),
            max_runtime_sec=int(request.get("max_runtime_sec", defaults.get("max_runtime_sec", 300))),
            risk_profile=str(request.get("risk_profile", defaults.get("risk_profile", "risk_neutral"))),
            text_coverage_min=float(request.get("text_coverage_min", defaults.get("text_coverage_min", 0.20))),
            model_policy=str(request.get("model_policy", defaults.get("model_policy", "gemini_with_search"))),
            primary_model=str(request.get("primary_model", defaults.get("primary_model", "claude-3-5-sonnet-v2@20241022"))),
            gemini_model=str(request.get("gemini_model", defaults.get("gemini_model", "gemini-2.5-flash"))),
            enable_google_search_tool=bool(
                request.get("enable_google_search_tool", defaults.get("enable_google_search_tool", True))
            ),
            max_debate_rounds=int(request.get("max_debate_rounds", defaults.get("max_debate_rounds", 2))),
        )

        run_meta = RunMeta(run_id=run_id, status=status, runtime_budget_sec=run_config.max_runtime_sec)

        delta = {
            "run.config": run_config.model_dump(mode="json"),
            "run.meta": run_meta.model_dump(mode="json"),
            "errors.hypothesis": errors,
            "hypothesis.model_trace": [],
            "run.control.stop": run_stop,
        }
        yield self._state_event(
            ctx,
            delta,
            text=(
                f"HypothesisRunConfigAgent prepared run_id={run_id} "
                f"ingestion_run_id={run_config.ingestion_run_id} stop={run_stop}"
            ),
        )
