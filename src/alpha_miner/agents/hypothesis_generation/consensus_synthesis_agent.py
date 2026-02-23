"""Consensus synthesis for role outputs into final hypotheses."""

from __future__ import annotations

from collections import defaultdict

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.schemas import (
    DebateRoundLog,
    Feature2RunConfig,
    HypothesisCandidate,
)
from alpha_miner.tools.hypothesis.interfaces import score_hypothesis


def compute_disagreements(candidates: list[HypothesisCandidate]) -> list[str]:
    disagreements: list[str] = []
    horizons = {c.horizon_days for c in candidates}
    directions = {c.direction for c in candidates}

    if len(horizons) > 1:
        disagreements.append("Horizon mismatch across role proposals")
    if len(directions) > 1:
        disagreements.append("Direction mismatch across role proposals")

    return disagreements


def compute_consensus_score(candidates: list[HypothesisCandidate], disagreements: list[str]) -> float:
    if not candidates:
        return 0.0

    role_union = set()
    for c in candidates:
        role_union.update(c.originating_roles)

    diversity = min(1.0, len(role_union) / 3.0)
    score = diversity - (0.12 * len(disagreements))
    return max(0.0, min(1.0, score))


def _merge_role_candidates(role_outputs: dict[str, list[dict]]) -> list[HypothesisCandidate]:
    merged: dict[str, HypothesisCandidate] = {}

    for role, rows in role_outputs.items():
        for row in rows:
            candidate = HypothesisCandidate.model_validate(row)
            key = candidate.thesis.strip().lower()
            if key not in merged:
                merged[key] = candidate
                continue

            existing = merged[key]
            existing.originating_roles = sorted(
                set(existing.originating_roles + candidate.originating_roles)
            )
            existing.supporting_symbols = sorted(
                set(existing.supporting_symbols + candidate.supporting_symbols)
            )
            existing.confidence = max(existing.confidence, candidate.confidence)

    return list(merged.values())


class ConsensusSynthesisAgent(StatefulCustomAgent):
    """Creates ranked final hypotheses and debate round logs."""

    consensus_stop_threshold: float = 0.75

    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="ConsensusSynthesisAgent skipped due to run stop flag")
            return

        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        round_idx = int(ctx.session.state.get("hypothesis.debate.current_round", 1))

        role_outputs = dict(ctx.session.state.get("hypothesis.role_outputs", {}))
        for role in ("fundamental", "sentiment", "valuation"):
            role_rows = ctx.session.state.get(f"hypothesis.role_outputs.{role}")
            if isinstance(role_rows, list):
                role_outputs[role] = role_rows
        candidates = _merge_role_candidates(role_outputs)

        for candidate in candidates:
            candidate.score_total = score_hypothesis(candidate, run_config.risk_profile)

        # Encourage cross-role agreement by adding bonus for merged role support.
        for candidate in candidates:
            candidate.score_total = min(
                1.0,
                candidate.score_total + 0.05 * max(0, len(set(candidate.originating_roles)) - 1),
            )

        candidates.sort(key=lambda c: c.score_total, reverse=True)
        final_candidates = candidates[: run_config.target_hypothesis_count]

        disagreements = compute_disagreements(final_candidates)
        consensus_score = compute_consensus_score(final_candidates, disagreements)

        stop_reason = None
        if consensus_score >= self.consensus_stop_threshold:
            stop_reason = f"consensus_reached_{consensus_score:.2f}"
        elif round_idx >= run_config.max_debate_rounds:
            stop_reason = "max_rounds_reached"

        round_log = DebateRoundLog(
            round_idx=round_idx,
            disagreements=disagreements,
            consensus_score=consensus_score,
            stop_reason=stop_reason,
        )

        rounds = list(ctx.session.state.get("hypothesis.debate.rounds", []))
        rounds.append(round_log.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                "hypothesis.final": [c.model_dump(mode="json") for c in final_candidates],
                "hypothesis.role_outputs": role_outputs,
                "hypothesis.debate.rounds": rounds,
                "hypothesis.debate.stop_reason": stop_reason,
                "hypothesis.debate.stop": stop_reason is not None,
            },
            text=(
                f"ConsensusSynthesisAgent round={round_idx} final={len(final_candidates)} "
                f"consensus={consensus_score:.2f}"
            ),
            escalate=stop_reason is not None,
        )
