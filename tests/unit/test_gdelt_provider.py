from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from alpha_miner.agents.data_ingestion.schemas import NewsRequest
from alpha_miner.tools.text import gdelt_provider


def test_build_query_contains_symbol():
    query = gdelt_provider._build_query("AAPL")
    assert "AAPL" in query
    assert "lang:english" in query


def test_fetch_gdelt_news_dedupes(monkeypatch):
    payload = {
        "articles": [
            {
                "url": "https://example.com/1",
                "title": "AAPL rises",
                "seendate": "20240101T120000Z",
                "snippet": "Sample",
                "tone": "0.5",
            },
            {
                "url": "https://example.com/1",
                "title": "AAPL rises",
                "seendate": "20240101T120000Z",
                "snippet": "Sample",
                "tone": "0.5",
            },
        ]
    }

    monkeypatch.setattr(gdelt_provider, "_fetch_gdelt", lambda symbol, req, timeout=30: payload)

    req = NewsRequest(
        symbols=["AAPL"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
        max_docs_per_symbol=10,
    )
    resp = gdelt_provider.fetch_gdelt_news(req)

    assert resp.missing_symbols == []
    assert len(resp.documents) == 1
    assert resp.documents[0].url == "https://example.com/1"


def test_fetch_gdelt_news_rate_limit_short_circuit(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(symbol, req, timeout=30):
        calls["count"] += 1
        raise gdelt_provider.GdeltRateLimitError("429")

    monkeypatch.setattr(gdelt_provider, "_fetch_gdelt", fake_fetch)

    req = NewsRequest(
        symbols=["AAPL", "MSFT", "NVDA"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
        max_docs_per_symbol=10,
    )
    resp = gdelt_provider.fetch_gdelt_news(req)

    assert calls["count"] == 1
    assert sorted(resp.missing_symbols) == ["AAPL", "MSFT", "NVDA"]
    assert resp.documents == []


def test_fetch_gdelt_news_deadline_skips_all(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(symbol, req, timeout=30):
        calls["count"] += 1
        return {"articles": []}

    monkeypatch.setattr(gdelt_provider, "_fetch_gdelt", fake_fetch)
    req = NewsRequest(
        symbols=["AAPL", "MSFT"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
        max_docs_per_symbol=10,
    )
    past_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    resp = gdelt_provider.fetch_gdelt_news(req, deadline=past_deadline)

    assert calls["count"] == 0
    assert sorted(resp.missing_symbols) == ["AAPL", "MSFT"]
