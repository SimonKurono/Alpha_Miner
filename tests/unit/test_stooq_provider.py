from __future__ import annotations

from datetime import date

from alpha_miner.agents.data_ingestion.schemas import PriceBatchRequest
from alpha_miner.tools.market import stooq_provider


SAMPLE_CSV = """Date,Open,High,Low,Close,Volume
2024-01-02,100,102,99,101,1000
2024-01-03,101,103,100,102,2000
2024-01-04,102,104,101,100,3000
"""


def test_fetch_stooq_prices_sorted_and_deduped(monkeypatch):
    def fake_fetch(symbol: str, timeout: int = 30):
        return SAMPLE_CSV

    monkeypatch.setattr(stooq_provider, "_fetch_symbol_csv", fake_fetch)

    req = PriceBatchRequest(
        symbols=["MSFT", "AAPL"],
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 4),
        provider="stooq",
    )

    response = stooq_provider.fetch_stooq_prices(req, max_workers=2)
    keys = [(r.symbol, r.date.isoformat()) for r in response.records]

    assert response.missing_symbols == []
    assert len(response.records) == 6
    assert keys == sorted(keys)
    assert len(set(keys)) == len(keys)


def test_parse_stooq_csv_filters_date_range():
    rows = stooq_provider._parse_stooq_csv(
        "AAPL",
        SAMPLE_CSV,
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 4),
    )

    assert len(rows) == 2
    assert rows[0].date == date(2024, 1, 3)
