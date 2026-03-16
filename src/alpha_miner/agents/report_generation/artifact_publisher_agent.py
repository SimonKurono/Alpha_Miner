"""Publishes Feature 5 research note artifacts and manifest."""

from __future__ import annotations

from datetime import datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.schemas import Feature5RunConfig, ReportManifest, RunMeta
from alpha_miner.tools.io_utils import ensure_parent_dir, write_json


def _write_text(path: str, text: str) -> str:
    target = ensure_parent_dir(path)
    with target.open("w", encoding="utf-8") as f:
        f.write(text)
    return str(target)


class ReportPublisherAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = Feature5RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = RunMeta.model_validate(ctx.session.state.get("run.meta", {}))

        payload = dict(ctx.session.state.get("report.payload", {}))
        markdown = str(ctx.session.state.get("report.markdown", ""))
        quality = dict(ctx.session.state.get("report.quality", {}))
        errors = list(ctx.session.state.get("errors.report", []))

        markdown_path = _write_text(f"artifacts/{run_config.run_id}/research_note.md", markdown)
        payload_path = write_json(f"artifacts/{run_config.run_id}/research_note.json", payload)
        quality_path = write_json(f"artifacts/{run_config.run_id}/report_quality.json", quality)

        manifest = ReportManifest(
            run_id=run_config.run_id,
            evaluation_run_id=run_config.evaluation_run_id,
            report_markdown_path=markdown_path,
            report_payload_path=payload_path,
            quality_path=quality_path,
        )
        manifest_path = write_json(
            f"artifacts/{run_config.run_id}/report_manifest.json",
            manifest.model_dump(mode="json"),
        )

        run_stop = bool(ctx.session.state.get("run.control.stop", False))
        fatal_count = sum(1 for e in errors if bool(e.get("is_fatal", False)))
        quality_passed = bool(quality.get("passed", False))
        warning_count = len(quality.get("warnings", []))

        if run_meta.status != "failed":
            if run_stop and fatal_count > 0:
                run_meta.status = "failed"
            elif not quality_passed:
                run_meta.status = "failed"
            elif warning_count > 0:
                run_meta.status = "partial_success"
            else:
                run_meta.status = "success"

        if run_meta.finished_at is None:
            run_meta.finished_at = datetime.now(timezone.utc)
            run_meta.duration_sec = (run_meta.finished_at - run_meta.started_at).total_seconds()

        yield self._state_event(
            ctx,
            {
                "artifacts.report.manifest": manifest_path,
                "run.meta": run_meta.model_dump(mode="json"),
            },
            text=f"ReportPublisherAgent wrote manifest={manifest_path}",
        )
