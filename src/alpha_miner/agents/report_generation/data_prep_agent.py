"""Selects factors and prepares report-level structured rows."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.schemas import ErrorEvent, Feature5RunConfig, ReportFactorSummary
from alpha_miner.tools.reporting.interfaces import select_report_factors


class ReportDataPrepAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ReportDataPrepAgent skipped due to run stop flag")
            return

        run_config = Feature5RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        errors = list(ctx.session.state.get("errors.report", []))
        results = list(ctx.session.state.get("inputs.evaluation.results", []))

        if not results:
            errors.append(
                ErrorEvent(
                    source="data_prep",
                    error_type="empty_results",
                    message="No evaluation results available for report selection",
                    is_fatal=True,
                ).model_dump(mode="json")
            )
            yield self._state_event(
                ctx,
                {
                    "errors.report": errors,
                    "run.control.stop": True,
                },
                text="ReportDataPrepAgent failed: no results",
            )
            return

        selected = select_report_factors(
            results,
            policy=run_config.factor_selection_policy,
            top_fallback_count=run_config.top_fallback_count,
        )
        promoted_count = sum(1 for row in results if bool(row.get("promoted", False)))
        fallback_used = run_config.factor_selection_policy == "promoted_plus_top_fallback" and promoted_count == 0

        if not selected:
            errors.append(
                ErrorEvent(
                    source="data_prep",
                    error_type="empty_selection",
                    message="Factor selection produced zero rows",
                    is_fatal=True,
                ).model_dump(mode="json")
            )
            yield self._state_event(
                ctx,
                {
                    "errors.report": errors,
                    "run.control.stop": True,
                },
                text="ReportDataPrepAgent failed: empty selection",
            )
            return

        summaries: list[dict] = []
        for row in selected:
            risk_tags: list[str] = []
            if float(row.get("turnover_monthly_max", 0.0)) > 0.80:
                risk_tags.append("high_turnover_risk")

            summary = ReportFactorSummary(
                factor_id=str(row.get("factor_id", "")),
                expression=str(row.get("expression", "")),
                promoted=bool(row.get("promoted", False)),
                sharpe=float(row.get("sharpe", 0.0)),
                information_ratio=float(row.get("information_ratio", 0.0)),
                ic_mean=float(row.get("ic_mean", 0.0)),
                turnover_monthly_max=float(row.get("turnover_monthly_max", 0.0)),
                oos_score=float(row.get("oos_score", 0.0)),
                decay_score=float(row.get("decay_score", 0.0)),
                composite_score=float(row.get("composite_score", 0.0)),
                reject_reasons=list(row.get("reject_reasons", [])),
                risk_tags=risk_tags,
            )
            summaries.append(summary.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                "report.selected_factors": summaries,
                "report.selection.meta": {
                    "policy": run_config.factor_selection_policy,
                    "fallback_used": fallback_used,
                    "source_result_count": len(results),
                    "selected_count": len(summaries),
                    "promoted_source_count": promoted_count,
                },
            },
            text=f"ReportDataPrepAgent selected={len(summaries)} fallback_used={fallback_used}",
        )
