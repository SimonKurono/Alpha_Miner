"""Text data ingestion custom agent."""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from typing import Any

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.config_loader import load_feature1_config
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
from alpha_miner.tools.interfaces import fetch_gdelt_news, fetch_rss_news, fetch_sec_filings
from alpha_miner.tools.io_utils import write_json, write_table_prefer_parquet


class TextDataIngestionAgent(StatefulCustomAgent):
    """Fetches SEC filings metadata + GDELT news + RSS fallback, then normalizes."""

    config_path: str = "configs/feature1_ingestion.yaml"
    gdelt_min_remaining_sec: int = 30
    rss_min_remaining_sec: int = 15

    @staticmethod
    def _dedupe_news_rows(rows: list[dict]) -> list[dict]:
        seen: set[tuple[str, str, str]] = set()
        deduped: list[dict] = []
        for row in rows:
            key = (
                str(row.get("source", "")),
                str(row.get("url", "")),
                str(row.get("published_at", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(row)
        deduped.sort(
            key=lambda d: (
                str(d.get("symbol", "")),
                str(d.get("published_at", "")),
                str(d.get("url", "")),
            )
        )
        return deduped

    @staticmethod
    def build_text_coverage_breakdown(
        symbols: list[str],
        sec_rows: list[dict],
        gdelt_rows: list[dict],
        rss_rows: list[dict],
        sec_missing: list[str],
        gdelt_missing: list[str],
        rss_missing: list[str],
        gdelt_metadata: dict[str, Any] | None = None,
        rss_metadata: dict[str, Any] | None = None,
    ) -> dict:
        upper_symbols = [str(s).upper() for s in symbols]
        sec_missing_set = {s.upper() for s in sec_missing}
        gdelt_missing_set = {s.upper() for s in gdelt_missing}
        rss_missing_set = {s.upper() for s in rss_missing}

        sec_counts: Counter[str] = Counter()
        gdelt_counts: Counter[str] = Counter()
        rss_counts: Counter[str] = Counter()

        for row in sec_rows:
            sec_counts[str(row.get("symbol", "")).upper()] += 1
        for row in gdelt_rows:
            gdelt_counts[str(row.get("symbol", "")).upper()] += 1
        for row in rss_rows:
            rss_counts[str(row.get("symbol", "")).upper()] += 1

        symbol_rows: list[dict] = []
        reason_counts: Counter[str] = Counter()
        symbols_with_any_text = 0

        gdelt_rate_limited = bool((gdelt_metadata or {}).get("rate_limited", False))
        gdelt_deadline_reached = bool((gdelt_metadata or {}).get("deadline_reached", False))
        rss_deadline_reached = bool((rss_metadata or {}).get("deadline_reached", False))

        for symbol in upper_symbols:
            sec_docs = int(sec_counts.get(symbol, 0))
            gdelt_docs = int(gdelt_counts.get(symbol, 0))
            rss_docs = int(rss_counts.get(symbol, 0))

            total_docs = sec_docs + gdelt_docs + rss_docs
            has_text = total_docs > 0
            if has_text:
                symbols_with_any_text += 1

            missing_reasons: list[str] = []
            if sec_docs == 0 and symbol in sec_missing_set:
                missing_reasons.append("sec_missing")
            if gdelt_docs == 0 and symbol in gdelt_missing_set:
                missing_reasons.append("gdelt_missing")
                if gdelt_rate_limited:
                    missing_reasons.append("gdelt_rate_limited")
                if gdelt_deadline_reached:
                    missing_reasons.append("gdelt_skipped_deadline")
            if rss_docs == 0 and symbol in rss_missing_set:
                missing_reasons.append("rss_missing")
                if rss_deadline_reached:
                    missing_reasons.append("rss_skipped_deadline")

            if not has_text:
                missing_reasons.append("no_text_docs")

            for reason in missing_reasons:
                reason_counts[reason] += 1

            symbol_rows.append(
                {
                    "symbol": symbol,
                    "sec_docs": sec_docs,
                    "gdelt_docs": gdelt_docs,
                    "rss_docs": rss_docs,
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
            "source_totals": {
                "sec_docs": len(sec_rows),
                "gdelt_docs": len(gdelt_rows),
                "rss_docs": len(rss_rows),
            },
            "provider_metadata": {
                "gdelt": gdelt_metadata or {},
                "rss": rss_metadata or {},
            },
        }

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = get_run_meta(ctx)
        deadline = get_runtime_deadline(run_meta)
        errors = list(ctx.session.state.get("errors.ingestion", []))

        config = load_feature1_config(self.config_path)
        text_cfg = config.get("providers", {}).get("text", {})
        news_cfg = text_cfg.get("news", {})
        fallback_cfg = news_cfg.get("fallback", {})

        rss_enabled = bool(fallback_cfg.get("enabled", True))
        rss_max_docs_per_symbol = int(fallback_cfg.get("max_docs_per_symbol", 20))
        rss_min_remaining_sec = int(fallback_cfg.get("min_remaining_sec", self.rss_min_remaining_sec))

        sec_req = SecFilingsRequest(
            symbols=run_config.symbols,
            filing_types=["10-K", "10-Q"],
            lookback_days=365,
            start_date=run_config.start_date,
            end_date=run_config.end_date,
            anchor_mode="run_window",
        )
        gdelt_req = NewsRequest(
            symbols=run_config.symbols,
            start_date=run_config.start_date,
            end_date=run_config.end_date,
            max_docs_per_symbol=int(news_cfg.get("max_docs_per_symbol", 50)),
        )

        sec_rows: list[dict] = []
        gdelt_rows: list[dict] = []
        rss_rows: list[dict] = []

        sec_missing: list[str] = []
        gdelt_missing: list[str] = []
        rss_missing: list[str] = []

        gdelt_metadata: dict[str, Any] = {}
        rss_metadata: dict[str, Any] = {}

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="text",
                message=(
                    "Runtime budget exceeded before text ingestion started. "
                    "Skipping SEC/GDELT/RSS fetch and emitting empty artifact."
                ),
            )
            sec_missing = list(run_config.symbols)
            gdelt_missing = list(run_config.symbols)
            rss_missing = list(run_config.symbols)
        else:
            sec_response = fetch_sec_filings(sec_req)
            sec_rows = [doc.model_dump(mode="json") for doc in sec_response.documents]
            sec_missing = list(sec_response.missing_symbols)

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
                gdelt_response = NewsResponse(
                    documents=[],
                    missing_symbols=list(run_config.symbols),
                    source="gdelt",
                    metadata={"skipped_runtime": True, "rate_limited": False, "deadline_reached": False},
                )
            else:
                gdelt_response = fetch_gdelt_news(gdelt_req, deadline=deadline - timedelta(seconds=5))

            gdelt_rows = [doc.model_dump(mode="json") for doc in gdelt_response.documents]
            gdelt_missing = list(gdelt_response.missing_symbols)
            gdelt_metadata = dict(gdelt_response.metadata)

            unresolved_symbols = sorted({str(s).upper() for s in gdelt_missing})
            if unresolved_symbols and rss_enabled:
                remaining_after_gdelt = get_runtime_remaining_sec(run_meta)
                if remaining_after_gdelt <= rss_min_remaining_sec:
                    errors = append_budget_exceeded_error(
                        errors,
                        source="rss",
                        message=(
                            "Skipped RSS fallback because remaining runtime after GDELT "
                            f"was {remaining_after_gdelt:.1f}s "
                            f"(threshold={rss_min_remaining_sec}s)."
                        ),
                    )
                    rss_missing = unresolved_symbols
                    rss_metadata = {"skipped_runtime": True, "deadline_reached": False}
                else:
                    rss_req = NewsRequest(
                        symbols=unresolved_symbols,
                        start_date=run_config.start_date,
                        end_date=run_config.end_date,
                        max_docs_per_symbol=rss_max_docs_per_symbol,
                    )
                    try:
                        rss_response = fetch_rss_news(rss_req, symbols=unresolved_symbols, deadline=deadline - timedelta(seconds=3))
                        rss_rows = [doc.model_dump(mode="json") for doc in rss_response.documents]
                        rss_missing = list(rss_response.missing_symbols)
                        rss_metadata = dict(rss_response.metadata)
                    except Exception as exc:  # noqa: BLE001
                        rss_missing = unresolved_symbols
                        rss_metadata = {"provider_error": str(exc)}
                        errors.append(
                            ErrorEvent(
                                source="rss",
                                error_type="provider_error",
                                message=str(exc),
                                retry_count=2,
                                is_fatal=False,
                            ).model_dump(mode="json")
                        )
            elif unresolved_symbols:
                rss_missing = unresolved_symbols
                rss_metadata = {"fallback_disabled": True}

        combined_news_rows = self._dedupe_news_rows(gdelt_rows + rss_rows)
        rss_symbols_with_docs = {str(row.get("symbol", "")).upper() for row in rss_rows}
        if rss_enabled:
            news_missing = sorted({s.upper() for s in gdelt_missing if s.upper() not in rss_symbols_with_docs})
        else:
            news_missing = sorted({s.upper() for s in gdelt_missing})

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
        for row in combined_news_rows:
            normalized_rows.append(
                {
                    "symbol": row["symbol"],
                    "doc_type": "news",
                    "date": str(row["published_at"])[:10],
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
                "metadata": gdelt_metadata,
                "missing_symbols": gdelt_missing,
                "documents": gdelt_rows,
            },
        )
        raw_rss_path = write_json(
            f"data/raw/ingestion/{run_config.run_id}/text_rss_news.json",
            {
                "source": "rss",
                "metadata": rss_metadata,
                "missing_symbols": rss_missing,
                "documents": rss_rows,
            },
        )

        normalized_path = write_table_prefer_parquet(
            f"data/processed/ingestion/{run_config.run_id}/text_normalized",
            normalized_rows,
        )
        coverage_breakdown = self.build_text_coverage_breakdown(
            symbols=run_config.symbols,
            sec_rows=sec_rows,
            gdelt_rows=gdelt_rows,
            rss_rows=rss_rows,
            sec_missing=sec_missing,
            gdelt_missing=gdelt_missing,
            rss_missing=rss_missing,
            gdelt_metadata=gdelt_metadata,
            rss_metadata=rss_metadata,
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
                    message=f"Missing symbols: {','.join(sorted(set(sec_missing)))}",
                    retry_count=3,
                    is_fatal=False,
                ).model_dump(mode="json")
            )
        if gdelt_missing:
            errors.append(
                ErrorEvent(
                    source="gdelt",
                    error_type="missing_symbols",
                    message=f"Missing symbols: {','.join(sorted(set(gdelt_missing)))}",
                    retry_count=3,
                    is_fatal=False,
                ).model_dump(mode="json")
            )
        if rss_enabled and rss_missing:
            errors.append(
                ErrorEvent(
                    source="rss",
                    error_type="missing_symbols",
                    message=f"Missing symbols: {','.join(sorted(set(rss_missing)))}",
                    retry_count=2,
                    is_fatal=False,
                ).model_dump(mode="json")
            )

        existing_raw = dict(ctx.session.state.get("ingestion.text.raw", {}))
        existing_raw["sec"] = raw_sec_path
        existing_raw["gdelt"] = raw_gdelt_path
        existing_raw["rss"] = raw_rss_path
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
                f"sec_missing={len(sec_missing)} gdelt_missing={len(gdelt_missing)} rss_missing={len(rss_missing)} "
                f"text_symbols={coverage_breakdown['symbols_with_any_text']}/{coverage_breakdown['symbols_total']} "
                f"remaining_runtime_sec={get_runtime_remaining_sec(run_meta):.1f}"
            ),
        )
