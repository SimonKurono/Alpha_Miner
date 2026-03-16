"""Computes per-factor score frames from market data and DSL expressions."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.evaluation.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    is_runtime_exceeded,
)
from alpha_miner.tools.backtesting.interfaces import compute_factor_scores


class ScoreComputationAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ScoreComputationAgent skipped due to run stop flag")
            return

        run_meta = get_run_meta(ctx)
        errors = list(ctx.session.state.get("errors.evaluation", []))

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="score_computation",
                message="Runtime budget exceeded before score computation",
            )
            yield self._state_event(
                ctx,
                {
                    "errors.evaluation": errors,
                    "evaluation.scores": {},
                    "run.control.stop": True,
                },
                text="ScoreComputationAgent stopped due to runtime budget",
            )
            return

        market_rows = list(ctx.session.state.get("inputs.market", []))
        factors = list(ctx.session.state.get("inputs.factors", []))

        score_map: dict[str, list[dict]] = {}
        rejected_ids: list[str] = []
        for factor in factors:
            factor_id = str(factor.get("factor_id"))
            expression = str(factor.get("expression", ""))
            try:
                rows = compute_factor_scores(market_rows, expression)
                for row in rows:
                    row["factor_id"] = factor_id
                score_map[factor_id] = rows
            except Exception as exc:  # noqa: BLE001
                rejected_ids.append(factor_id)
                errors.append(
                    {
                        "source": "score_computation",
                        "error_type": "factor_score_failure",
                        "message": f"factor_id={factor_id} {exc}",
                        "retry_count": 0,
                        "is_fatal": False,
                    }
                )

        remaining_factors = [f for f in factors if str(f.get("factor_id")) in score_map]
        run_stop = len(remaining_factors) == 0

        yield self._state_event(
            ctx,
            {
                "evaluation.scores": score_map,
                "inputs.factors": remaining_factors,
                "errors.evaluation": errors,
                "run.control.stop": run_stop,
            },
            text=(
                f"ScoreComputationAgent computed={len(score_map)} failed={len(rejected_ids)}"
            ),
        )
