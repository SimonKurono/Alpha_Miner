"""Originality + complexity scoring and final constraint filtering."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.schemas import FactorCandidate, Feature3RunConfig
from alpha_miner.tools.factors.interfaces import (
    compute_complexity_score,
    compute_originality_score,
    parse_factor_expression,
    score_hypothesis_alignment,
)


REFERENCE_FACTOR_LIBRARY = [
    "Rank(close)",
    "Normalize(close)",
    "Rank(volume)",
    "Normalize(market_cap)",
    "Rank(returns_1d)",
]


class OriginalityComplexityAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="OriginalityComplexityAgent skipped due to run stop flag")
            return

        run_config = Feature3RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        hypotheses = list(ctx.session.state.get("inputs.hypotheses", []))
        hypothesis_map = {str(h.get("hypothesis_id")): h for h in hypotheses}

        validated = [FactorCandidate.model_validate(row) for row in ctx.session.state.get("factors.validated", [])]
        rejected = [FactorCandidate.model_validate(row) for row in ctx.session.state.get("factors.rejected", [])]
        validation_rows = list(ctx.session.state.get("factors.validation", []))

        accepted: list[dict] = []
        rejected_out: list[dict] = [row.model_dump(mode="json") for row in rejected]

        dynamic_library = list(REFERENCE_FACTOR_LIBRARY)

        for candidate in validated:
            reasons: list[str] = list(candidate.reject_reasons)
            try:
                ast = parse_factor_expression(candidate.expression)
                candidate.complexity_score = compute_complexity_score(ast)
                candidate.originality_score = compute_originality_score(candidate.expression, dynamic_library)
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"scoring_parse_error: {exc}")
                candidate.passed_constraints = False
                candidate.reject_reasons = reasons
                rejected_out.append(candidate.model_dump(mode="json"))
                validation_rows.append(
                    {
                        "factor_id": candidate.factor_id,
                        "expression": candidate.expression,
                        "passed": False,
                        "errors": [f"scoring_parse_error: {exc}"],
                        "stage": "originality_complexity",
                    }
                )
                continue

            source_hypothesis = hypothesis_map.get(candidate.source_hypothesis_id, {})
            candidate.alignment_score = score_hypothesis_alignment(source_hypothesis, candidate.expression)

            if candidate.complexity_score > run_config.complexity_max:
                reasons.append(
                    f"complexity_exceeded: {candidate.complexity_score} > {run_config.complexity_max}"
                )
            if candidate.originality_score < run_config.originality_min:
                reasons.append(
                    f"originality_below_min: {candidate.originality_score:.2f} < {run_config.originality_min:.2f}"
                )

            candidate.reject_reasons = reasons
            candidate.passed_constraints = len(reasons) == 0

            validation_rows.append(
                {
                    "factor_id": candidate.factor_id,
                    "expression": candidate.expression,
                    "passed": candidate.passed_constraints,
                    "errors": reasons,
                    "stage": "originality_complexity",
                    "complexity_score": candidate.complexity_score,
                    "originality_score": candidate.originality_score,
                    "alignment_score": candidate.alignment_score,
                }
            )

            if candidate.passed_constraints:
                accepted.append(candidate.model_dump(mode="json"))
                dynamic_library.append(candidate.expression)
            else:
                rejected_out.append(candidate.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                "factors.accepted": accepted,
                "factors.rejected": rejected_out,
                "factors.validation": validation_rows,
            },
            text=(
                f"OriginalityComplexityAgent accepted={len(accepted)} "
                f"rejected={len(rejected_out)}"
            ),
        )
