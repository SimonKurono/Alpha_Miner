"""Stable tool interfaces for Feature 1 ingestion."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from alpha_miner.agents.data_ingestion.schemas import (
    MacroSeriesResponse,
    NewsRequest,
    NewsResponse,
    NormalizedMarketRow,
    PriceBatchRequest,
    PriceBatchResponse,
    SecFilingsRequest,
    SecFilingsResponse,
)
from alpha_miner.tools.macro.fred_provider import fetch_fred_series
from alpha_miner.tools.market.stooq_provider import fetch_stooq_prices
from alpha_miner.tools.text.gdelt_provider import fetch_gdelt_news
from alpha_miner.tools.text.sec_provider import fetch_latest_shares_outstanding, fetch_sec_filings
from alpha_miner.tools.validators.ingestion_quality import validate_ingestion_outputs

if TYPE_CHECKING:
    import pandas as pd  # pragma: no cover


def derive_market_features(
    price_df: Any,  # accepts DataFrame-like or list[dict]
    shares_df: Any,  # accepts mapping/simplified structure
) -> list[dict[str, Any]]:
    """Derive returns_1d/returns_5d and market_cap in a deterministic way.

    The function name keeps the DataFrame-oriented interface, but this
    implementation intentionally accepts generic structures to avoid hard
    dependency on pandas during local prototype development.
    """

    rows: list[dict[str, Any]]
    if isinstance(price_df, list):
        rows = [dict(r) for r in price_df]
    else:
        # Pandas-like fallback
        rows = price_df.to_dict(orient="records")

    shares_lookup: dict[str, float | None]
    if isinstance(shares_df, dict):
        shares_lookup = {str(k).upper(): (None if v is None else float(v)) for k, v in shares_df.items()}
    else:
        tmp_rows = shares_df.to_dict(orient="records")
        shares_lookup = {
            str(r.get("symbol", "")).upper(): (None if r.get("shares_outstanding") is None else float(r["shares_outstanding"]))
            for r in tmp_rows
        }

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        symbol = str(row["symbol"]).upper()
        grouped.setdefault(symbol, []).append(row)

    output: list[dict[str, Any]] = []
    for symbol, series in grouped.items():
        series.sort(key=lambda r: str(r["date"]))
        closes = [float(r["close"]) for r in series]
        shares = shares_lookup.get(symbol)

        for idx, row in enumerate(series):
            close = closes[idx]
            ret_1d = None
            ret_5d = None
            if idx >= 1 and closes[idx - 1] != 0:
                ret_1d = (close / closes[idx - 1]) - 1.0
            if idx >= 5 and closes[idx - 5] != 0:
                ret_5d = (close / closes[idx - 5]) - 1.0
            market_cap = (close * shares) if shares is not None else None

            normalized = NormalizedMarketRow(
                symbol=symbol,
                date=row["date"],
                close=close,
                volume=float(row["volume"]),
                returns_1d=ret_1d,
                returns_5d=ret_5d,
                market_cap=market_cap,
            )
            output.append(normalized.model_dump(mode="json"))

    output.sort(key=lambda r: (r["symbol"], r["date"]))
    return output


__all__ = [
    "fetch_stooq_prices",
    "fetch_fred_series",
    "fetch_sec_filings",
    "fetch_gdelt_news",
    "fetch_latest_shares_outstanding",
    "derive_market_features",
    "validate_ingestion_outputs",
    "PriceBatchRequest",
    "PriceBatchResponse",
    "SecFilingsRequest",
    "SecFilingsResponse",
    "NewsRequest",
    "NewsResponse",
    "MacroSeriesResponse",
]
