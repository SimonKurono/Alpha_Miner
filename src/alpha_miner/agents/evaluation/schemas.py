"""Pydantic schemas for Feature 4 evaluation pipeline."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class Feature4RunConfig(BaseModel):
    run_id: str
    ingestion_run_id: str
    factor_run_id: str
    start_date: date | None = None
    end_date: date | None = None
    benchmark: str = "SPY"
    rebalance_freq: Literal["weekly", "monthly"] = "weekly"
    train_window_days: int = Field(default=252, ge=20, le=1000)
    test_window_days: int = Field(default=63, ge=5, le=365)
    transaction_cost_bps: float = Field(default=10.0, ge=0.0, le=500.0)
    promotion_profile: Literal["moderate", "strict", "lenient"] = "moderate"
    max_runtime_sec: int = Field(default=300, ge=60, le=900)

    @model_validator(mode="after")
    def _validate_dates(self) -> "Feature4RunConfig":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class RunMeta(BaseModel):
    run_id: str
    status: Literal["created", "running", "partial_success", "success", "failed"] = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    runtime_budget_sec: int = 300


class FactorEvaluationResult(BaseModel):
    factor_id: str
    expression: str
    sharpe: float
    information_ratio: float
    ic_mean: float
    turnover_mean: float
    turnover_monthly_max: float
    net_return_cagr: float
    max_drawdown: float
    oos_score: float
    decay_score: float
    promoted: bool
    reject_reasons: list[str] = Field(default_factory=list)


class EvaluationManifest(BaseModel):
    run_id: str
    ingestion_run_id: str
    factor_run_id: str
    results_path: str
    timeseries_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    error_type: str
    message: str
    retry_count: int = 0
    is_fatal: bool = False


class StateNamespace(BaseModel):
    run_config: Feature4RunConfig
    run_meta: RunMeta
    inputs_market: list[dict[str, Any]] = Field(default_factory=list)
    inputs_factors: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_current_index: int = 0
    evaluation_results: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_timeseries: list[dict[str, Any]] = Field(default_factory=list)
    artifacts_evaluation_manifest: Optional[str] = None
    errors_evaluation: list[dict[str, Any]] = Field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
