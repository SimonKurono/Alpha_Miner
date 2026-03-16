"""RSS news fallback provider for Feature 1 ingestion.

Uses free RSS feeds to improve symbol text coverage when GDELT is sparse
or rate-limited.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from alpha_miner.agents.data_ingestion.schemas import NewsDocument, NewsRequest, NewsResponse

logger = logging.getLogger(__name__)

RSS_QUERY_URL = "https://news.google.com/rss/search"
DEFAULT_TIMEOUT = 20


class RssPayloadError(RuntimeError):
    """Raised when RSS payload parsing fails."""


def _to_utc(raw: str) -> datetime:
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:  # noqa: BLE001
        return datetime.now(timezone.utc)


def _build_query(symbol: str) -> str:
    return f'{symbol} stock'


@retry(
    retry=retry_if_exception_type((requests.RequestException, RssPayloadError)),
    wait=wait_exponential_jitter(initial=0.5, max=4),
    stop=stop_after_attempt(2),
    reraise=True,
)
def _fetch_rss(symbol: str, timeout: int = DEFAULT_TIMEOUT) -> bytes:
    response = requests.get(
        RSS_QUERY_URL,
        params={
            "q": _build_query(symbol),
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.content


def _parse_items(payload: bytes) -> list[dict[str, Any]]:
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise RssPayloadError("Invalid RSS XML payload") from exc

    items: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "url": link,
                "published_at": _to_utc(pub_date),
                "snippet": desc or None,
            }
        )
    return items


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


def fetch_rss_news(req: NewsRequest, symbols: list[str], deadline: datetime | None = None) -> NewsResponse:
    all_docs: list[NewsDocument] = []
    missing_symbols: list[str] = []
    deadline_reached = False

    requested_symbols = [str(s).upper() for s in symbols if str(s).strip()]
    if not requested_symbols:
        return NewsResponse(documents=[], missing_symbols=[], source="rss", metadata={"deadline_reached": False})

    start_day = req.start_date
    end_day = req.end_date

    for idx, symbol in enumerate(requested_symbols):
        if deadline and datetime.now(timezone.utc) >= deadline:
            deadline_reached = True
            missing_symbols.extend(requested_symbols[idx:])
            logger.warning("RSS deadline reached at %s; skipping %d symbols", symbol, len(requested_symbols[idx:]))
            break

        timeout = DEFAULT_TIMEOUT
        if deadline:
            remaining = int((deadline - datetime.now(timezone.utc)).total_seconds())
            timeout = max(2, min(DEFAULT_TIMEOUT, remaining))

        try:
            payload = _fetch_rss(symbol, timeout=timeout)
            items = _parse_items(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS fetch failed for %s: %s", symbol, exc)
            missing_symbols.append(symbol)
            continue

        count = 0
        for item in items:
            published_at = item["published_at"]
            pub_day = published_at.date()
            if pub_day < start_day or pub_day > end_day:
                continue

            all_docs.append(
                NewsDocument(
                    symbol=symbol,
                    source="rss",
                    title=item["title"],
                    published_at=published_at,
                    url=item["url"],
                    snippet=item["snippet"],
                )
            )
            count += 1
            if count >= req.max_docs_per_symbol:
                break

        if count == 0:
            missing_symbols.append(symbol)

    deduped = _dedupe_news_documents(all_docs)
    return NewsResponse(
        documents=deduped,
        missing_symbols=sorted(set(missing_symbols)),
        source="rss",
        metadata={
            "deadline_reached": deadline_reached,
            "requested_symbols": len(requested_symbols),
            "document_count": len(deduped),
        },
    )
