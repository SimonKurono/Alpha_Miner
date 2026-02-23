from __future__ import annotations

from alpha_miner.agents.data_ingestion.schemas import SecFilingsRequest
from alpha_miner.tools.text import sec_provider


def test_sec_headers_do_not_force_host():
    headers = sec_provider._sec_headers("AlphaMinerPrototype/0.1 (contact:test@example.com)")
    assert headers["User-Agent"].startswith("AlphaMinerPrototype/0.1")
    assert "Host" not in headers


def test_get_ticker_cik_mapping_from_payload(monkeypatch, tmp_path):
    payload = {
        "0": {"ticker": "AAPL", "cik_str": 320193},
        "1": {"ticker": "MSFT", "cik_str": 789019},
    }

    monkeypatch.setattr(sec_provider, "_get_json", lambda url, headers, timeout=30: payload)
    cache_file = tmp_path / "tickers.json"

    mapping = sec_provider.get_ticker_cik_mapping(cache_path=str(cache_file))

    assert mapping["AAPL"] == "0000320193"
    assert mapping["MSFT"] == "0000789019"


def test_fetch_sec_filings_parses_recent(monkeypatch):
    ticker_payload = {
        "0": {"ticker": "AAPL", "cik_str": 320193},
    }
    submissions_payload = {
        "filings": {
            "recent": {
                "form": ["10-K", "8-K"],
                "accessionNumber": ["0000320193-24-000010", "0000320193-24-000011"],
                "filingDate": ["2024-02-01", "2024-02-10"],
                "reportDate": ["2023-12-31", "2024-01-31"],
                "primaryDocument": ["aapl10k.htm", "aapl8k.htm"],
            }
        }
    }

    def fake_get_json(url: str, headers: dict, timeout: int = 30):
        if "company_tickers" in url:
            return ticker_payload
        return submissions_payload

    monkeypatch.setattr(sec_provider, "_get_json", fake_get_json)

    req = SecFilingsRequest(symbols=["AAPL"], filing_types=["10-K", "10-Q"], lookback_days=3650)
    resp = sec_provider.fetch_sec_filings(req)

    assert resp.missing_symbols == []
    assert len(resp.documents) == 1
    doc = resp.documents[0]
    assert doc.filing_type == "10-K"
    assert doc.symbol == "AAPL"
    assert "aapl10k.htm" in doc.source_url


def test_fetch_sec_filings_run_window_filters_dates(monkeypatch):
    ticker_payload = {"0": {"ticker": "AAPL", "cik_str": 320193}}
    submissions_payload = {
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q"],
                "accessionNumber": ["0000320193-20-000001", "0000320193-24-000010"],
                "filingDate": ["2020-02-01", "2024-02-01"],
                "reportDate": ["2019-12-31", "2023-12-31"],
                "primaryDocument": ["aapl20.htm", "aapl24.htm"],
            }
        }
    }

    def fake_get_json(url: str, headers: dict, timeout: int = 30):
        if "company_tickers" in url:
            return ticker_payload
        return submissions_payload

    monkeypatch.setattr(sec_provider, "_get_json", fake_get_json)

    req = SecFilingsRequest(
        symbols=["AAPL"],
        filing_types=["10-K", "10-Q"],
        start_date=sec_provider.date(2024, 1, 1),
        end_date=sec_provider.date(2024, 12, 31),
        anchor_mode="run_window",
        lookback_days=3650,
    )
    resp = sec_provider.fetch_sec_filings(req)

    assert len(resp.documents) == 1
    assert resp.documents[0].filing_date.isoformat() == "2024-02-01"


def test_fetch_sec_filings_lookback_mode_ignores_run_window(monkeypatch):
    ticker_payload = {"0": {"ticker": "AAPL", "cik_str": 320193}}
    submissions_payload = {
        "filings": {
            "recent": {
                "form": ["10-K"],
                "accessionNumber": ["0000320193-24-000010"],
                "filingDate": ["2024-02-01"],
                "reportDate": ["2023-12-31"],
                "primaryDocument": ["aapl24.htm"],
            }
        }
    }

    def fake_get_json(url: str, headers: dict, timeout: int = 30):
        if "company_tickers" in url:
            return ticker_payload
        return submissions_payload

    monkeypatch.setattr(sec_provider, "_get_json", fake_get_json)

    req = SecFilingsRequest(
        symbols=["AAPL"],
        filing_types=["10-K", "10-Q"],
        start_date=sec_provider.date(2020, 1, 1),
        end_date=sec_provider.date(2020, 12, 31),
        anchor_mode="lookback_from_today",
        lookback_days=3650,
    )
    resp = sec_provider.fetch_sec_filings(req)

    assert len(resp.documents) == 1
