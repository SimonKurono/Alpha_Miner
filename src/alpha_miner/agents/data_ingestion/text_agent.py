"""Text data ingestion custom agent."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.schemas import (
    ErrorEvent,
    NewsRequest,
    NewsResponse,
    RunConfig,
    SecFilingsRequest,
)
from alpha_miner.agents.data_ingestion.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    get_runtime_deadline,
    get_runtime_remaining_sec,
    is_runtime_exceeded,
)
from alpha_miner.tools.interfaces import fetch_gdelt_news, fetch_sec_filings
from alpha_miner.tools.io_utils import write_json, write_table_prefer_parquet


class TextDataIngestionAgent(StatefulCustomAgent):
    """Fetches SEC filings metadata and GDELT news, then normalizes."""

    gdelt_min_remaining_sec: int = 30

    @staticmethod
    def build_text_coverage_breakdown(
        symbols: list[str],
        sec_rows: list[dict],
        news_rows: list[dict],
        sec_missing: list[str],
        news_missing: list[str],
    ) -> dict:
        upper_symbols = [str(s).upper() for s in symbols]
        sec_missing_set = {s.upper() for s in sec_missing}
        news_missing_set = {s.upper() for s in news_missing}

        sec_counts: Counter[str] = Counter()
        news_counts: Counter[str] = Counter()
        for row in sec_rows:
            sec_counts[str(row.get("symbol", "")).upper()] += 1
        for row in news_rows:
            news_counts[str(row.get("symbol", "")).upper()] += 1

        symbol_rows: list[dict] = []
        reason_counts: Counter[str] = Counter()
        symbols_with_any_text = 0

        for symbol in upper_symbols:
            sec_docs = int(sec_counts.get(symbol, 0))
            gdelt_docs = int(news_counts.get(symbol, 0))
            total_docs = sec_docs + gdelt_docs
            has_text = total_docs > 0
            if has_text:
                symbols_with_any_text += 1

            missing_reasons: list[str] = []
            if sec_docs == 0 and symbol in sec_missing_set:
                missing_reasons.append("sec_missing")
            if gdelt_docs == 0 and symbol in news_missing_set:
                missing_reasons.append("gdelt_missing")
            if not has_text:
                missing_reasons.append("no_text_docs")

            for reason in missing_reasons:
                reason_counts[reason] += 1

            symbol_rows.append(
                {
                    "symbol": symbol,
                    "sec_docs": sec_docs,
                    "gdelt_docs": gdelt_docs,
                    "total_docs": total_docs,
                    "has_text": has_text,
                    "missing_reasons": missing_reasons,
                }
            )

        return {
            "symbols_total": len(upper_symbols),
            "symbols_with_any_text": symbols_with_any_text,
            "symbol_rows": symbol_rows,
            "top_missing_reasons": dict(reason_counts.most_common()),
        }

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = get_run_meta(ctx)
        deadline = get_runtime_deadline(run_meta)
        errors = list(ctx.session.state.get("errors.ingestion", []))

        sec_req = SecFilingsRequest(
            symbols=run_config.symbols,
            filing_types=["10-K", "10-Q"],
            lookback_days=365,
            start_date=run_config.start_date,
            end_date=run_config.end_date,
            anchor_mode="run_window",
        )
        news_req = NewsRequest(
            symbols=run_config.symbols,
            start_date=run_config.start_date,
            end_date=run_config.end_date,
            max_docs_per_symbol=50,
        )

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="text",
                message=(
                    "Runtime budget exceeded before text ingestion started. "
                    "Skipping SEC and GDELT fetch and emitting empty artifact."
                ),
            )

            sec_rows: list[dict] = []
            news_rows: list[dict] = []
            sec_missing = list(run_config.symbols)
            news_missing = list(run_config.symbols)
        else:
            sec_response = fetch_sec_filings(sec_req)
            remaining_after_sec = get_runtime_remaining_sec(run_meta)
            if remaining_after_sec <= self.gdelt_min_remaining_sec:
                errors = append_budget_exceeded_error(
                    errors,
                    source="gdelt",
                    message=(
                        "Skipped GDELT fetch because remaining runtime after SEC "
                        f"ingestion was {remaining_after_sec:.1f}s "
                        f"(threshold={self.gdelt_min_remaining_sec}s)."
                    ),
                )
                news_response = NewsResponse(
                    documents=[],
                    missing_symbols=list(run_config.symbols),
                    source="gdelt",
                )
            else:
                news_response = fetch_gdelt_news(news_req, deadline=deadline - timedelta(seconds=5))

            sec_rows = [doc.model_dump(mode="json") for doc in sec_response.documents]
            news_rows = [doc.model_dump(mode="json") for doc in news_response.documents]
            sec_missing = list(sec_response.missing_symbols)
            news_missing = list(news_response.missing_symbols)

        normalized_rows: list[dict] = []
        for row in sec_rows:
            normalized_rows.append(
                {
                    "symbol": row["symbol"],
                    "doc_type": "sec_10kq",
                    "date": row["filing_date"],
                    "title": f"{row['filing_type']} filing",
                    "body": None,
                    "source": "sec",
                    "url": row["source_url"],
                }
            )
        for row in news_rows:
            normalized_rows.append(
                {
                    "symbol": row["symbol"],
                    "doc_type": "news",
                    "date": row["published_at"][:10],
                    "title": row["title"],
                    "body": row.get("snippet"),
                    "source": row["source"],
                    "url": row["url"],
                }
            )

        raw_sec_path = write_json(
            f"data/raw/ingestion/{run_config.run_id}/text_sec_filings.json",
            {
                "source": "sec",
                "missing_symbols": sec_missing,
                "documents": sec_rows,
            },
        )
        raw_gdelt_path = write_json(
            f"data/raw/ingestion/{run_config.run_id}/text_gdelt_news.json",
            {
                "source": "gdelt",
                "missing_symbols": news_missing,
                "documents": news_rows,
            },
        )
        normalized_path = write_table_prefer_parquet(
            f"data/processed/ingestion/{run_config.run_id}/text_normalized",
            normalized_rows,
        )
        coverage_breakdown = self.build_text_coverage_breakdown(
            symbols=run_config.symbols,
            sec_rows=sec_rows,
            news_rows=news_rows,
            sec_missing=sec_missing,
            news_missing=news_missing,
        )
        coverage_breakdown["run_id"] = run_config.run_id
        coverage_breakdown_path = write_json(
            f"artifacts/{run_config.run_id}/text_coverage_breakdown.json",
            coverage_breakdown,
        )

        if sec_missing:
            errors.append(
                ErrorEvent(
                    source="sec",
                    error_type="missing_symbols",
                    message=f"Missing symbols: {','.join(sec_missing)}",
                    retry_count=3,
                    is_fatal=False,
                ).model_dump(mode="json")
            )
        if news_missing:
            errors.append(
                ErrorEvent(
                    source="gdelt",
                    error_type="missing_symbols",
                    message=f"Missing symbols: {','.join(news_missing)}",
                    retry_count=3,
                    is_fatal=False,
                ).model_dump(mode="json")
            )

        existing_raw = dict(ctx.session.state.get("ingestion.text.raw", {}))
        existing_raw["sec"] = raw_sec_path
        existing_raw["gdelt"] = raw_gdelt_path
        existing_raw["coverage_breakdown"] = coverage_breakdown_path

        delta = {
            "ingestion.text.raw": existing_raw,
            "ingestion.text.normalized": normalized_path,
            "ingestion.text.coverage_breakdown": coverage_breakdown_path,
            "errors.ingestion": errors,
        }

        yield self._state_event(
            ctx,
            delta,
            text=(
                f"TextDataIngestionAgent completed rows={len(normalized_rows)} "
                f"sec_missing={len(sec_missing)} news_missing={len(news_missing)} "
                f"text_symbols={coverage_breakdown['symbols_with_any_text']}/{coverage_breakdown['symbols_total']} "
                f"remaining_runtime_sec={get_runtime_remaining_sec(run_meta):.1f}"
            ),
        )
