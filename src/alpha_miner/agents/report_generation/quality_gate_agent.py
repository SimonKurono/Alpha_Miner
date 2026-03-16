"""Quality gate for Feature 5 research note outputs."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.schemas import ErrorEvent
from alpha_miner.tools.reporting.interfaces import validate_research_note


class ReportQualityGateAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ReportQualityGateAgent skipped due to run stop flag")
            return

        markdown = str(ctx.session.state.get("report.markdown", ""))
        payload = dict(ctx.session.state.get("report.payload", {}))
        errors = list(ctx.session.state.get("errors.report", []))
        selection_meta = dict(ctx.session.state.get("report.selection.meta", {}))

        quality = validate_research_note(markdown, payload)
        warnings = list(quality.get("warnings", []))
        if bool(selection_meta.get("fallback_used", False)):
            warnings.append(
                "No promoted factors available; applied promoted_plus_top_fallback selection path."
            )

        quality["warnings"] = warnings

        run_stop = False
        if not bool(quality.get("passed", False)):
            run_stop = True
            errors.append(
                ErrorEvent(
                    source="quality_gate",
                    error_type="quality_gate_failed",
                    message="; ".join(list(quality.get("failures", []))) or "Report quality gate failed",
                    is_fatal=True,
                ).model_dump(mode="json")
            )

        yield self._state_event(
            ctx,
            {
                "report.quality": quality,
                "errors.report": errors,
                "run.control.stop": run_stop,
            },
            text=(
                f"ReportQualityGateAgent passed={quality.get('passed', False)} "
                f"warnings={len(quality.get('warnings', []))}"
            ),
        )
