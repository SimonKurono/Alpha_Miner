"""Applies promotion rules and appends current factor result to state."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.tools.backtesting.interfaces import apply_promotion_rules


class PromotionJudgeAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="PromotionJudgeAgent skipped due to run stop flag")
            return

        factor = dict(ctx.session.state.get("evaluation.current_factor", {}))
        backtest = dict(ctx.session.state.get("evaluation.current_backtest", {}))
        robustness = dict(ctx.session.state.get("evaluation.current_robustness", {}))
        decay = dict(ctx.session.state.get("evaluation.current_decay", {}))

        metrics = dict(backtest.get("metrics", {}))
        metrics["oos_score"] = float(dict(robustness.get("aggregate", {})).get("oos_score", 0.0))
        metrics["decay_score"] = float(decay.get("decay_score", 0.0))

        profile = str(dict(ctx.session.state.get("run.config", {})).get("promotion_profile", "moderate"))
        promoted, reject_reasons = apply_promotion_rules(metrics, profile)

        result = {
            "factor_id": str(factor.get("factor_id", "")),
            "expression": str(factor.get("expression", "")),
            "sharpe": float(metrics.get("sharpe", 0.0)),
            "information_ratio": float(metrics.get("information_ratio", 0.0)),
            "ic_mean": float(metrics.get("ic_mean", 0.0)),
            "turnover_mean": float(metrics.get("turnover_mean", 0.0)),
            "turnover_monthly_max": float(metrics.get("turnover_monthly_max", 0.0)),
            "net_return_cagr": float(metrics.get("net_return_cagr", 0.0)),
            "max_drawdown": float(metrics.get("max_drawdown", 0.0)),
            "oos_score": float(metrics.get("oos_score", 0.0)),
            "decay_score": float(metrics.get("decay_score", 0.0)),
            "promoted": bool(promoted),
            "reject_reasons": list(reject_reasons),
        }

        results = list(ctx.session.state.get("evaluation.results", []))
        results.append(result)

        timeseries_rows = list(ctx.session.state.get("evaluation.timeseries", []))
        factor_id = result["factor_id"]
        for row in list(backtest.get("timeseries", [])):
            merged = dict(row)
            merged["factor_id"] = factor_id
            merged["expression"] = result["expression"]
            merged["oos_score"] = result["oos_score"]
            merged["decay_score"] = result["decay_score"]
            timeseries_rows.append(merged)

        idx = int(ctx.session.state.get("evaluation.current_index", 0) or 0)
        factor_count = len(ctx.session.state.get("inputs.factors", []))
        next_idx = idx + 1
        loop_done = next_idx >= factor_count

        yield self._state_event(
            ctx,
            {
                "evaluation.results": results,
                "evaluation.timeseries": timeseries_rows,
                "evaluation.current_index": next_idx,
                "evaluation.loop_done": loop_done,
            },
            text=(
                f"PromotionJudgeAgent factor_id={factor_id} promoted={promoted} "
                f"index={next_idx}/{factor_count}"
            ),
            escalate=loop_done,
        )
