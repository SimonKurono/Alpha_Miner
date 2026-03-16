"""Pydantic schemas for Feature 5 report generation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class Feature5RunConfig(BaseModel):
    run_id: str
    ingestion_run_id: str
    factor_run_id: str
    evaluation_run_id: str
    hypothesis_run_id: str | None = None
    report_mode: Literal["deterministic_first", "llm_first", "deterministic_only"] = "deterministic_first"
    factor_selection_policy: Literal[
        "promoted_plus_top_fallback", "promoted_only", "top3_always"
    ] = "promoted_plus_top_fallback"
    top_fallback_count: int = Field(default=3, ge=1, le=10)
    max_runtime_sec: int = Field(default=300, ge=60, le=900)


class RunMeta(BaseModel):
    run_id: str
    status: Literal["created", "running", "partial_success", "success", "failed"] = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    runtime_budget_sec: int = 300


class ReportFactorSummary(BaseModel):
    factor_id: str
    expression: str
    promoted: bool
    sharpe: float
    information_ratio: float
    ic_mean: float
    turnover_monthly_max: float
    oos_score: float
    decay_score: float
    composite_score: float
    reject_reasons: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)


class ResearchNotePayload(BaseModel):
    run_id: str
    title: str
    as_of_date: date
    executive_summary: str
    methodology: str
    selected_factors: list[ReportFactorSummary]
    key_risks: list[str]
    disclaimer: str
    appendix_metrics: dict[str, Any]


class ReportManifest(BaseModel):
    run_id: str
    evaluation_run_id: str
    report_markdown_path: str
    report_payload_path: str
    quality_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    error_type: str
    message: str
    retry_count: int = 0
    is_fatal: bool = False


class StateNamespace(BaseModel):
    run_config: Feature5RunConfig
    run_meta: RunMeta
    inputs_evaluation_manifest: dict[str, Any] = Field(default_factory=dict)
    inputs_evaluation_results: list[dict[str, Any]] = Field(default_factory=list)
    report_selected_factors: list[dict[str, Any]] = Field(default_factory=list)
    report_payload: dict[str, Any] = Field(default_factory=dict)
    report_markdown: str = ""
    report_quality: dict[str, Any] = Field(default_factory=dict)
    artifacts_report_manifest: Optional[str] = None
    errors_report: list[dict[str, Any]] = Field(default_factory=list)
