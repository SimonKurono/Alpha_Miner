"""Stooq market data provider for daily close/volume."""

from __future__ import annotations

import csv
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Iterable

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from alpha_miner.agents.data_ingestion.schemas import PriceBatchRequest, PriceBatchResponse, PriceRecord

logger = logging.getLogger(__name__)

STOOQ_BASE_URL = "https://stooq.com/q/d/l/"
DEFAULT_TIMEOUT = 30


class StooqError(RuntimeError):
    pass


@retry(
    retry=retry_if_exception_type((requests.RequestException, StooqError)),
    wait=wait_exponential_jitter(initial=1, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _fetch_symbol_csv(symbol: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    query_symbol = symbol.lower().replace(".", "-") + ".us"
    resp = requests.get(
        STOOQ_BASE_URL,
        params={"s": query_symbol, "i": "d"},
        timeout=timeout,
    )
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or "No data" in text:
        raise StooqError(f"No data returned for symbol={symbol}")
    return text


def _parse_stooq_csv(symbol: str, csv_text: str, start_date: date, end_date: date) -> list[PriceRecord]:
    rows: list[PriceRecord] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for item in reader:
        if not item.get("Date"):
            continue
        day = datetime.strptime(item["Date"], "%Y-%m-%d").date()
        if day < start_date or day > end_date:
            continue
        close_raw = item.get("Close")
        volume_raw = item.get("Volume")
        if not close_raw or not volume_raw:
            continue
        try:
            close = float(close_raw)
            volume = float(volume_raw)
        except ValueError:
            continue
        rows.append(
            PriceRecord(
                symbol=symbol,
                date=day,
                close=close,
                volume=volume,
            )
        )

    rows.sort(key=lambda r: (r.symbol, r.date))
    return rows


def fetch_stooq_prices(req: PriceBatchRequest, max_workers: int = 12) -> PriceBatchResponse:
    """Fetch close/volume for symbols and date range from Stooq."""

    records: list[PriceRecord] = []
    missing_symbols: list[str] = []

    def _load(symbol: str) -> tuple[str, list[PriceRecord]]:
        csv_text = _fetch_symbol_csv(symbol)
        parsed = _parse_stooq_csv(symbol, csv_text, req.start_date, req.end_date)
        if not parsed:
            raise StooqError(f"No in-range rows for symbol={symbol}")
        return symbol, parsed

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_load, symbol): symbol for symbol in req.symbols}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                _, rows = future.result()
                records.extend(rows)
            except Exception as exc:  # noqa: BLE001
                missing_symbols.append(symbol)
                logger.warning("Failed to fetch %s from stooq: %s", symbol, exc)

    # Dedupe and sort for deterministic output.
    dedup: dict[tuple[str, date], PriceRecord] = {(r.symbol, r.date): r for r in records}
    ordered = [dedup[k] for k in sorted(dedup)]
    return PriceBatchResponse(records=ordered, missing_symbols=sorted(set(missing_symbols)), source="stooq")


def records_to_rows(records: Iterable[PriceRecord]) -> list[dict]:
    return [record.model_dump(mode="json") for record in records]
