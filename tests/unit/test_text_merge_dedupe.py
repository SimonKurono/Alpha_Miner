from __future__ import annotations

from alpha_miner.agents.data_ingestion.text_agent import TextDataIngestionAgent


def test_text_merge_dedupe_stable_and_unique():
    rows = [
        {
            "symbol": "AAPL",
            "source": "gdelt",
            "url": "https://example.com/1",
            "published_at": "2024-01-15T12:00:00+00:00",
            "title": "A",
        },
        {
            "symbol": "AAPL",
            "source": "gdelt",
            "url": "https://example.com/1",
            "published_at": "2024-01-15T12:00:00+00:00",
            "title": "A duplicate",
        },
        {
            "symbol": "AAPL",
            "source": "rss",
            "url": "https://example.com/2",
            "published_at": "2024-01-16T12:00:00+00:00",
            "title": "B",
        },
    ]

    out = TextDataIngestionAgent._dedupe_news_rows(rows)

    assert len(out) == 2
    assert out[0]["url"] == "https://example.com/1"
    assert out[1]["url"] == "https://example.com/2"
