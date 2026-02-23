"""Debate coordinator for light consensus rounds."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.schemas import Feature2RunConfig


class DebateCoordinatorAgent(StatefulCustomAgent):
    """Controls round progression and early stop checks."""

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_stop = bool(ctx.session.state.get("run.control.stop", False))
        rounds = list(ctx.session.state.get("hypothesis.debate.rounds", []))

        if run_stop:
            yield self._state_event(
                ctx,
                {"hypothesis.debate.stop": True, "hypothesis.debate.stop_reason": "run_control_stop"},
                text="DebateCoordinatorAgent stopping debate because run is stopped",
                escalate=True,
            )
            return

        if rounds and rounds[-1].get("stop_reason"):
            yield self._state_event(
                ctx,
                {
                    "hypothesis.debate.stop": True,
                    "hypothesis.debate.stop_reason": str(rounds[-1].get("stop_reason")),
                },
                text="DebateCoordinatorAgent early-stop: previous round reached stop condition",
                escalate=True,
            )
            return

        round_idx = int(ctx.session.state.get("hypothesis.debate.current_round", 0) or 0) + 1
        if round_idx > run_config.max_debate_rounds:
            yield self._state_event(
                ctx,
                {
                    "hypothesis.debate.stop": True,
                    "hypothesis.debate.stop_reason": "max_rounds_reached",
                },
                text="DebateCoordinatorAgent reached max rounds",
                escalate=True,
            )
            return

        yield self._state_event(
            ctx,
            {
                "hypothesis.debate.current_round": round_idx,
                "hypothesis.debate.stop": False,
            },
            text=f"DebateCoordinatorAgent starting round={round_idx}",
        )
