from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from google.adk.runners import InMemoryRunner
from google.genai import types

from alpha_miner.agents.data_ingestion.schemas import (
    FilingDocument,
    NewsDocument,
    NewsResponse,
    PriceBatchResponse,
    PriceRecord,
    RunMeta,
    SecFilingsResponse,
)
from alpha_miner.agents.data_ingestion.workflow import build_root_ingestion_workflow
from alpha_miner.agents.data_ingestion import market_agent, text_agent


def test_feature1_e2e_small_universe(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    symbols = [f"SYM{i}" for i in range(10)]

    def fake_prices(req):
        records = []
        for symbol in req.symbols:
            records.extend(
                [
                    PriceRecord(symbol=symbol, date=date(2024, 1, 1), close=100.0, volume=1000),
                    PriceRecord(symbol=symbol, date=date(2024, 1, 2), close=101.0, volume=1200),
                ]
            )
        return PriceBatchResponse(records=records, missing_symbols=[])

    def fake_shares(symbols_list):
        return {s: 10.0 for s in symbols_list}

    seen_sec_req = {}

    def fake_sec(req):
        seen_sec_req["anchor_mode"] = req.anchor_mode
        seen_sec_req["start_date"] = req.start_date
        seen_sec_req["end_date"] = req.end_date
        docs = [
            FilingDocument(
                symbol=s,
                cik="0000000001",
                accession_number="0000000001-24-000001",
                filing_type="10-K",
                filing_date=date(2024, 1, 15),
                report_date=date(2023, 12, 31),
                primary_document="doc.htm",
                source_url="https://example.com/sec",
            )
            for s in req.symbols
        ]
        return SecFilingsResponse(documents=docs, missing_symbols=[])

    def fake_news(req, deadline=None):
        docs = [
            NewsDocument(
                symbol=s,
                source="gdelt",
                title=f"{s} headline",
                published_at=datetime(2024, 1, 20, tzinfo=timezone.utc),
                url=f"https://example.com/{s}",
                snippet="sample",
            )
            for s in req.symbols
        ]
        return NewsResponse(documents=docs, missing_symbols=[])

    monkeypatch.setattr(market_agent, "fetch_stooq_prices", fake_prices)
    monkeypatch.setattr(market_agent, "fetch_latest_shares_outstanding", fake_shares)
    monkeypatch.setattr(text_agent, "fetch_sec_filings", fake_sec)
    monkeypatch.setattr(text_agent, "fetch_gdelt_news", fake_news)

    async def _run():
        runner = InMemoryRunner(agent=build_root_ingestion_workflow(), app_name="test_feature1")
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s1",
        )
        async for _ in runner.run_async(
            user_id="u1",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="run")]),
            state_delta={
                "run.request": {
                    "run_id": "test_run",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "symbols": symbols,
                }
            },
        ):
            pass

        final_session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s1",
        )
        return final_session.state

    state = asyncio.run(_run())

    manifest_path = state.get("artifacts.ingestion.manifest")
    assert manifest_path is not None
    assert Path(manifest_path).exists()
    assert Path(state["ingestion.market.normalized"]).exists()
    assert Path(state["ingestion.text.normalized"]).exists()
    assert Path(state["ingestion.text.coverage_breakdown"]).exists()
    assert seen_sec_req["anchor_mode"] == "run_window"
    assert str(seen_sec_req["start_date"]) == "2024-01-01"
    assert str(seen_sec_req["end_date"]) == "2024-01-31"


def test_feature1_runtime_budget_cutoff_marks_failure(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    symbols = ["AAPL", "MSFT"]

    def fake_prices(req):
        return PriceBatchResponse(
            records=[
                PriceRecord(symbol="AAPL", date=date(2024, 1, 1), close=100.0, volume=1000),
                PriceRecord(symbol="MSFT", date=date(2024, 1, 1), close=200.0, volume=1000),
            ],
            missing_symbols=[],
        )

    def fake_shares(symbols_list):
        return {s: 10.0 for s in symbols_list}

    def fake_sec(req):
        return SecFilingsResponse(documents=[], missing_symbols=req.symbols)

    def fake_news(req, deadline=None):
        return NewsResponse(documents=[], missing_symbols=req.symbols)

    # Force text agent runtime guard to trip immediately.
    def expired_run_meta(_ctx):
        return RunMeta(
            run_id="test_runtime_cutoff",
            status="running",
            started_at=datetime.now(timezone.utc) - timedelta(hours=1),
            runtime_budget_sec=300,
        )

    monkeypatch.setattr(market_agent, "fetch_stooq_prices", fake_prices)
    monkeypatch.setattr(market_agent, "fetch_latest_shares_outstanding", fake_shares)
    monkeypatch.setattr(text_agent, "fetch_sec_filings", fake_sec)
    monkeypatch.setattr(text_agent, "fetch_gdelt_news", fake_news)
    monkeypatch.setattr(text_agent, "get_run_meta", expired_run_meta)

    async def _run():
        runner = InMemoryRunner(agent=build_root_ingestion_workflow(), app_name="test_feature1_runtime")
        session = await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s2",
        )
        async for _ in runner.run_async(
            user_id="u1",
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text="run")]),
            state_delta={
                "run.request": {
                    "run_id": "test_runtime_cutoff",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "symbols": symbols,
                }
            },
        ):
            pass
        final_session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id="u1",
            session_id="s2",
        )
        return final_session.state

    state = asyncio.run(_run())
    assert state["ingestion.quality"]["passed"] is False
    assert any("Runtime budget exceeded events detected" in msg for msg in state["ingestion.quality"]["failures"])
