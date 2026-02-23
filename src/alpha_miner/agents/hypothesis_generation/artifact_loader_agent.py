"""Loads Feature 1 artifacts required by Feature 2."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.schemas import ErrorEvent, Feature2RunConfig
from alpha_miner.tools.hypothesis.interfaces import (
    load_hypothesis_input_snapshot,
    load_ingestion_manifest,
    load_ingestion_quality,
)


class Feature1ArtifactLoaderAgent(StatefulCustomAgent):
    """Loads ingestion manifest/quality/snapshot into state."""

    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="Feature1ArtifactLoaderAgent skipped due to run stop flag")
            return

        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        errors = list(ctx.session.state.get("errors.hypothesis", []))

        try:
            ingestion_manifest = load_ingestion_manifest(run_config.ingestion_run_id)
            ingestion_quality = load_ingestion_quality(run_config.ingestion_run_id)
            snapshot = load_hypothesis_input_snapshot(
                manifest_path=f"artifacts/{run_config.ingestion_run_id}/ingestion_manifest.json"
            )
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
                    "errors.hypothesis": errors,
                    "run.control.stop": True,
                },
                text=f"Feature1ArtifactLoaderAgent failed: {exc}",
            )
            return

        yield self._state_event(
            ctx,
            {
                "inputs.ingestion.manifest": ingestion_manifest,
                "inputs.ingestion.quality": ingestion_quality,
                "hypothesis.input_snapshot": snapshot,
                "errors.hypothesis": errors,
            },
            text=(
                "Feature1ArtifactLoaderAgent loaded artifacts "
                f"symbols={snapshot.get('stats', {}).get('symbols', 0)}"
            ),
        )
