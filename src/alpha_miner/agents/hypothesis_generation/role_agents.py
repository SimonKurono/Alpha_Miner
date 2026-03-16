"""Role-specialized hypothesis generation agents for Feature 2."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.hypothesis_generation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.hypothesis_generation.model_factory import create_model_backend
from alpha_miner.agents.hypothesis_generation.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    get_runtime_remaining_sec,
    is_runtime_exceeded,
)
from alpha_miner.agents.hypothesis_generation.schemas import ErrorEvent, Feature2RunConfig, HypothesisCandidate
from alpha_miner.tools.hypothesis.interfaces import score_hypothesis

RoleName = Literal["fundamental", "sentiment", "valuation"]


def _top_symbols(snapshot: dict, count: int = 5) -> list[str]:
    symbols = [str(s).upper() for s in snapshot.get("symbols", []) if str(s).strip()]
    return symbols[:count]


def _deterministic_candidate(role: RoleName, snapshot: dict, risk_profile: str) -> HypothesisCandidate:
    symbols = _top_symbols(snapshot, count=5)

    templates = {
        "fundamental": {
            "thesis": "Firms with recent SEC filing activity and stable positive 1M returns are more likely to outperform over the next month.",
            "horizon_days": 21,
            "direction": "long_only",
            "evidence": "SEC 10-K/10-Q presence plus recent return persistence suggests continued fundamental drift.",
            "confidence": 0.63,
        },
        "sentiment": {
            "thesis": "Stocks with positive recent news flow and supportive short-term momentum tend to deliver excess returns over a 1-week horizon.",
            "horizon_days": 5,
            "direction": "long_short",
            "evidence": "News mentions combined with short-term return direction can proxy sentiment persistence.",
            "confidence": 0.58,
        },
        "valuation": {
            "thesis": "Large-cap names with moderate pullbacks and resilient liquidity may mean-revert positively over the next quarter.",
            "horizon_days": 63,
            "direction": "long_only",
            "evidence": "Market cap and volume stability indicate tradability; pullback regimes can revert on medium horizons.",
            "confidence": 0.60,
        },
    }

    chosen = templates[role]
    confidence = float(chosen["confidence"])
    if risk_profile == "risk_averse" and role == "sentiment":
        confidence = max(0.0, confidence - 0.06)

    return HypothesisCandidate(
        hypothesis_id=f"{role}_h1",
        thesis=str(chosen["thesis"]),
        horizon_days=int(chosen["horizon_days"]),
        direction=str(chosen["direction"]),
        evidence_summary=str(chosen["evidence"]),
        supporting_symbols=symbols,
        originating_roles=[role],
        confidence=confidence,
    )


def _extract_json_block(text: str) -> str:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return text

    match = re.search(r"\[(?:.|\n|\r)*\]", text)
    if not match:
        raise ValueError("Model output did not contain a JSON array payload")
    return match.group(0)


def _role_prompt(role: RoleName, snapshot: dict, risk_profile: str) -> str:
    symbols = ", ".join(_top_symbols(snapshot, 10))
    stats = snapshot.get("stats", {})

    return (
        "You are a quant analyst role agent. Generate exactly one structured hypothesis as JSON array with one object.\n"
        "Allowed keys: thesis,horizon_days,direction,evidence_summary,supporting_symbols,confidence.\n"
        "horizon_days must be one of [5,21,63]; direction one of [long_short,long_only,short_only].\n"
        f"Role: {role}. Risk profile: {risk_profile}.\n"
        f"Data stats: {json.dumps(stats, sort_keys=True)}\n"
        f"Representative symbols: {symbols}\n"
        "Return JSON only."
    )


def _parse_model_candidates(role: RoleName, raw_text: str) -> list[HypothesisCandidate]:
    payload = _extract_json_block(raw_text)
    rows = json.loads(payload)
    if not isinstance(rows, list) or not rows:
        raise ValueError("Model payload must be a non-empty JSON list")

    out: list[HypothesisCandidate] = []
    for idx, row in enumerate(rows, start=1):
        row = dict(row)
        row.setdefault("supporting_symbols", [])
        row.setdefault("confidence", 0.55)
        row.setdefault("originating_roles", [role])
        row["hypothesis_id"] = f"{role}_llm_{idx}"
        candidate = HypothesisCandidate.model_validate(row)
        out.append(candidate)
    return out


class RoleHypothesisAgent(StatefulCustomAgent):
    """Single role agent that emits structured candidate hypotheses."""

    role_name: RoleName = "fundamental"
    min_llm_remaining_sec: int = 45

    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text=f"{self.name} skipped due to run stop flag")
            return

        run_config = Feature2RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = get_run_meta(ctx)
        snapshot = dict(ctx.session.state.get("hypothesis.input_snapshot", {}))

        errors = list(ctx.session.state.get("errors.hypothesis", []))
        role_output_key = f"hypothesis.role_outputs.{self.role_name}"
        model_trace_key = "hypothesis.model_trace"
        candidates: list[HypothesisCandidate] = []
        role_model_trace: dict[str, Any] = {
            "role": self.role_name,
            "provider": "deterministic",
            "model": "deterministic",
            "google_search_tool_enabled": False,
            "attempts": 0,
            "fallback_used": False,
        }

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source=self.role_name,
                message=f"Runtime budget exceeded before {self.role_name} role generation",
            )
            yield self._state_event(
                ctx,
                {
                    "errors.hypothesis": errors,
                    role_output_key: [],
                    "run.control.stop": True,
                },
                text=f"{self.name} stopped due to runtime budget",
            )
            return

        backend = create_model_backend(
            model_policy=run_config.model_policy,
            primary_model=run_config.primary_model,
            gemini_model=run_config.gemini_model,
            enable_google_search_tool=run_config.enable_google_search_tool,
        )
        if backend.warning:
            errors.append(
                ErrorEvent(
                    source=self.role_name,
                    error_type="model_fallback",
                    message=backend.warning,
                    is_fatal=False,
                ).model_dump(mode="json")
            )
            role_model_trace["fallback_used"] = True
            role_model_trace["warning"] = backend.warning
        role_model_trace["provider"] = backend.mode
        role_model_trace["model"] = (
            run_config.gemini_model if backend.mode == "gemini" else run_config.primary_model
        )
        role_model_trace["google_search_tool_enabled"] = bool(
            backend.mode == "gemini" and run_config.enable_google_search_tool
        )

        if backend.mode in {"claude", "gemini"} and get_runtime_remaining_sec(run_meta) >= self.min_llm_remaining_sec:
            try:
                prompt = _role_prompt(self.role_name, snapshot=snapshot, risk_profile=run_config.risk_profile)
                raw, generated_trace = backend.generate_text(prompt)
                role_model_trace.update(generated_trace)
                candidates = _parse_model_candidates(self.role_name, raw)
            except Exception as exc:  # noqa: BLE001
                if run_config.model_policy in {"claude_only", "gemini_only"}:
                    errors.append(
                        ErrorEvent(
                            source=self.role_name,
                            error_type=f"{backend.mode}_generation_failed",
                            message=str(exc),
                            is_fatal=True,
                        ).model_dump(mode="json")
                    )
                    yield self._state_event(
                        ctx,
                        {
                            "errors.hypothesis": errors,
                            role_output_key: [],
                            "run.control.stop": True,
                            model_trace_key: list(ctx.session.state.get(model_trace_key, [])) + [role_model_trace],
                        },
                        text=f"{self.name} failed in strict {backend.mode} mode: {exc}",
                    )
                    return

                errors.append(
                    ErrorEvent(
                        source=self.role_name,
                        error_type=f"{backend.mode}_generation_failed_fallback",
                        message=str(exc),
                        is_fatal=False,
                    ).model_dump(mode="json")
                )
                role_model_trace["fallback_used"] = True
                role_model_trace["error"] = str(exc)

        if not candidates:
            candidates = [_deterministic_candidate(self.role_name, snapshot=snapshot, risk_profile=run_config.risk_profile)]
            if backend.mode == "deterministic":
                role_model_trace["provider"] = "deterministic"
                role_model_trace["model"] = "deterministic"

        scored: list[dict] = []
        for candidate in candidates:
            candidate.score_total = score_hypothesis(candidate, run_config.risk_profile)
            scored.append(candidate.model_dump(mode="json"))

        yield self._state_event(
            ctx,
            {
                role_output_key: scored,
                "errors.hypothesis": errors,
                model_trace_key: list(ctx.session.state.get(model_trace_key, [])) + [role_model_trace],
            },
            text=f"{self.name} produced {len(scored)} candidate(s)",
        )
