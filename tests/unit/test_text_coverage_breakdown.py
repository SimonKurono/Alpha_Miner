from __future__ import annotations

from alpha_miner.agents.data_ingestion.text_agent import TextDataIngestionAgent


def test_text_coverage_breakdown_includes_rss_and_missing_reasons():
    breakdown = TextDataIngestionAgent.build_text_coverage_breakdown(
        symbols=["AAPL", "MSFT", "NVDA"],
        sec_rows=[{"symbol": "AAPL"}],
        gdelt_rows=[],
        rss_rows=[{"symbol": "MSFT"}],
        sec_missing=["MSFT", "NVDA"],
        gdelt_missing=["AAPL", "MSFT", "NVDA"],
        rss_missing=["NVDA"],
        gdelt_metadata={"rate_limited": True, "deadline_reached": False},
        rss_metadata={"deadline_reached": False},
    )

    assert breakdown["symbols_total"] == 3
    assert breakdown["symbols_with_any_text"] == 2
    assert breakdown["source_totals"]["rss_docs"] == 1

    nvda = [row for row in breakdown["symbol_rows"] if row["symbol"] == "NVDA"][0]
    assert "rss_missing" in nvda["missing_reasons"]
    assert "gdelt_rate_limited" in nvda["missing_reasons"]
