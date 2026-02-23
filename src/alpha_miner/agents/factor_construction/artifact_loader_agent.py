"""Loads Feature 1/2 artifacts required by Feature 3."""

from __future__ import annotations

import json
from pathlib import Path

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.schemas import ErrorEvent, Feature3RunConfig


def _read_json(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing artifact: {target}")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


class UpstreamArtifactLoaderAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="UpstreamArtifactLoaderAgent skipped due to run stop flag")
            return

        run_config = Feature3RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        errors = list(ctx.session.state.get("errors.factor", []))

        ingestion_manifest_path = f"artifacts/{run_config.ingestion_run_id}/ingestion_manifest.json"
        hypotheses_path = f"artifacts/{run_config.hypothesis_run_id}/hypotheses.json"

        try:
            ingestion_manifest = _read_json(ingestion_manifest_path)
            hypotheses_payload = _read_json(hypotheses_path)
            hypotheses = list(hypotheses_payload.get("hypotheses", []))
            if not hypotheses:
                raise ValueError("No hypotheses found in hypotheses artifact")
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
                    "errors.factor": errors,
                    "run.control.stop": True,
                },
                text=f"UpstreamArtifactLoaderAgent failed: {exc}",
            )
            return

        yield self._state_event(
            ctx,
            {
                "inputs.ingestion.manifest": ingestion_manifest,
                "inputs.hypotheses": hypotheses,
                "errors.factor": errors,
            },
            text=f"UpstreamArtifactLoaderAgent loaded hypotheses={len(hypotheses)}",
        )
