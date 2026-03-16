"""Loads ingestion + factor artifacts for Feature 4 evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from google.adk.agents.invocation_context import InvocationContext

from alpha_miner.agents.evaluation.base_custom_agent import StatefulCustomAgent
from alpha_miner.agents.evaluation.schemas import ErrorEvent, Feature4RunConfig
from alpha_miner.tools.backtesting.dsl_executor import filter_rows_by_date
from alpha_miner.tools.io_utils import read_jsonl


def _read_json(path: str | Path) -> dict:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing artifact: {target}")
    with target.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_table(path: str | Path) -> list[dict]:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Missing table artifact: {target}")

    if target.suffix == ".jsonl":
        return read_jsonl(target)

    if target.suffix == ".parquet":
        try:
            import pandas as pd  # type: ignore

            return pd.read_parquet(target).to_dict(orient="records")
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Could not read parquet artifact: {target}") from exc

    raise ValueError(f"Unsupported table extension: {target.suffix}")


class EvalArtifactLoaderAgent(StatefulCustomAgent):
    async def _run_async_impl(self, ctx: InvocationContext):
        if bool(ctx.session.state.get("run.control.stop", False)):
            yield self._state_event(ctx, {}, text="EvalArtifactLoaderAgent skipped due to run stop flag")
            return

        run_config = Feature4RunConfig.model_validate(ctx.session.state.get("run.config", {}))
        errors = list(ctx.session.state.get("errors.evaluation", []))

        ingestion_manifest_path = f"artifacts/{run_config.ingestion_run_id}/ingestion_manifest.json"
        factor_manifest_path = f"artifacts/{run_config.factor_run_id}/factor_manifest.json"

        try:
            ingestion_manifest = _read_json(ingestion_manifest_path)
            market_rows = _read_table(ingestion_manifest["market_path"])

            factor_manifest = _read_json(factor_manifest_path)
            factors_payload = _read_json(factor_manifest["factors_path"])
            validation_payload = _read_json(factor_manifest["validation_path"])

            dsl_valid_ids = {
                str(row.get("factor_id"))
                for row in validation_payload.get("rows", [])
                if row.get("stage") == "dsl_validation" and bool(row.get("passed", False))
            }

            candidates = [
                row
                for row in factors_payload.get("candidates", [])
                if str(row.get("factor_id")) in dsl_valid_ids
            ]
            if not candidates:
                raise ValueError("No DSL-valid factors available for evaluation")

            market_rows = filter_rows_by_date(market_rows, run_config.start_date, run_config.end_date)
            if not market_rows:
                raise ValueError("No market rows remain after date filtering")

        except Exception as exc:  # noqa: BLE001
            errors.append(
                ErrorEvent(
                    source="artifact_loader",
                    error_type="missing_or_invalid_artifact",
                    message=str(exc),
                    is_fatal=True,
                ).model_dump(mode="json")
            )
            yield self._state_event(
                ctx,
                {
                    "errors.evaluation": errors,
                    "run.control.stop": True,
                },
                text=f"EvalArtifactLoaderAgent failed: {exc}",
            )
            return

        yield self._state_event(
            ctx,
            {
                "inputs.market": market_rows,
                "inputs.factors": candidates,
                "inputs.ingestion.manifest": ingestion_manifest,
                "inputs.factor.manifest": factor_manifest,
                "errors.evaluation": errors,
            },
            text=f"EvalArtifactLoaderAgent loaded market_rows={len(market_rows)} factors={len(candidates)}",
        )
