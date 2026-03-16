"""Deterministic markdown rendering for Feature 5 research notes."""

from __future__ import annotations

import json


def _fmt(v: float) -> str:
    return f"{float(v):.4f}"


def _factor_table_rows(selected_factors: list[dict]) -> list[str]:
    rows: list[str] = []
    for row in selected_factors:
        risk_tags = ",".join(row.get("risk_tags", [])) if row.get("risk_tags") else "-"
        rows.append(
            "| {factor_id} | `{expr}` | {promoted} | {sharpe} | {ir} | {ic} | {turnover} | {oos} | {decay} | {comp} | {risk} |".format(
                factor_id=row.get("factor_id", ""),
                expr=row.get("expression", ""),
                promoted="yes" if row.get("promoted", False) else "no",
                sharpe=_fmt(row.get("sharpe", 0.0)),
                ir=_fmt(row.get("information_ratio", 0.0)),
                ic=_fmt(row.get("ic_mean", 0.0)),
                turnover=_fmt(row.get("turnover_monthly_max", 0.0)),
                oos=_fmt(row.get("oos_score", 0.0)),
                decay=_fmt(row.get("decay_score", 0.0)),
                comp=_fmt(row.get("composite_score", 0.0)),
                risk=risk_tags,
            )
        )
    return rows


def build_research_note_markdown(payload: dict) -> str:
    selected_factors = list(payload.get("selected_factors", []))
    key_risks = list(payload.get("key_risks", []))
    appendix = dict(payload.get("appendix_metrics", {}))

    risk_lines = "\n".join(f"- {item}" for item in key_risks) if key_risks else "- None"
    factor_rows = _factor_table_rows(selected_factors)
    if not factor_rows:
        factor_rows = ["| - | - | - | - | - | - | - | - | - | - | - |"]

    md = [
        f"# {payload.get('title', 'Alpha Miner Research Note')}",
        "",
        f"- Run ID: `{payload.get('run_id', '')}`",
        f"- As of Date: `{payload.get('as_of_date', '')}`",
        "",
        "## Executive Summary",
        str(payload.get("executive_summary", "")),
        "",
        "## Methodology",
        str(payload.get("methodology", "")),
        "",
        "## Selected Factors",
        "| factor_id | expression | promoted | sharpe | ir | ic_mean | turnover_monthly_max | oos_score | decay_score | composite_score | risk_tags |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    md.extend(factor_rows)

    md.extend(
        [
            "",
            "## Key Risks",
            risk_lines,
            "",
            "## Disclaimer",
            str(payload.get("disclaimer", "")),
            "",
            "## Appendix Metrics",
            "```json",
            json.dumps(appendix, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )

    return "\n".join(md)
