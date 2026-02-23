"""Validation logic for ingestion outputs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from alpha_miner.agents.data_ingestion.schemas import QualityReport
from alpha_miner.tools.io_utils import read_jsonl


def _load_rows(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []

    if p.suffix == ".parquet":
        try:
            import pandas as pd  # type: ignore

            return pd.read_parquet(p).to_dict(orient="records")
        except Exception:
            return []

    return read_jsonl(p)


def _null_rate(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        return {}
    fields = sorted({k for row in rows for k in row.keys()})
    counts = Counter()
    for row in rows:
        for field in fields:
            if row.get(field) in (None, ""):
                counts[field] += 1

    denom = len(rows)
    return {field: counts[field] / denom for field in fields}


def validate_ingestion_outputs(
    market_path: str,
    text_path: str,
    run_id: str,
    symbols: list[str],
    min_symbol_coverage: float = 0.85,
) -> QualityReport:
    market_rows = _load_rows(market_path)
    text_rows = _load_rows(text_path)

    symbols_set = {s.upper() for s in symbols}
    market_symbols = {str(row.get("symbol", "")).upper() for row in market_rows if row.get("symbol")}
    text_symbols = {str(row.get("symbol", "")).upper() for row in text_rows if row.get("symbol")}

    coverage_base = len(symbols_set) if symbols_set else 1
    market_cov = len(market_symbols & symbols_set) / coverage_base
    text_cov = len(text_symbols & symbols_set) / coverage_base

    report = QualityReport(
        run_id=run_id,
        market_symbol_coverage=market_cov,
        text_symbol_coverage=text_cov,
        market_row_count=len(market_rows),
        text_row_count=len(text_rows),
        null_rate_by_field={
            **{f"market.{k}": v for k, v in _null_rate(market_rows).items()},
            **{f"text.{k}": v for k, v in _null_rate(text_rows).items()},
        },
        warnings=[],
        failures=[],
        passed=True,
    )

    if market_cov < min_symbol_coverage:
        report.failures.append(
            f"Market symbol coverage below threshold: {market_cov:.2%} < {min_symbol_coverage:.2%}"
        )
    if len(market_rows) == 0:
        report.failures.append("No market rows were produced")

    # Text is allowed to be sparse in prototype mode but should be visible.
    if text_cov < 0.5:
        report.warnings.append(f"Low text symbol coverage: {text_cov:.2%}")
    if len(text_rows) == 0:
        report.warnings.append("No text rows were produced")

    report.passed = len(report.failures) == 0
    return report
