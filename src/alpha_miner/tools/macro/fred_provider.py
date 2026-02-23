"""FRED macro series provider."""

from __future__ import annotations

import os
from datetime import date, datetime

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from alpha_miner.agents.data_ingestion.schemas import MacroPoint, MacroSeriesResponse

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_TIMEOUT = 30


@retry(
    retry=retry_if_exception_type(requests.RequestException),
    wait=wait_exponential_jitter(initial=1, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def fetch_fred_series(series_id: str, start_date: date, end_date: date) -> MacroSeriesResponse:
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY is required for FRED requests")

    resp = requests.get(
        FRED_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": start_date.isoformat(),
            "observation_end": end_date.isoformat(),
        },
        timeout=DEFAULT_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    points: list[MacroPoint] = []
    for obs in payload.get("observations", []):
        value = obs.get("value")
        if value in (None, "."):
            continue
        try:
            parsed_date = datetime.strptime(obs["date"], "%Y-%m-%d").date()
            parsed_value = float(value)
        except (ValueError, TypeError, KeyError):
            continue
        points.append(MacroPoint(date=parsed_date, value=parsed_value))

    return MacroSeriesResponse(series_id=series_id, points=points, source="fred")
