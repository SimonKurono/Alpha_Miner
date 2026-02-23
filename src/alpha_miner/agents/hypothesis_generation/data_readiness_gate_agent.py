"""Readiness gate for Feature 2 before role generation."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.schemas import ErrorEvent, Feature2RunConfig, RunMeta
from alpha_miner.tools.hypothesis.interfaces import apply_hypothesis_gate


class DataReadinessGateAgent(StatefulCustomAgent):
    """Enforces strict prerequisites from Feature 1 quality artifacts."""

    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="DataReadinessGateAgent skipped due to run stop flag")
            return

        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        quality = dict(ctx.session.state.get("inputs.ingestion.quality", {}))
        gate = apply_hypothesis_gate(
            quality=quality,
            text_coverage_min=run_config.text_coverage_min,
            market_coverage_min=0.85,
        )

        errors = list(ctx.session.state.get("errors.hypothesis", []))

        run_stop = False
        if not gate["passed"]:
            run_stop = True
            run_meta.status = "failed"
            for failure in gate["failures"]:
                errors.append(
                    ErrorEvent(
                        source="data_gate",
                        error_type="readiness_gate_failed",
                        message=failure,
                        is_fatal=True,
                    ).model_dump(mode="json")
                )
        elif gate["warnings"]:
            run_meta.status = "partial_success"

        run_meta.finished_at = datetime.now(timezone.utc) if run_stop else run_meta.finished_at
        run_meta.duration_sec = (
            (run_meta.finished_at - run_meta.started_at).total_seconds()
            if run_meta.finished_at is not None
            else run_meta.duration_sec
        )

        delta = {
            "hypothesis.gate": gate,
            "run.meta": run_meta.model_dump(mode="json"),
            "errors.hypothesis": errors,
            "run.control.stop": run_stop,
        }
        yield self._state_event(
            ctx,
            delta,
            text=f"DataReadinessGateAgent passed={gate['passed']} failures={len(gate['failures'])}",
        )
