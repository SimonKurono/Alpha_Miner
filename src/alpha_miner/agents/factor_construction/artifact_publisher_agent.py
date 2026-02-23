"""Artifact publisher for Feature 3 factor outputs."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.schemas import FactorManifest, Feature3RunConfig, RunMeta
from alpha_miner.tools.io_utils import write_json


class FactorPublisherAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = Feature3RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        candidates = list(ctx.session.state.get("factors.candidates", []))
        accepted = list(ctx.session.state.get("factors.accepted", []))
        rejected = list(ctx.session.state.get("factors.rejected", []))
        validation_rows = list(ctx.session.state.get("factors.validation", []))

        factors_path = write_json(
            f"artifacts/{run_config.run_id}/factors.json",
            {
                "run_id": run_config.run_id,
                "ingestion_run_id": run_config.ingestion_run_id,
                "hypothesis_run_id": run_config.hypothesis_run_id,
                "candidate_count": len(candidates),
                "accepted_count": len(accepted),
                "rejected_count": len(rejected),
                "candidates": candidates,
                "accepted": accepted,
                "rejected": rejected,
            },
        )

        validation_path = write_json(
            f"artifacts/{run_config.run_id}/factor_validation.json",
            {
                "run_id": run_config.run_id,
                "rows": validation_rows,
                "summary": {
                    "candidate_count": len(candidates),
                    "accepted_count": len(accepted),
                    "rejected_count": len(rejected),
                },
            },
        )

        manifest = FactorManifest(
            run_id=run_config.run_id,
            ingestion_run_id=run_config.ingestion_run_id,
            hypothesis_run_id=run_config.hypothesis_run_id,
            factors_path=factors_path,
            validation_path=validation_path,
        )
        manifest_path = write_json(
            f"artifacts/{run_config.run_id}/factor_manifest.json",
            manifest.model_dump(mode="json"),
        )

        run_stop = bool(ctx.session.state.get("run.control.stop", False))
        if run_meta.status != "failed":
            if run_stop:
                run_meta.status = "failed"
            elif rejected:
                run_meta.status = "partial_success"
            else:
                run_meta.status = "success"

        if run_meta.finished_at is None:
            run_meta.finished_at = datetime.now(timezone.utc)
            run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        yield self._state_event(
            ctx,
            {
                "artifacts.factor.manifest": manifest_path,
                "run.meta": run_meta.model_dump(mode="json"),
            },
            text=f"FactorPublisherAgent wrote manifest={manifest_path}",
        )
