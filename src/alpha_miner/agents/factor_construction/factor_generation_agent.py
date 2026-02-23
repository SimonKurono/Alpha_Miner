"""Deterministic factor-expression candidate generation from hypotheses."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.factor_construction.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.factor_construction.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    is_runtime_exceeded,
)
from alpha_miner.agents.factor_construction.schemas import FactorCandidate, Feature3RunConfig


BASE_FACTOR_TEMPLATES = [
    "Rank(returns_1d)",
    "Rank(returns_5d)",
    "Normalize(volume)",
    "Normalize(market_cap)",
    "Rank(close)",
    "WinsorizedSum(Rank(returns_1d), Normalize(volume))",
    "WinsorizedSum(Rank(returns_5d), Normalize(close))",
    "Rank(returns_1d) + Normalize(volume)",
    "Rank(returns_5d) - Normalize(market_cap)",
    "(Rank(close) * 0.5) + (Normalize(volume) * 0.5)",
    "WinsorizedSum(Rank(close / market_cap), Normalize(returns_5d))",
    "Rank(returns_1d / close) * Normalize(volume)",
    "Normalize(returns_5d) + Normalize(returns_1d)",
    "WinsorizedSum(Rank(market_cap), Normalize(volume), Rank(returns_1d))",
    "Rank(close / volume)",
]


class FactorGenerationAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="FactorGenerationAgent skipped due to run stop flag")
            return

        run_config = Feature3RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = get_run_meta(ctx)
        errors = list(ctx.session.state.get("errors.factor", []))

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="factor_generation",
                message="Runtime budget exceeded before factor generation",
            )
            yield self._state_event(
                ctx,
                {
                    "errors.factor": errors,
                    "factors.candidates": [],
                    "run.control.stop": True,
                },
                text="FactorGenerationAgent stopped due to runtime budget",
            )
            return

        hypotheses = list(ctx.session.state.get("inputs.hypotheses", []))
        if not hypotheses:
            yield self._state_event(
                ctx,
                {
                    "factors.candidates": [],
                    "run.control.stop": True,
                },
                text="FactorGenerationAgent failed: no upstream hypotheses",
            )
            return

        candidates: list[dict] = []
        for idx in range(run_config.target_factor_count):
            expression = BASE_FACTOR_TEMPLATES[idx % len(BASE_FACTOR_TEMPLATES)]
            source = hypotheses[idx % len(hypotheses)]
            source_hypothesis_id = str(source.get("hypothesis_id", f"h{idx+1}"))

            candidate = FactorCandidate(
                factor_id=f"fct_{idx+1:03d}",
                expression=expression,
                source_hypothesis_id=source_hypothesis_id,
            )
            candidates.append(candidate.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                "factors.candidates": candidates,
                "errors.factor": errors,
            },
            text=f"FactorGenerationAgent produced candidates={len(candidates)}",
        )
