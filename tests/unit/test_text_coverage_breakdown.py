from __future__ import annotations

from alpha_miner.agents.data_ingestion.text_agent import TextDataIngestionAgent


def test_text_coverage_breakdown_counts_and_reasons():
    breakdown = TextDataIngestionAgent.build_text_coverage_breakdown(
        symbols=["AAPL", "MSFT", "NVDA"],
        sec_rows=[
            {"symbol": "AAPL"},
            {"symbol": "AAPL"},
        ],
        news_rows=[
            {"symbol": "MSFT"},
        ],
        sec_missing=["MSFT", "NVDA"],
        news_missing=["AAPL", "NVDA"],
    )

    assert breakdown["symbols_total"] == 3
    assert breakdown["symbols_with_any_text"] == 2
    assert breakdown["top_missing_reasons"]["no_text_docs"] == 1
    assert breakdown["top_missing_reasons"]["sec_missing"] == 2
    assert breakdown["top_missing_reasons"]["gdelt_missing"] == 2

