"""Publishes Feature 4 evaluation artifacts and manifest."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.evaluation.schemas import EvaluationManifest, Feature4RunConfig, RunMeta
from alpha_miner.tools.io_utils import write_json


class EvalPublisherAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = Feature4RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        results = list(ctx.session.state.get("evaluation.results", []))
        timeseries = list(ctx.session.state.get("evaluation.timeseries", []))
        errors = list(ctx.session.state.get("errors.evaluation", []))

        results_path = write_json(
            f"artifacts/{run_config.run_id}/evaluation_results.json",
            {
                "run_id": run_config.run_id,
                "ingestion_run_id": run_config.ingestion_run_id,
                "factor_run_id": run_config.factor_run_id,
                "result_count": len(results),
                "promoted_count": sum(1 for row in results if bool(row.get("promoted", False))),
                "results": results,
            },
        )

        timeseries_path = write_json(
            f"artifacts/{run_config.run_id}/evaluation_metrics_timeseries.json",
            {
                "run_id": run_config.run_id,
                "rows": timeseries,
                "row_count": len(timeseries),
            },
        )

        manifest = EvaluationManifest(
            run_id=run_config.run_id,
            ingestion_run_id=run_config.ingestion_run_id,
            factor_run_id=run_config.factor_run_id,
            results_path=results_path,
            timeseries_path=timeseries_path,
        )
        manifest_path = write_json(
            f"artifacts/{run_config.run_id}/evaluation_manifest.json",
            manifest.model_dump(mode="json"),
        )

        run_stop = bool(ctx.session.state.get("run.control.stop", False))
        if run_meta.status != "failed":
            fatal_count = sum(1 for e in errors if bool(e.get("is_fatal", False)))
            if run_stop and fatal_count > 0:
                run_meta.status = "failed"
            elif fatal_count > 0:
                run_meta.status = "partial_success"
            elif results:
                promoted_count = sum(1 for row in results if bool(row.get("promoted", False)))
                run_meta.status = "success" if promoted_count > 0 else "partial_success"
            else:
                run_meta.status = "failed"

        if run_meta.finished_at is None:
            run_meta.finished_at = datetime.now(timezone.utc)
            run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        yield self._state_event(
            ctx,
            {
                "artifacts.evaluation.manifest": manifest_path,
                "run.meta": run_meta.model_dump(mode="json"),
            },
            text=f"EvalPublisherAgent wrote manifest={manifest_path}",
        )
