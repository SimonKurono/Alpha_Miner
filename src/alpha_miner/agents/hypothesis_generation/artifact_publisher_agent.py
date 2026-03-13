"""Artifact publisher for Feature 2 hypothesis outputs."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.schemas import Feature2RunConfig, HypothesisManifest, RunMeta
from alpha_miner.tools.io_utils import write_json


class HypothesisPublisherAgent(StatefulCustomAgent):
    """Writes final hypothesis artifacts and manifest."""

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        gate_payload = dict(ctx.session.state.get("hypothesis.gate", {}))
        hypotheses_payload = list(ctx.session.state.get("hypothesis.final", []))
        debate_payload = list(ctx.session.state.get("hypothesis.debate.rounds", []))
        model_trace_payload = list(ctx.session.state.get("hypothesis.model_trace", []))

        gate_path = write_json(
            f"artifacts/{run_config.run_id}/hypothesis_quality_gate.json",
            gate_payload,
        )
        hypotheses_path = write_json(
            f"artifacts/{run_config.run_id}/hypotheses.json",
            {
                "run_id": run_config.run_id,
                "ingestion_run_id": run_config.ingestion_run_id,
                "hypotheses": hypotheses_payload,
            },
        )
        debate_path = write_json(
            f"artifacts/{run_config.run_id}/debate_log.json",
            {
                "run_id": run_config.run_id,
                "rounds": debate_payload,
            },
        )
        model_trace_path = write_json(
            f"artifacts/{run_config.run_id}/model_trace.json",
            {
                "run_id": run_config.run_id,
                "trace": model_trace_payload,
            },
        )

        manifest = HypothesisManifest(
            run_id=run_config.run_id,
            ingestion_run_id=run_config.ingestion_run_id,
            hypotheses_path=hypotheses_path,
            debate_log_path=debate_path,
            quality_gate_path=gate_path,
            model_trace_path=model_trace_path,
        )
        manifest_path = write_json(
            f"artifacts/{run_config.run_id}/hypothesis_manifest.json",
            manifest.model_dump(mode="json"),
        )

        run_stop = bool(ctx.session.state.get("run.control.stop", False))
        if run_meta.status != "failed":
            if run_stop:
                run_meta.status = "failed"
            elif gate_payload.get("warnings"):
                run_meta.status = "partial_success"
            else:
                run_meta.status = "success"

        if run_meta.finished_at is None:
            run_meta.finished_at = datetime.now(timezone.utc)
            run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        yield self._state_event(
            ctx,
            {
                "artifacts.hypothesis.manifest": manifest_path,
                "run.meta": run_meta.model_dump(mode="json"),
            },
            text=f"HypothesisPublisherAgent wrote manifest={manifest_path}",
        )
