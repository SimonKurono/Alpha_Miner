"""Pydantic schemas for Feature 1 ingestion pipeline."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class RunConfig(BaseModel):
    """Configuration for a single ingestion run."""

    run_id: str
    start_date: date
    end_date: date
    symbols: list[str] = Field(min_length=1)
    benchmark: str = "SPY"
    max_runtime_sec: int = Field(default=300, ge=60, le=3600)
    risk_profile: Literal["risk_averse", "risk_neutral"] = "risk_neutral"

    @model_validator(mode="after")
    def _validate_dates(self) -> "RunConfig":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class RunMeta(BaseModel):
    """Runtime metadata stored in session state."""

    run_id: str
    status: Literal["created", "running", "partial_success", "success", "failed"] = "created"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_sec: Optional[float] = None
    runtime_budget_sec: int = 300


class PriceRecord(BaseModel):
    """Single OHLCV row from a market provider."""

    symbol: str
    date: date
    close: float
    volume: float


class PriceBatchRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    provider: Literal["stooq"] = "stooq"


class PriceBatchResponse(BaseModel):
    records: list[PriceRecord] = Field(default_factory=list)
    missing_symbols: list[str] = Field(default_factory=list)
    source: str = "stooq"


class MacroPoint(BaseModel):
    date: date
    value: float


class MacroSeriesResponse(BaseModel):
    series_id: str
    points: list[MacroPoint] = Field(default_factory=list)
    source: str = "fred"


class FilingDocument(BaseModel):
    symbol: str
    cik: str
    accession_number: str
    filing_type: Literal["10-K", "10-Q"]
    filing_date: date
    report_date: Optional[date] = None
    primary_document: Optional[str] = None
    source_url: str


class SecFilingsRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    filing_types: list[Literal["10-K", "10-Q"]] = Field(default_factory=lambda: ["10-K", "10-Q"])
    lookback_days: int = Field(default=365, ge=30, le=3650)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    anchor_mode: Literal["run_window", "lookback_from_today"] = "run_window"

    @model_validator(mode="after")
    def _validate_anchor_dates(self) -> "SecFilingsRequest":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return self


class SecFilingsResponse(BaseModel):
    documents: list[FilingDocument] = Field(default_factory=list)
    missing_symbols: list[str] = Field(default_factory=list)
    source: str = "sec"


class NewsDocument(BaseModel):
    symbol: str
    source: str
    title: str
    published_at: datetime
    url: str
    snippet: Optional[str] = None
    tone: Optional[float] = None


class NewsRequest(BaseModel):
    symbols: list[str] = Field(min_length=1)
    start_date: date
    end_date: date
    max_docs_per_symbol: int = Field(default=50, ge=1, le=200)


class NewsResponse(BaseModel):
    documents: list[NewsDocument] = Field(default_factory=list)
    missing_symbols: list[str] = Field(default_factory=list)
    source: str = "gdelt"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    symbol: Optional[str] = None
    error_type: str
    message: str
    retry_count: int = 0
    is_fatal: bool = False


class QualityReport(BaseModel):
    run_id: str
    market_symbol_coverage: float = 0.0
    text_symbol_coverage: float = 0.0
    market_row_count: int = 0
    text_row_count: int = 0
    null_rate_by_field: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    passed: bool = True


class IngestionManifest(BaseModel):
    run_id: str
    market_path: str
    text_path: str
    quality_path: str
    row_counts: dict[str, int] = Field(default_factory=dict)
    raw_artifacts: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StateNamespace(BaseModel):
    """Typed view of session state namespaces for this feature."""

    run_config: RunConfig
    run_meta: RunMeta
    ingestion_market_raw: dict[str, str] = Field(default_factory=dict)
    ingestion_text_raw: dict[str, str] = Field(default_factory=dict)
    ingestion_market_normalized: Optional[str] = None
    ingestion_text_normalized: Optional[str] = None
    ingestion_text_coverage_breakdown: Optional[str] = None
    ingestion_quality: Optional[QualityReport] = None
    artifacts_ingestion_manifest: Optional[str] = None
    errors_ingestion: list[ErrorEvent] = Field(default_factory=list)


class NormalizedMarketRow(BaseModel):
    symbol: str
    date: date
    close: Optional[float] = None
    volume: Optional[float] = None
    returns_1d: Optional[float] = None
    returns_5d: Optional[float] = None
    market_cap: Optional[float] = None


class NormalizedTextRow(BaseModel):
    symbol: str
    doc_type: Literal["sec_10kq", "news"]
    date: date
    title: str
    body: Optional[str] = None
    source: str
    url: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_delta_for(key: str, value: Any) -> dict[str, Any]:
    """Helper for event state_delta payloads."""

    return {key: value}
