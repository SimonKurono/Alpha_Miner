"""Computes rolling OOS robustness and decay diagnostics for current factor."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.tools.backtesting.interfaces import run_decay_analysis, run_rolling_oos


class RobustnessDecayAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="RobustnessDecayAgent skipped due to run stop flag")
            return

        factor = dict(ctx.session.state.get("evaluation.current_factor", {}))
        backtest = dict(ctx.session.state.get("evaluation.current_backtest", {}))
        scores = list(ctx.session.state.get("evaluation.current_scores", []))
        market_rows = list(ctx.session.state.get("inputs.market", []))
        run_cfg = dict(ctx.session.state.get("run.config", {}))

        timeseries = list(backtest.get("timeseries", []))
        oos = run_rolling_oos(
            scores=scores,
            prices=market_rows,
            train_days=int(run_cfg.get("train_window_days", 252)),
            test_days=int(run_cfg.get("test_window_days", 63)),
            cfg=run_cfg,
        )
        decay = run_decay_analysis(timeseries)

        yield self._state_event(
            ctx,
            {
                "evaluation.current_robustness": oos,
                "evaluation.current_decay": decay,
            },
            text=(
                f"RobustnessDecayAgent factor_id={factor.get('factor_id','unknown')} "
                f"oos_windows={oos.get('window_count', 0)}"
            ),
        )
