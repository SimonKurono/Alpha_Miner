"""Builds deterministic Feature 5 research note payload and markdown draft."""

from __future__ import annotations

from datetime import date, datetime, timezone

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.report_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.report_generation.schemas import Feature5RunConfig, ResearchNotePayload
from alpha_miner.tools.reporting.interfaces import build_research_note_markdown


def _as_date_from_manifest(manifest: dict) -> date:
    raw = manifest.get("created_at")
    if raw:
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
        except Exception:  # noqa: BLE001
            pass
    return datetime.now(timezone.utc).date()


class ReportDraftAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ReportDraftAgent skipped due to run stop flag")
            return

        run_config = Feature5RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        selected_factors = list(ctx.session.state.get("report.selected_factors", []))
        selection_meta = dict(ctx.session.state.get("report.selection.meta", {}))
        eval_manifest = dict(ctx.session.state.get("inputs.evaluation.manifest", {}))
        eval_results_meta = dict(ctx.session.state.get("inputs.evaluation.results_meta", {}))

        selected_count = len(selected_factors)
        promoted_selected_count = sum(1 for row in selected_factors if bool(row.get("promoted", False)))
        fallback_used = bool(selection_meta.get("fallback_used", False))

        if fallback_used:
            summary_line = (
                "No factors met promotion bar; top candidates are shown for continued research iteration."
            )
        else:
            summary_line = (
                f"Selected {promoted_selected_count} promoted factor(s) from evaluation results for reporting."
            )

        methodology = (
            "Factors were evaluated in Feature 4 using deterministic score computation, "
            "weekly-rebalanced long-short portfolio construction, 10 bps turnover-based transaction costs, "
            "rolling out-of-sample robustness checks, and decay diagnostics."
        )

        key_risks = [
            "Prototype pipeline currently uses temporary text coverage gate (0.10) pending upstream stability restoration.",
            "Backtest results are historical simulations and can be sensitive to universe, costs, and data quality assumptions.",
        ]
        if any("high_turnover_risk" in list(row.get("risk_tags", [])) for row in selected_factors):
            key_risks.append("One or more selected factors exhibit high turnover, which can reduce net performance in production.")

        if run_config.report_mode == "llm_first":
            key_risks.append("LLM enrichment is not enabled in this run; deterministic draft was used.")

        payload = ResearchNotePayload(
            run_id=run_config.run_id,
            title="Alpha Miner Research Note",
            as_of_date=_as_date_from_manifest(eval_manifest),
            executive_summary=(
                f"Evaluation run `{run_config.evaluation_run_id}` produced {int(eval_results_meta.get('result_count', 0))} factor result(s); "
                f"{int(eval_results_meta.get('promoted_count', 0))} met promotion thresholds. "
                f"Report includes {selected_count} selected factor(s). {summary_line}"
            ),
            methodology=methodology,
            selected_factors=selected_factors,
            key_risks=key_risks,
            disclaimer=(
                "Alpha Miner is an educational and research tool only. "
                "This output is not financial advice and should not be used as a sole basis for investment decisions."
            ),
            appendix_metrics={
                "lineage": {
                    "ingestion_run_id": run_config.ingestion_run_id,
                    "factor_run_id": run_config.factor_run_id,
                    "evaluation_run_id": run_config.evaluation_run_id,
                    "hypothesis_run_id": run_config.hypothesis_run_id,
                },
                "selection": selection_meta,
                "selected_factor_ids": [row.get("factor_id", "") for row in selected_factors],
                "promoted_selected_count": promoted_selected_count,
            },
        )

        markdown = build_research_note_markdown(payload.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                "report.payload": payload.model_dump(mode="json"),
                "report.markdown": markdown,
            },
            text=f"ReportDraftAgent drafted report with selected={selected_count}",
        )
