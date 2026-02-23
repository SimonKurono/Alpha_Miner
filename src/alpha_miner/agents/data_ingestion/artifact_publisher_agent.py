"""Artifact publisher custom agent."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.schemas import IngestionManifest, RunConfig, RunMeta
from alpha_miner.tools.io_utils import write_json


class ArtifactPublisherAgent(StatefulCustomAgent):
    """Persists final manifest and run status."""

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        market_path = str(ctx.session.state.get("ingestion.market.normalized", ""))
        text_path = str(ctx.session.state.get("ingestion.text.normalized", ""))
        quality_payload = ctx.session.state.get("ingestion.quality", {})

        quality_path = write_json(
            f"artifacts/{run_config.run_id}/ingestion_quality.json",
            quality_payload,
        )

        manifest = IngestionManifest(
            run_id=run_config.run_id,
            market_path=market_path,
            text_path=text_path,
            quality_path=quality_path,
            row_counts={
                "market": int(quality_payload.get("market_row_count", 0)),
                "text": int(quality_payload.get("text_row_count", 0)),
            },
            raw_artifacts={
                **dict(ctx.session.state.get("ingestion.market.raw", {})),
                **dict(ctx.session.state.get("ingestion.text.raw", {})),
            },
        )

        manifest_path = write_json(
            f"artifacts/{run_config.run_id}/ingestion_manifest.json",
            manifest.model_dump(mode="json"),
        )

        if run_meta.status == "running":
            run_meta.status = "success"
        if run_meta.finished_at is None:
            run_meta.finished_at = datetime.now(timezone.utc)
            run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        delta = {
            "artifacts.ingestion.manifest": manifest_path,
            "run.meta": run_meta.model_dump(mode="json"),
        }
        yield self._state_event(
            ctx,
            delta,
            text=f"ArtifactPublisherAgent wrote manifest={manifest_path}",
        )
