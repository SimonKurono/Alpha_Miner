"""Pydantic schemas for Feature 2 hypothesis generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Feature2RunConfig(BaseModel):
    """Configuration for a single Feature 2 run."""

    run_id: str
    ingestion_run_id: str
    target_hypothesis_count: int = Field(default=3, ge=1, le=20)
    max_runtime_sec: int = Field(default=300, ge=60, le=900)
    risk_profile: Literal["risk_averse", "risk_neutral"] = "risk_neutral"
    text_coverage_min: float = Field(default=0.20, ge=0.0, le=1.0)
    model_policy: Literal[
        "claude_with_fallback",
        "claude_only",
        "deterministic_only",
        "gemini_with_search",
        "gemini_only",
    ] = "claude_with_fallback"
    primary_model: str = "claude-3-5-sonnet-v2@20241022"
    gemini_model: str = "gemini-2.5-flash"
    enable_google_search_tool: bool = True
    max_debate_rounds: int = Field(default=2, ge=1, le=5)


class RunMeta(BaseModel):
    """Runtime metadata for Feature 2."""

    run_id: str
    status: Literal["created", "running", "partial_success", "success", "failed"] = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    runtime_budget_sec: int = 300


class HypothesisCandidate(BaseModel):
    """Structured hypothesis candidate produced by role agents/synthesis."""

    hypothesis_id: str
    thesis: str
    horizon_days: Literal[5, 21, 63]
    direction: Literal["long_short", "long_only", "short_only"]
    evidence_summary: str
    supporting_symbols: list[str] = Field(default_factory=list)
    originating_roles: list[Literal["fundamental", "sentiment", "valuation"]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    score_total: float = Field(default=0.0, ge=0.0, le=1.0)


class DebateRoundLog(BaseModel):
    """Debate round telemetry."""

    round_idx: int
    disagreements: list[str] = Field(default_factory=list)
    consensus_score: float = Field(ge=0.0, le=1.0)
    stop_reason: str | None = None


class HypothesisGateReport(BaseModel):
    """Quality-gate result before hypothesis generation starts."""

    passed: bool
    market_symbol_coverage: float = 0.0
    text_symbol_coverage: float = 0.0
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class HypothesisManifest(BaseModel):
    """Final artifact index for Feature 2 outputs."""

    run_id: str
    ingestion_run_id: str
    hypotheses_path: str
    debate_log_path: str
    quality_gate_path: str
    model_trace_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEvent(BaseModel):
    """Structured non-fatal/fatal event for troubleshooting."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    error_type: str
    message: str
    retry_count: int = 0
    is_fatal: bool = False


class StateNamespace(BaseModel):
    """Typed state namespaces used in Feature 2."""

    run_config: Feature2RunConfig
    run_meta: RunMeta
    inputs_ingestion_manifest: dict[str, Any]
    inputs_ingestion_quality: dict[str, Any]
    hypothesis_role_outputs: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    hypothesis_model_trace: list[dict[str, Any]] = Field(default_factory=list)
    hypothesis_debate_rounds: list[dict[str, Any]] = Field(default_factory=list)
    hypothesis_final: list[dict[str, Any]] = Field(default_factory=list)
    artifacts_hypothesis_manifest: Optional[str] = None
    errors_hypothesis: list[dict[str, Any]] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_delta_for(key: str, value: Any) -> dict[str, Any]:
    return {key: value}
