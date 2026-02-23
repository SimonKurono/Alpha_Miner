"""Quality gate custom agent."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.schemas import RunConfig, RunMeta
from alpha_miner.tools.validators.ingestion_quality import validate_ingestion_outputs


class IngestionQualityGateAgent(StatefulCustomAgent):
    """Applies schema/freshness/completeness checks."""

    min_coverage: float = 0.85

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        market_path = str(ctx.session.state.get("ingestion.market.normalized", ""))
        text_path = str(ctx.session.state.get("ingestion.text.normalized", ""))

        report = validate_ingestion_outputs(
            market_path=market_path,
            text_path=text_path,
            run_id=run_config.run_id,
            symbols=run_config.symbols,
            min_symbol_coverage=self.min_coverage,
        )

        runtime_budget_errors = [
            err
            for err in ctx.session.state.get("errors.ingestion", [])
            if err.get("error_type") == "budget_exceeded"
        ]
        if runtime_budget_errors:
            report.failures.append(
                f"Runtime budget exceeded events detected: {len(runtime_budget_errors)}"
            )

        current_duration_sec = (datetime.now(timezone.utc) - run_meta.started_at).total_seconds()
        if current_duration_sec > run_meta.runtime_budget_sec:
            report.failures.append(
                "Runtime exceeded configured budget: "
                f"{current_duration_sec:.2f}s > {run_meta.runtime_budget_sec}s"
            )

        if report.failures:
            report.passed = False

        if report.passed and report.warnings:
            run_meta.status = "partial_success"
        elif report.passed:
            run_meta.status = "running"
        else:
            run_meta.status = "failed"

        run_meta.finished_at = datetime.now(timezone.utc)
        run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        delta = {
            "ingestion.quality": report.model_dump(mode="json"),
            "run.meta": run_meta.model_dump(mode="json"),
        }

        yield self._state_event(
            ctx,
            delta,
            text=f"IngestionQualityGateAgent passed={report.passed} warnings={len(report.warnings)} failures={len(report.failures)}",
        )
