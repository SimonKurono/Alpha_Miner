"""Loads Feature 4 artifacts for Feature 5 report generation."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.schemas import ErrorEvent, Feature5RunConfig
from alpha_miner.tools.reporting.interfaces import load_evaluation_bundle


class ReportArtifactLoaderAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ReportArtifactLoaderAgent skipped due to run stop flag")
            return

        run_config = Feature5RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        errors = list(ctx.session.state.get("errors.report", []))

        try:
            bundle = load_evaluation_bundle(run_config.evaluation_run_id)
            manifest = dict(bundle["manifest"])
            results_payload = dict(bundle["results"])
            timeseries_payload = dict(bundle["timeseries"])
            results = list(results_payload.get("results", []))
            if not results:
                raise ValueError("No evaluation results rows available")
        except Exception as exc:  # noqa: BLE001
            errors.append(
                ErrorEvent(
                    source="artifact_loader",
                    error_type="missing_or_invalid_artifact",
                    message=str(exc),
                    is_fatal=True,
                ).model_dump(mode="json")
            )
            yield self._state_event(
                ctx,
                {
                    "errors.report": errors,
                    "run.control.stop": True,
                },
                text=f"ReportArtifactLoaderAgent failed: {exc}",
            )
            return

        yield self._state_event(
            ctx,
            {
                "inputs.evaluation.manifest": manifest,
                "inputs.evaluation.results": results,
                "inputs.evaluation.results_meta": {
                    "result_count": int(results_payload.get("result_count", len(results))),
                    "promoted_count": int(results_payload.get("promoted_count", 0)),
                },
                "inputs.evaluation.timeseries": list(timeseries_payload.get("rows", [])),
            },
            text=f"ReportArtifactLoaderAgent loaded results={len(results)}",
        )
