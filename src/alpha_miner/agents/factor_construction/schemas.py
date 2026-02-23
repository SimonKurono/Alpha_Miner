"""Pydantic schemas for Feature 3 factor construction."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Feature3RunConfig(BaseModel):
    run_id: str
    ingestion_run_id: str
    hypothesis_run_id: str
    target_factor_count: int = Field(default=10, ge=1, le=100)
    max_runtime_sec: int = Field(default=300, ge=60, le=900)
    originality_min: float = Field(default=0.20, ge=0.0, le=1.0)
    complexity_max: int = Field(default=16, ge=1, le=200)


class RunMeta(BaseModel):
    run_id: str
    status: Literal["created", "running", "partial_success", "success", "failed"] = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    runtime_budget_sec: int = 300


class FactorCandidate(BaseModel):
    factor_id: str
    expression: str
    source_hypothesis_id: str
    alignment_score: float = Field(default=0.0, ge=0.0, le=1.0)
    originality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity_score: int = 0
    passed_constraints: bool = False
    reject_reasons: list[str] = Field(default_factory=list)


class FactorManifest(BaseModel):
    run_id: str
    ingestion_run_id: str
    hypothesis_run_id: str
    factors_path: str
    validation_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    error_type: str
    message: str
    retry_count: int = 0
    is_fatal: bool = False


class StateNamespace(BaseModel):
    run_config: Feature3RunConfig
    run_meta: RunMeta
    inputs_hypotheses: list[dict[str, Any]] = Field(default_factory=list)
    inputs_ingestion_manifest: dict[str, Any] = Field(default_factory=dict)
    factors_candidates: list[dict[str, Any]] = Field(default_factory=list)
    factors_validated: list[dict[str, Any]] = Field(default_factory=list)
    factors_rejected: list[dict[str, Any]] = Field(default_factory=list)
    artifacts_factor_manifest: Optional[str] = None
    errors_factor: list[dict[str, Any]] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
