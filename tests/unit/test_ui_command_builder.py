from __future__ import annotations

from datetime import date

from alpha_miner.ui.command_builder import build_stage_command, validate_stage_params


def test_feature1_command_builder_includes_essential_controls():
    module, args = build_stage_command(
        "feature1_ingestion",
        {
            "run_id": "f1_ui_test",
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "symbols": "AAPL,MSFT",
            "max_runtime_sec": 300,
            "risk_profile": "risk_neutral",
        },
    )
    assert module == "alpha_miner.pipelines.feature1_ingestion_cli"
    assert args == [
        "--run-id",
        "f1_ui_test",
        "--start-date",
        "2024-01-01",
        "--end-date",
        "2024-12-31",
        "--symbols",
        "AAPL,MSFT",
        "--max-runtime-sec",
        "300",
        "--risk-profile",
        "risk_neutral",
    ]


def test_feature3_command_builder_includes_upstream_run_ids():
    module, args = build_stage_command(
        "feature3_factor",
        {
            "ingestion_run_id": "f1_strict_s2_20260225",
            "hypothesis_run_id": "f2_strict_20260225",
            "target_factor_count": 10,
            "max_runtime_sec": 300,
        },
    )
    assert module == "alpha_miner.pipelines.feature3_factor_cli"
    assert "--ingestion-run-id" in args
    assert "f1_strict_s2_20260225" in args
    assert "--hypothesis-run-id" in args
    assert "f2_strict_20260225" in args


def test_validation_requires_stage_specific_fields():
    assert validate_stage_params("feature2_hypothesis", {"ingestion_run_id": ""}) == [
        "Missing required field: ingestion_run_id"
    ]


def test_feature2_command_builder_supports_gemini_options():
    module, args = build_stage_command(
        "feature2_hypothesis",
        {
            "run_id": "f2_ui_test",
            "ingestion_run_id": "f1_strict_s2_20260225",
            "model_policy": "gemini_with_search",
            "primary_model": "claude-3-5-sonnet-v2@20241022",
            "gemini_model": "gemini-2.5-flash",
            "enable_google_search_tool": True,
            "max_runtime_sec": 300,
        },
    )
    assert module == "alpha_miner.pipelines.feature2_hypothesis_cli"
    assert "--model-policy" in args
    assert "gemini_with_search" in args
    assert "--gemini-model" in args
    assert "gemini-2.5-flash" in args
    assert "--enable-google-search-tool" in args
