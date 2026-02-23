"""SEC EDGAR provider for 10-K/10-Q metadata and shares outstanding."""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from alpha_miner.agents.data_ingestion.schemas import FilingDocument, SecFilingsRequest, SecFilingsResponse
from alpha_miner.tools.io_utils import write_json

logger = logging.getLogger(__name__)

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
DEFAULT_TIMEOUT = 30


class SecProviderError(RuntimeError):
    pass


def _sec_headers(user_agent: str | None = None) -> dict[str, str]:
    ua = user_agent or os.getenv("SEC_USER_AGENT") or "AlphaMinerPrototype/0.1 (contact:example@example.com)"
    return {
        "User-Agent": ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate",
    }


@retry(
    retry=retry_if_exception_type((requests.RequestException, SecProviderError)),
    wait=wait_exponential_jitter(initial=1, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def _get_json(url: str, headers: dict[str, str], timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise SecProviderError(f"Invalid JSON payload from {url}")
    return data


def get_ticker_cik_mapping(cache_path: str = "data/raw/ingestion/sec_ticker_map.json") -> dict[str, str]:
    """Return mapping from ticker -> zero-padded 10-digit CIK."""

    path = Path(cache_path)
    use_cache = False
    if path.exists():
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        use_cache = (datetime.now(timezone.utc) - mtime) < timedelta(days=1)

    payload: dict[str, Any]
    if use_cache:
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = _get_json(SEC_TICKERS_URL, headers=_sec_headers())
        write_json(path, payload)

    mapping: dict[str, str] = {}
    for _, item in payload.items():
        ticker = str(item.get("ticker", "")).upper().strip()
        cik = item.get("cik_str")
        if not ticker or cik is None:
            continue
        mapping[ticker] = str(cik).zfill(10)
    return mapping


def _iter_recent_filings(payload: dict[str, Any]) -> list[dict[str, str]]:
    recent = payload.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    primary_docs = recent.get("primaryDocument", [])

    rows: list[dict[str, str]] = []
    size = min(len(forms), len(accession_numbers), len(filing_dates))
    for idx in range(size):
        rows.append(
            {
                "form": forms[idx],
                "accession_number": accession_numbers[idx],
                "filing_date": filing_dates[idx],
                "report_date": report_dates[idx] if idx < len(report_dates) else "",
                "primary_document": primary_docs[idx] if idx < len(primary_docs) else "",
            }
        )
    return rows


def fetch_sec_filings(req: SecFilingsRequest, user_agent: str | None = None) -> SecFilingsResponse:
    mapping = get_ticker_cik_mapping()
    headers = _sec_headers(user_agent)

    def _in_requested_window(filing_date: date) -> bool:
        if req.anchor_mode == "run_window":
            if req.start_date and filing_date < req.start_date:
                return False
            if req.end_date and filing_date > req.end_date:
                return False
            if req.start_date or req.end_date:
                return True
        # Backward-compatible fallback.
        cutoff = date.today() - timedelta(days=req.lookback_days)
        return filing_date >= cutoff

    docs: list[FilingDocument] = []
    missing: list[str] = []

    for symbol in req.symbols:
        cik = mapping.get(symbol.upper())
        if not cik:
            missing.append(symbol)
            continue

        url = SEC_SUBMISSIONS_URL.format(cik=cik)
        try:
            payload = _get_json(url, headers=headers)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SEC submissions fetch failed for %s: %s", symbol, exc)
            missing.append(symbol)
            continue

        for row in _iter_recent_filings(payload):
            form = row["form"]
            if form not in req.filing_types:
                continue
            try:
                filing_date = datetime.strptime(row["filing_date"], "%Y-%m-%d").date()
            except ValueError:
                continue
            if not _in_requested_window(filing_date):
                continue

            accession = row["accession_number"]
            accession_clean = accession.replace("-", "")
            primary_doc = row.get("primary_document") or ""
            doc_url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_clean}/{primary_doc}"
            )

            report_date = None
            if row.get("report_date"):
                try:
                    report_date = datetime.strptime(row["report_date"], "%Y-%m-%d").date()
                except ValueError:
                    report_date = None

            docs.append(
                FilingDocument(
                    symbol=symbol.upper(),
                    cik=cik,
                    accession_number=accession,
                    filing_type=form,
                    filing_date=filing_date,
                    report_date=report_date,
                    primary_document=primary_doc or None,
                    source_url=doc_url,
                )
            )

    docs.sort(key=lambda d: (d.symbol, d.filing_date, d.accession_number))
    return SecFilingsResponse(documents=docs, missing_symbols=sorted(set(missing)), source="sec")


def _extract_latest_shares(company_facts: dict[str, Any]) -> float | None:
    # Preferred concept for market-cap approximation.
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    candidates = [
        us_gaap.get("CommonStockSharesOutstanding"),
        us_gaap.get("EntityCommonStockSharesOutstanding"),
    ]

    latest_value: tuple[date, float] | None = None
    for concept in candidates:
        if not concept:
            continue
        units = concept.get("units", {})
        entries = units.get("shares", [])
        for entry in entries:
            try:
                end_date = datetime.strptime(entry["end"], "%Y-%m-%d").date()
                value = float(entry["val"])
            except (KeyError, TypeError, ValueError):
                continue
            if latest_value is None or end_date > latest_value[0]:
                latest_value = (end_date, value)
    return latest_value[1] if latest_value else None


def fetch_latest_shares_outstanding(symbols: list[str], user_agent: str | None = None) -> dict[str, float | None]:
    mapping = get_ticker_cik_mapping()
    headers = _sec_headers(user_agent)
    output: dict[str, float | None] = {}

    for symbol in symbols:
        upper = symbol.upper()
        cik = mapping.get(upper)
        if not cik:
            output[upper] = None
            continue
        try:
            facts = _get_json(SEC_COMPANY_FACTS_URL.format(cik=cik), headers=headers)
            output[upper] = _extract_latest_shares(facts)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Company facts fetch failed for %s: %s", upper, exc)
            output[upper] = None

    return output
