from __future__ import annotations

from alpha_miner.tools.io_utils import write_jsonl
from alpha_miner.tools.validators.ingestion_quality import validate_ingestion_outputs


def test_quality_gate_fails_under_coverage(tmp_path):
    market_path = tmp_path / "market.jsonl"
    text_path = tmp_path / "text.jsonl"

    write_jsonl(
        market_path,
        [
            {"symbol": "AAPL", "date": "2024-01-01", "close": 100, "volume": 1000},
            {"symbol": "AAPL", "date": "2024-01-02", "close": 101, "volume": 1100},
        ],
    )
    write_jsonl(
        text_path,
        [
            {"symbol": "AAPL", "doc_type": "news", "date": "2024-01-01", "title": "x", "source": "gdelt", "url": "u"}
        ],
    )

    report = validate_ingestion_outputs(
        market_path=str(market_path),
        text_path=str(text_path),
        run_id="run1",
        symbols=["AAPL", "MSFT", "NVDA"],
        min_symbol_coverage=0.85,
    )

    assert report.passed is False
    assert any("coverage" in failure.lower() for failure in report.failures)


def test_quality_gate_passes_when_coverage_sufficient(tmp_path):
    market_path = tmp_path / "market.jsonl"
    text_path = tmp_path / "text.jsonl"

    write_jsonl(
        market_path,
        [
            {"symbol": "AAPL", "date": "2024-01-01", "close": 100, "volume": 1000},
            {"symbol": "MSFT", "date": "2024-01-01", "close": 200, "volume": 2000},
            {"symbol": "NVDA", "date": "2024-01-01", "close": 300, "volume": 3000},
        ],
    )
    write_jsonl(
        text_path,
        [
            {"symbol": "AAPL", "doc_type": "news", "date": "2024-01-01", "title": "x", "source": "gdelt", "url": "u"},
            {"symbol": "MSFT", "doc_type": "news", "date": "2024-01-01", "title": "x", "source": "gdelt", "url": "u2"},
        ],
    )

    report = validate_ingestion_outputs(
        market_path=str(market_path),
        text_path=str(text_path),
        run_id="run2",
        symbols=["AAPL", "MSFT", "NVDA"],
        min_symbol_coverage=0.85,
    )

    assert report.passed is True
    assert report.market_symbol_coverage == 1.0
