"""Runs single-factor backtest for current loop index."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.evaluation.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    is_runtime_exceeded,
)
from alpha_miner.tools.backtesting.interfaces import run_backtest


class SingleFactorBacktestAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(
                ctx,
                {
                    "evaluation.loop_done": True,
                },
                text="SingleFactorBacktestAgent exiting due to run stop flag",
                escalate=True,
            )
            return

        factors = list(ctx.session.state.get("inputs.factors", []))
        idx = int(ctx.session.state.get("evaluation.current_index", 0) or 0)
        if idx >= len(factors):
            yield self._state_event(
                ctx,
                {"evaluation.loop_done": True},
                text="SingleFactorBacktestAgent completed all factors",
                escalate=True,
            )
            return

        run_meta = get_run_meta(ctx)
        errors = list(ctx.session.state.get("errors.evaluation", []))
        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="single_factor_backtest",
                message="Runtime budget exceeded during factor evaluation loop",
            )
            yield self._state_event(
                ctx,
                {
                    "errors.evaluation": errors,
                    "run.control.stop": True,
                    "evaluation.loop_done": True,
                },
                text="SingleFactorBacktestAgent stopped due to runtime budget",
                escalate=True,
            )
            return

        factor = dict(factors[idx])
        factor_id = str(factor.get("factor_id"))
        scores = list(dict(ctx.session.state.get("evaluation.scores", {})).get(factor_id, []))
        market_rows = list(ctx.session.state.get("inputs.market", []))
        run_cfg = dict(ctx.session.state.get("run.config", {}))
        benchmark_symbol = str(run_cfg.get("benchmark", "SPY")).upper()
        benchmark_rows = [
            row for row in market_rows if str(row.get("symbol", "")).upper() == benchmark_symbol
        ]

        try:
            bt = run_backtest(scores, market_rows, benchmark=benchmark_rows, cfg=run_cfg)
        except Exception as exc:  # noqa: BLE001
            errors.append(
                {
                    "source": "single_factor_backtest",
                    "error_type": "factor_backtest_failure",
                    "message": f"factor_id={factor_id} {exc}",
                    "retry_count": 0,
                    "is_fatal": False,
                }
            )
            next_idx = idx + 1
            loop_done = next_idx >= len(factors)
            yield self._state_event(
                ctx,
                {
                    "errors.evaluation": errors,
                    "evaluation.current_index": next_idx,
                    "evaluation.loop_done": loop_done,
                },
                text=f"SingleFactorBacktestAgent factor_id={factor_id} failed",
                escalate=loop_done,
            )
            return

        yield self._state_event(
            ctx,
            {
                "evaluation.current_factor": factor,
                "evaluation.current_backtest": bt,
                "evaluation.current_scores": scores,
            },
            text=f"SingleFactorBacktestAgent factor_id={factor_id} periods={bt['metrics'].get('period_count',0)}",
        )
