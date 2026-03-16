"""Command construction helpers for the Streamlit run launcher."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

STAGE_MODULES: dict[str, str] = {
    "feature1_ingestion": "alpha_miner.pipelines.feature1_ingestion_cli",
    "feature2_hypothesis": "alpha_miner.pipelines.feature2_hypothesis_cli",
    "feature3_factor": "alpha_miner.pipelines.feature3_factor_cli",
    "feature4_evaluation": "alpha_miner.pipelines.feature4_evaluation_cli",
    "feature5_report": "alpha_miner.pipelines.feature5_report_cli",
}


def validate_stage_params(stage: str, params: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    def _required(*keys: str) -> None:
        for key in keys:
            value = params.get(key)
            if value is None:
                errors.append(f"Missing required field: {key}")
                continue
            if isinstance(value, str) and not value.strip():
                errors.append(f"Missing required field: {key}")

    if stage == "feature1_ingestion":
        _required("start_date", "end_date", "symbols")
    elif stage == "feature2_hypothesis":
        _required("ingestion_run_id")
    elif stage == "feature3_factor":
        _required("ingestion_run_id", "hypothesis_run_id")
    elif stage == "feature4_evaluation":
        _required("ingestion_run_id", "factor_run_id")
    elif stage == "feature5_report":
        _required("ingestion_run_id", "factor_run_id", "evaluation_run_id")
    else:
        errors.append(f"Unsupported stage: {stage}")

    return errors


def build_stage_command(stage: str, params: Mapping[str, Any]) -> tuple[str, list[str]]:
    if stage not in STAGE_MODULES:
        raise ValueError(f"Unsupported stage: {stage}")

    args: list[str] = []

    def _append(flag: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if not value.strip():
                return
            args.extend([flag, value.strip()])
            return
        if isinstance(value, bool):
            if value:
                args.append(flag)
            return
        if isinstance(value, date):
            args.extend([flag, value.isoformat()])
            return
        args.extend([flag, str(value)])

    _append("--run-id", params.get("run_id"))

    if stage == "feature1_ingestion":
        _append("--start-date", params.get("start_date"))
        _append("--end-date", params.get("end_date"))
        _append("--symbols", params.get("symbols"))
        _append("--max-runtime-sec", params.get("max_runtime_sec"))
        _append("--risk-profile", params.get("risk_profile"))
    elif stage == "feature2_hypothesis":
        _append("--ingestion-run-id", params.get("ingestion_run_id"))
        _append("--model-policy", params.get("model_policy"))
        _append("--primary-model", params.get("primary_model"))
        _append("--gemini-model", params.get("gemini_model"))
        if params.get("enable_google_search_tool", True):
            args.append("--enable-google-search-tool")
        else:
            args.append("--disable-google-search-tool")
        _append("--max-runtime-sec", params.get("max_runtime_sec"))
    elif stage == "feature3_factor":
        _append("--ingestion-run-id", params.get("ingestion_run_id"))
        _append("--hypothesis-run-id", params.get("hypothesis_run_id"))
        _append("--target-factor-count", params.get("target_factor_count"))
        _append("--max-runtime-sec", params.get("max_runtime_sec"))
    elif stage == "feature4_evaluation":
        _append("--ingestion-run-id", params.get("ingestion_run_id"))
        _append("--factor-run-id", params.get("factor_run_id"))
        _append("--max-runtime-sec", params.get("max_runtime_sec"))
    elif stage == "feature5_report":
        _append("--ingestion-run-id", params.get("ingestion_run_id"))
        _append("--factor-run-id", params.get("factor_run_id"))
        _append("--evaluation-run-id", params.get("evaluation_run_id"))
        _append("--report-mode", params.get("report_mode"))
        _append("--factor-selection-policy", params.get("factor_selection_policy"))
        _append("--max-runtime-sec", params.get("max_runtime_sec"))

    return STAGE_MODULES[stage], args
