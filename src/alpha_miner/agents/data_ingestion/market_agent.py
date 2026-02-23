"""Market data ingestion custom agent."""

from __future__ import annotations

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.data_ingestion.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.data_ingestion.schemas import ErrorEvent, PriceBatchRequest, RunConfig
from alpha_miner.agents.data_ingestion.runtime_control import (
    append_budget_exceeded_error,
    get_run_meta,
    get_runtime_remaining_sec,
    is_runtime_exceeded,
)
from alpha_miner.tools.interfaces import derive_market_features, fetch_latest_shares_outstanding, fetch_stooq_prices
from alpha_miner.tools.io_utils import write_json, write_table_prefer_parquet


class MarketDataIngestionAgent(StatefulCustomAgent):
    """Fetches and normalizes market data for Feature 1."""

    async def _run_async_impl(self, ctx: InvocationContext):
        run_config = RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        run_meta = get_run_meta(ctx)
        errors = list(ctx.session.state.get("errors.ingestion", []))

        if is_runtime_exceeded(run_meta):
            errors = append_budget_exceeded_error(
                errors,
                source="market",
                message=(
                    "Runtime budget exceeded before market ingestion started. "
                    "Skipping market fetch and emitting empty artifact."
                ),
            )
            raw_path = write_json(
                f"data/raw/ingestion/{run_config.run_id}/market_stooq.json",
                {"source": "stooq", "missing_symbols": run_config.symbols, "records": []},
            )
            normalized_path = write_table_prefer_parquet(
                f"data/processed/ingestion/{run_config.run_id}/market_normalized",
                [],
            )
            existing_raw = dict(ctx.session.state.get("ingestion.market.raw", {}))
            existing_raw["stooq"] = raw_path
            yield self._state_event(
                ctx,
                {
                    "ingestion.market.raw": existing_raw,
                    "ingestion.market.normalized": normalized_path,
                    "errors.ingestion": errors,
                },
                text="MarketDataIngestionAgent skipped due to runtime budget cutoff",
            )
            return

        request = PriceBatchRequest(
            symbols=run_config.symbols,
            start_date=run_config.start_date,
            end_date=run_config.end_date,
            provider="stooq",
        )

        price_response = fetch_stooq_prices(request)
        shares_lookup = fetch_latest_shares_outstanding(run_config.symbols)

        price_rows = [record.model_dump(mode="json") for record in price_response.records]
        normalized_rows = derive_market_features(price_rows, shares_lookup)

        raw_path = write_json(
            f"data/raw/ingestion/{run_config.run_id}/market_stooq.json",
            {
                "source": "stooq",
                "missing_symbols": price_response.missing_symbols,
                "records": price_rows,
            },
        )
        normalized_path = write_table_prefer_parquet(
            f"data/processed/ingestion/{run_config.run_id}/market_normalized",
            normalized_rows,
        )

        if price_response.missing_symbols:
            errors.append(
                ErrorEvent(
                    source="stooq",
                    error_type="missing_symbols",
                    message=f"Missing symbols: {','.join(price_response.missing_symbols)}",
                    retry_count=3,
                    is_fatal=False,
                ).model_dump(mode="json")
            )

        existing_raw = dict(ctx.session.state.get("ingestion.market.raw", {}))
        existing_raw["stooq"] = raw_path

        delta = {
            "ingestion.market.raw": existing_raw,
            "ingestion.market.normalized": normalized_path,
            "errors.ingestion": errors,
        }

        yield self._state_event(
            ctx,
            delta,
            text=(
                f"MarketDataIngestionAgent completed rows={len(normalized_rows)} "
                f"missing={len(price_response.missing_symbols)} "
                f"remaining_runtime_sec={get_runtime_remaining_sec(run_meta):.1f}"
            ),
        )
