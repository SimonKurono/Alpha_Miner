"""GDELT doc API provider for news ingestion."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from alpha_miner.agents.data_ingestion.schemas import NewsDocument, NewsRequest, NewsResponse

logger = logging.getLogger(__name__)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
DEFAULT_TIMEOUT = 30


class GdeltRateLimitError(RuntimeError):
    """Raised when the API explicitly rate-limits the request."""


class GdeltPayloadError(RuntimeError):
    """Raised when the API response cannot be parsed as expected JSON."""


def _to_gdelt_dt(day: date, end_of_day: bool = False) -> str:
    if end_of_day:
        return day.strftime("%Y%m%d") + "235959"
    return day.strftime("%Y%m%d") + "000000"


def _build_query(symbol: str) -> str:
    # Keep query simple and deterministic for prototype speed.
    return f'("{symbol}" OR "{symbol} stock") lang:english'


@retry(
    retry=retry_if_exception_type((requests.RequestException, GdeltPayloadError)),
    wait=wait_exponential_jitter(initial=0.5, max=4),
    stop=stop_after_attempt(2),
    reraise=True,
)
def _fetch_gdelt(symbol: str, req: NewsRequest, timeout: int = DEFAULT_TIMEOUT) -> dict:
    response = requests.get(
        GDELT_DOC_URL,
        params={
            "query": _build_query(symbol),
            "mode": "ArtList",
            "format": "json",
            "startdatetime": _to_gdelt_dt(req.start_date),
            "enddatetime": _to_gdelt_dt(req.end_date, end_of_day=True),
            "maxrecords": req.max_docs_per_symbol,
            "sort": "datedesc",
        },
        timeout=timeout,
    )
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "")
        suffix = f" retry_after={retry_after}" if retry_after else ""
        raise GdeltRateLimitError(f"GDELT returned 429 for {symbol}.{suffix}")
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as exc:
        raise GdeltPayloadError(f"GDELT invalid JSON for {symbol}") from exc
    if not isinstance(payload, dict):
        raise GdeltPayloadError(f"GDELT non-dict payload for {symbol}")
    return payload


def _parse_published_at(raw: str) -> datetime:
    candidates = ["%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ"]
    for fmt in candidates:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def _dedupe_news_documents(docs: list[NewsDocument]) -> list[NewsDocument]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[NewsDocument] = []
    for doc in docs:
        key = (doc.source, doc.url, doc.published_at.isoformat())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(doc)
    deduped.sort(key=lambda d: (d.symbol, d.published_at, d.url))
    return deduped


def fetch_gdelt_news(req: NewsRequest, deadline: datetime | None = None) -> NewsResponse:
    all_docs: list[NewsDocument] = []
    missing_symbols: list[str] = []

    for idx, symbol in enumerate(req.symbols):
        if deadline and datetime.now(timezone.utc) >= deadline:
            # Stop early to preserve runtime budget for the overall run.
            missing_symbols.extend(req.symbols[idx:])
            logger.warning("GDELT deadline reached at %s; skipping %d symbols", symbol, len(req.symbols[idx:]))
            break

        timeout = DEFAULT_TIMEOUT
        if deadline:
            remaining = int((deadline - datetime.now(timezone.utc)).total_seconds())
            timeout = max(2, min(10, remaining))

        try:
            payload = _fetch_gdelt(symbol, req, timeout=timeout)
        except GdeltRateLimitError as exc:
            # Tight throttle response: avoid burning runtime retrying each symbol.
            remaining_symbols = req.symbols[idx:]
            missing_symbols.extend(remaining_symbols)
            logger.warning("GDELT rate-limited at %s; skipping %d symbols: %s", symbol, len(remaining_symbols), exc)
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("GDELT fetch failed for %s: %s", symbol, exc)
            missing_symbols.append(symbol)
            continue

        articles = payload.get("articles", []) or []
        if not articles:
            missing_symbols.append(symbol)
            continue

        for item in articles:
            url = item.get("url") or ""
            title = item.get("title") or ""
            if not url or not title:
                continue
            published_at = _parse_published_at(item.get("seendate") or item.get("date") or "")
            tone_value = item.get("tone")
            tone = None
            if tone_value not in (None, ""):
                try:
                    tone = float(tone_value)
                except (TypeError, ValueError):
                    tone = None
            all_docs.append(
                NewsDocument(
                    symbol=symbol.upper(),
                    source="gdelt",
                    title=title,
                    published_at=published_at,
                    url=url,
                    snippet=item.get("snippet"),
                    tone=tone,
                )
            )

    deduped = _dedupe_news_documents(all_docs)
    return NewsResponse(documents=deduped, missing_symbols=sorted(set(missing_symbols)), source="gdelt")
