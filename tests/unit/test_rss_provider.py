from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from alpha_miner.agents.data_ingestion.schemas import NewsRequest
from alpha_miner.tools.text import rss_provider


def test_fetch_rss_news_parses_and_filters_date(monkeypatch):
    payload = b"""
    <rss><channel>
      <item>
        <title>AAPL headline</title>
        <link>https://example.com/aapl1</link>
        <pubDate>Mon, 15 Jan 2024 10:30:00 GMT</pubDate>
        <description>Snippet</description>
      </item>
      <item>
        <title>Old headline</title>
        <link>https://example.com/old</link>
        <pubDate>Mon, 15 Jan 2018 10:30:00 GMT</pubDate>
        <description>Old</description>
      </item>
    </channel></rss>
    """

    monkeypatch.setattr(rss_provider, "_fetch_rss", lambda symbol, timeout=20: payload)

    req = NewsRequest(
        symbols=["AAPL"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        max_docs_per_symbol=10,
    )
    resp = rss_provider.fetch_rss_news(req, symbols=["AAPL"])

    assert len(resp.documents) == 1
    assert resp.documents[0].symbol == "AAPL"
    assert resp.documents[0].source == "rss"
    assert resp.missing_symbols == []


def test_fetch_rss_news_deadline_skips_symbols(monkeypatch):
    calls = {"count": 0}

    def fake_fetch(symbol, timeout=20):
        calls["count"] += 1
        return b"<rss><channel></channel></rss>"

    monkeypatch.setattr(rss_provider, "_fetch_rss", fake_fetch)

    req = NewsRequest(
        symbols=["AAPL", "MSFT"],
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
        max_docs_per_symbol=10,
    )
    past_deadline = datetime.now(timezone.utc) - timedelta(seconds=1)

    resp = rss_provider.fetch_rss_news(req, symbols=["AAPL", "MSFT"], deadline=past_deadline)

    assert calls["count"] == 0
    assert sorted(resp.missing_symbols) == ["AAPL", "MSFT"]
    assert resp.metadata.get("deadline_reached") is True
