"""Alpha Miner Streamlit UI for run control and artifact exploration.

Run with:
    PYTHONPATH=src streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

try:
    import altair as alt
except Exception:  # noqa: BLE001
    alt = None

from alpha_miner.ui.command_builder import STAGE_MODULES, build_stage_command, validate_stage_params
from alpha_miner.ui.run_index import load_run_index, write_run_index

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
RUN_INDEX_PATH = ARTIFACTS / "run_index.json"

STAGE_LABELS: dict[str, str] = {
    "feature1_ingestion": "Feature 1 Ingestion",
    "feature2_hypothesis": "Feature 2 Hypothesis",
    "feature3_factor": "Feature 3 Factors",
    "feature4_evaluation": "Feature 4 Evaluation",
    "feature5_report": "Feature 5 Report",
}

MANIFEST_BY_STAGE: dict[str, str] = {
    "feature1_ingestion": "ingestion_manifest.json",
    "feature2_hypothesis": "hypothesis_manifest.json",
    "feature3_factor": "factor_manifest.json",
    "feature4_evaluation": "evaluation_manifest.json",
    "feature5_report": "report_manifest.json",
}

RUN_TYPE_LABEL_TO_STAGE: dict[str, str] = {label: stage for stage, label in STAGE_LABELS.items()}
STAGE_TO_RUN_TYPE_LABEL: dict[str, str] = {stage: label for label, stage in RUN_TYPE_LABEL_TO_STAGE.items()}


def _inject_css() -> None:
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');
          :root {
            --bg-a: #f4efe1;
            --bg-b: #dbe8f8;
            --ink: #1c1f26;
            --card: rgba(255, 255, 255, 0.78);
            --accent: #0f766e;
            --accent-2: #b45309;
            --good: #166534;
            --warn: #a16207;
            --bad: #991b1b;
          }
          html, body, [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 8% 2%, var(--bg-b) 0%, var(--bg-a) 45%, #f7f2e9 100%);
            color: var(--ink);
            font-family: 'Space Grotesk', 'Trebuchet MS', sans-serif;
          }
          [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(255,255,255,0.72));
          }
          .am-card {
            background: var(--card);
            border: 1px solid rgba(17,24,39,0.08);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 10px;
            box-shadow: 0 3px 10px rgba(15, 23, 42, 0.06);
          }
          .am-kpi {
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--accent);
          }
          .am-label {
            font-size: 0.82rem;
            opacity: 0.75;
          }
          .am-story {
            background: rgba(255,255,255,0.62);
            border: 1px solid rgba(0,0,0,0.08);
            border-left: 4px solid var(--accent);
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 12px;
          }
          .am-chip {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            margin-right: 6px;
          }
          .am-chip-ok { background: rgba(22,163,74,0.15); color: var(--good); }
          .am-chip-partial { background: rgba(202,138,4,0.18); color: var(--warn); }
          .am-chip-bad { background: rgba(239,68,68,0.18); color: var(--bad); }
          .am-chip-unknown { background: rgba(100,116,139,0.18); color: #334155; }
          .stButton button {
            border-radius: 10px;
            border: 1px solid rgba(15,118,110,0.4);
            background: linear-gradient(120deg, #e6fffb 0%, #fff7ed 100%);
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi(col, label: str, value: str) -> None:
    col.markdown(
        f"<div class='am-card'><div class='am-kpi'>{value}</div><div class='am-label'>{label}</div></div>",
        unsafe_allow_html=True,
    )


def _status_chip(status: str) -> str:
    normalized = (status or "unknown").lower()
    mapping = {
        "success": ("SUCCESS", "am-chip-ok"),
        "partial_success": ("PARTIAL", "am-chip-partial"),
        "failed": ("FAILED", "am-chip-bad"),
        "ok": ("OK", "am-chip-ok"),
        "unknown": ("UNKNOWN", "am-chip-unknown"),
    }
    text, css = mapping.get(normalized, (normalized.upper(), "am-chip-unknown"))
    return f"<span class='am-chip {css}'>{text}</span>"


def _render_run_story(what_ran: str, what_happened: str, what_next: str) -> None:
    st.markdown(
        (
            "<div class='am-story'>"
            f"<b>What ran:</b> {what_ran}<br/>"
            f"<b>What happened:</b> {what_happened}<br/>"
            f"<b>What to do next:</b> {what_next}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _safe_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"Missing file: {path}"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Invalid JSON at {path}: {exc}"


def _safe_read_text(path: Path) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, f"Missing file: {path}"
    try:
        return path.read_text(encoding="utf-8"), None
    except Exception as exc:  # noqa: BLE001
        return None, f"Unable to read text file {path}: {exc}"


def _resolve_path(raw_path: str | None) -> Path:
    if not raw_path:
        return ROOT / "__missing__"
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return ROOT / candidate


def _list_run_ids(manifest_name: str) -> list[str]:
    if not ARTIFACTS.exists():
        return []
    run_ids: list[str] = []
    for child in sorted(ARTIFACTS.iterdir(), key=lambda p: p.name, reverse=True):
        if not child.is_dir():
            continue
        if (child / manifest_name).exists():
            run_ids.append(child.name)
    return run_ids


def _run_pipeline(module_name: str, args: list[str]) -> tuple[int, str, str, float]:
    env = os.environ.copy()
    current_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"src{os.pathsep}{current_path}" if current_path else "src"
    cmd = [sys.executable, "-m", module_name] + args
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - started
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def _extract_error_excerpt(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if "Traceback" in line:
            continue
        return line[:280]
    return ""


def _analyze_run_diagnostics(exit_code: int, stdout: str, stderr: str) -> dict[str, Any]:
    agent_health = {"status": "ok", "failure_reason": "", "remediation": ""}
    warnings: list[str] = []

    merged = "\n".join([stdout or "", stderr or ""])
    if "App name mismatch detected" in merged:
        agent_health = {
            "status": "failed",
            "failure_reason": "ADK reported app-name mismatch between runner and loaded root agent.",
            "remediation": "Re-run after confirming CLI uses runtime_utils.build_runner() and restart Streamlit.",
        }

    if "GDELT rate-limited" in merged:
        warnings.append("GDELT was rate-limited; text ingestion may be degraded.")
    if "deterministic fallback enabled" in merged:
        warnings.append("LLM fallback triggered; deterministic hypothesis path used.")

    run_status = "success"
    if exit_code != 0 or agent_health["status"] == "failed":
        run_status = "failed"
    elif warnings:
        run_status = "partial_success"

    if exit_code != 0 and not agent_health["failure_reason"]:
        agent_health = {
            "status": "failed",
            "failure_reason": _extract_error_excerpt(stderr or stdout) or "Pipeline execution failed.",
            "remediation": "Inspect stderr details and resolve provider/auth/config issues, then rerun.",
        }

    return {
        "run_status": run_status,
        "agent_health": agent_health,
        "warnings": warnings,
    }


def _manifest_health(manifest: dict[str, Any]) -> dict[str, Any]:
    paths: list[tuple[str, Path]] = []
    for key, value in manifest.items():
        if key.endswith("_path") and isinstance(value, str):
            paths.append((key, _resolve_path(value)))
        elif isinstance(value, dict):
            for inner_key, inner_value in value.items():
                if isinstance(inner_value, str) and ("path" in inner_key or "/" in inner_value or "." in inner_value):
                    paths.append((f"{key}.{inner_key}", _resolve_path(inner_value)))

    rows = [{"field": name, "path": str(path), "exists": path.exists()} for name, path in paths]
    missing = [row for row in rows if not row["exists"]]
    return {"checked": len(paths), "missing": missing, "rows": rows}


def _load_run_index_map() -> dict[tuple[str, str], dict[str, Any]]:
    payload = load_run_index(ARTIFACTS)
    mapping: dict[tuple[str, str], dict[str, Any]] = {}
    for row in payload.get("runs", []):
        run_id = str(row.get("run_id", ""))
        stage = str(row.get("stage", ""))
        if run_id and stage:
            mapping[(run_id, stage)] = row
    return mapping


def _choose_default(select_key: str, options: list[str], fallback: str | None = None) -> int:
    if not options:
        return 0
    preferred = st.session_state.get(select_key) or fallback
    if preferred and preferred in options:
        return options.index(preferred)
    return 0


def _seed_timeline_defaults(entry: dict[str, Any]) -> None:
    stage = str(entry.get("stage", ""))
    run_id = str(entry.get("run_id", ""))
    if not run_id or not stage:
        return
    run_type = STAGE_TO_RUN_TYPE_LABEL.get(stage)
    if run_type:
        st.session_state["monitor.run_type"] = run_type
        st.session_state["monitor.run_id"] = run_id

    lineage = entry.get("lineage", {}) or {}
    if stage == "feature3_factor":
        st.session_state["factor_library.factor_run_id"] = run_id
    if stage == "feature4_evaluation":
        st.session_state["dashboard.eval_run_id"] = run_id
        st.session_state["factor_library.eval_run_id"] = run_id
        factor_run_id = lineage.get("factor_run_id")
        if factor_run_id:
            st.session_state["factor_library.factor_run_id"] = factor_run_id
    if stage == "feature5_report":
        st.session_state["report_viewer.run_id"] = run_id
        eval_run_id = lineage.get("evaluation_run_id")
        if eval_run_id:
            st.session_state["dashboard.eval_run_id"] = eval_run_id
            st.session_state["factor_library.eval_run_id"] = eval_run_id


def _parse_summary_json_from_stdout(stdout: str) -> dict[str, Any]:
    block_match = re.search(r"\{(?:.|\n|\r)*\}\s*$", stdout.strip())
    if not block_match:
        return {}
    try:
        return json.loads(block_match.group(0))
    except Exception:  # noqa: BLE001
        return {}


def _run_feature2_preflight(params: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "").strip()
    rows.append(
        {
            "check": "GOOGLE_CLOUD_PROJECT",
            "status": "PASS" if project else "FAIL",
            "details": project or "missing",
        }
    )
    rows.append(
        {
            "check": "GOOGLE_CLOUD_LOCATION",
            "status": "PASS" if location else "FAIL",
            "details": location or "missing",
        }
    )

    try:
        import google.auth

        creds, _ = google.auth.default()
        rows.append(
            {
                "check": "ADC credentials",
                "status": "PASS" if creds else "FAIL",
                "details": type(creds).__name__ if creds else "not resolved",
            }
        )
    except Exception as exc:  # noqa: BLE001
        rows.append({"check": "ADC credentials", "status": "FAIL", "details": str(exc)})

    try:
        from google import genai
        from google.genai import types

        rows.append({"check": "google-genai import", "status": "PASS", "details": "available"})
        if project and location:
            client = genai.Client(vertexai=True, project=project, location=location)
            tools = []
            if bool(params.get("enable_google_search_tool", True)):
                tools = [types.Tool(googleSearch=types.GoogleSearch())]
            response = client.models.generate_content(
                model=str(params.get("gemini_model", "gemini-2.5-flash")),
                contents="Respond with the word ok.",
                config=types.GenerateContentConfig(maxOutputTokens=8, temperature=0.0, tools=tools),
            )
            text = str(getattr(response, "text", "") or "").strip()
            rows.append(
                {
                    "check": "Gemini dry run",
                    "status": "PASS" if text else "FAIL",
                    "details": text or "empty response",
                }
            )
    except Exception as exc:  # noqa: BLE001
        rows.append({"check": "Gemini dry run", "status": "FAIL", "details": str(exc)})

    return rows


def _render_artifact_integrity_table(health: dict[str, Any]) -> None:
    if not health["rows"]:
        st.info("No artifact paths detected in manifest.")
        return
    table = pd.DataFrame(health["rows"])
    st.dataframe(table, width="stretch", hide_index=True)


def _render_debug_json(title: str, payload: dict[str, Any]) -> None:
    with st.expander(f"Debug Details: {title}"):
        st.json(payload)


def _screen_create_run() -> None:
    st.subheader("Create Run")
    _render_run_story(
        "Choose a stage and run with essential controls.",
        "The UI validates required inputs and executes the selected CLI module.",
        "Use preflight first for Feature 2 Gemini mode, then run and inspect health summary.",
    )

    stage_options = list(STAGE_MODULES.keys())
    stage = st.selectbox("Pipeline Stage", stage_options, format_func=lambda x: STAGE_LABELS[x], key="create.stage")

    default_ingestion = _list_run_ids("ingestion_manifest.json")[0] if _list_run_ids("ingestion_manifest.json") else ""
    default_hypothesis = _list_run_ids("hypothesis_manifest.json")[0] if _list_run_ids("hypothesis_manifest.json") else ""
    default_factor = _list_run_ids("factor_manifest.json")[0] if _list_run_ids("factor_manifest.json") else ""
    default_eval = _list_run_ids("evaluation_manifest.json")[0] if _list_run_ids("evaluation_manifest.json") else ""

    params: dict[str, Any] = {}
    with st.form("create_run_form"):
        params["run_id"] = st.text_input("Run ID", value="")
        if stage == "feature1_ingestion":
            params["start_date"] = st.date_input("Start Date", value=date(2024, 1, 1))
            params["end_date"] = st.date_input("End Date", value=date(2024, 12, 31))
            params["symbols"] = st.text_input(
                "Symbols (comma-separated)",
                value="AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,UNH,BRK.B",
            )
            params["max_runtime_sec"] = st.number_input(
                "Max Runtime Sec", min_value=60, max_value=900, value=300, step=30
            )
            params["risk_profile"] = st.selectbox("Risk Profile", ["risk_neutral", "risk_averse"], index=0)
        elif stage == "feature2_hypothesis":
            params["ingestion_run_id"] = st.text_input("Ingestion Run ID", value=default_ingestion)
            params["model_policy"] = st.selectbox(
                "Model Policy",
                ["gemini_with_search", "gemini_only", "deterministic_only", "claude_with_fallback", "claude_only"],
                index=0,
            )
            params["gemini_model"] = st.text_input("Gemini Model", value="gemini-2.5-flash")
            params["primary_model"] = st.text_input("Claude Model", value="claude-3-5-sonnet-v2@20241022")
            params["enable_google_search_tool"] = st.checkbox("Enable Google Search Tool", value=True)
            params["max_runtime_sec"] = st.number_input(
                "Max Runtime Sec", min_value=60, max_value=900, value=300, step=30
            )
        elif stage == "feature3_factor":
            params["ingestion_run_id"] = st.text_input("Ingestion Run ID", value=default_ingestion)
            params["hypothesis_run_id"] = st.text_input("Hypothesis Run ID", value=default_hypothesis)
            params["target_factor_count"] = st.number_input(
                "Target Factor Count", min_value=1, max_value=50, value=10, step=1
            )
            params["max_runtime_sec"] = st.number_input(
                "Max Runtime Sec", min_value=60, max_value=900, value=300, step=30
            )
        elif stage == "feature4_evaluation":
            params["ingestion_run_id"] = st.text_input("Ingestion Run ID", value=default_ingestion)
            params["factor_run_id"] = st.text_input("Factor Run ID", value=default_factor)
            params["max_runtime_sec"] = st.number_input(
                "Max Runtime Sec", min_value=60, max_value=900, value=300, step=30
            )
        elif stage == "feature5_report":
            params["ingestion_run_id"] = st.text_input("Ingestion Run ID", value=default_ingestion)
            params["factor_run_id"] = st.text_input("Factor Run ID", value=default_factor)
            params["evaluation_run_id"] = st.text_input("Evaluation Run ID", value=default_eval)
            params["report_mode"] = st.selectbox(
                "Report Mode",
                ["deterministic_first", "deterministic_only", "llm_first"],
                index=0,
            )
            params["factor_selection_policy"] = st.selectbox(
                "Factor Selection Policy",
                ["promoted_plus_top_fallback", "promoted_only", "top3_always"],
                index=0,
            )
            params["max_runtime_sec"] = st.number_input(
                "Max Runtime Sec", min_value=60, max_value=900, value=300, step=30
            )

        submit = st.form_submit_button("Run")

    if stage == "feature2_hypothesis":
        if st.button("Run Feature 2 Preflight Checks"):
            checks = _run_feature2_preflight(params)
            st.dataframe(pd.DataFrame(checks), width="stretch", hide_index=True)

    validation_errors = validate_stage_params(stage, params)
    if validation_errors:
        st.warning("Required fields are missing.")
        st.code("\n".join(validation_errors))

    module, args = build_stage_command(stage, params)
    st.code(" ".join([sys.executable, "-m", module] + args), language="bash")

    if submit:
        if validation_errors:
            st.error("Run aborted due to missing required fields.")
            return

        with st.spinner("Executing pipeline..."):
            code, out, err, elapsed = _run_pipeline(module, args)
            write_run_index(ARTIFACTS)

        diagnostics = _analyze_run_diagnostics(code, out, err)
        summary = _parse_summary_json_from_stdout(out)

        c1, c2, c3, c4 = st.columns(4)
        _kpi(c1, "Exit Code", str(code))
        _kpi(c2, "Elapsed Sec", f"{elapsed:.2f}")
        _kpi(c3, "Run Status", diagnostics["run_status"])
        _kpi(c4, "Agent Health", diagnostics["agent_health"]["status"])

        status_chip_html = _status_chip(diagnostics["run_status"]) + _status_chip(diagnostics["agent_health"]["status"])
        st.markdown(status_chip_html, unsafe_allow_html=True)

        if diagnostics["run_status"] == "success":
            st.success("Run completed successfully.")
        elif diagnostics["run_status"] == "partial_success":
            st.warning("Run completed with warnings.")
        else:
            st.error("Run failed.")

        if diagnostics["agent_health"]["status"] == "failed":
            st.error(
                f"Agent health failure: {diagnostics['agent_health']['failure_reason']}\n\n"
                f"Remediation: {diagnostics['agent_health']['remediation']}"
            )

        for warning in diagnostics["warnings"]:
            st.warning(warning)

        if summary:
            st.markdown("### Run Summary")
            if isinstance(summary.get("run_meta"), dict):
                run_meta = summary["run_meta"]
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"field": "run_id", "value": run_meta.get("run_id")},
                            {"field": "status", "value": run_meta.get("status")},
                            {"field": "duration_sec", "value": run_meta.get("duration_sec")},
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )

        with st.expander("Debug Details: stdout", expanded=(code != 0)):
            st.text(out or "<empty>")
        if err:
            with st.expander("Debug Details: stderr", expanded=(code != 0)):
                st.text(err)


def _screen_run_timeline() -> None:
    st.subheader("Run Timeline")
    _render_run_story(
        "All discovered runs across Features 1-5.",
        "Timeline merges per-stage manifests and quality summaries.",
        "Filter by stage/status, then push selected run into monitor or dashboards.",
    )
    c1, c2 = st.columns([1, 5])
    if c1.button("Refresh Index"):
        write_run_index(ARTIFACTS)
    c2.caption(f"Index file: `{RUN_INDEX_PATH}`")

    payload = load_run_index(ARTIFACTS)
    runs = payload.get("runs", [])
    if not runs:
        st.info("No indexed runs found under artifacts/.")
        return

    all_stages = sorted({str(row.get("stage", "")) for row in runs if row.get("stage")})
    all_statuses = sorted({str(row.get("status", "")) for row in runs if row.get("status")})
    stage_filter = st.multiselect("Stage", all_stages, default=all_stages)
    status_filter = st.multiselect("Status", all_statuses, default=all_statuses)
    run_contains = st.text_input("Run ID contains", value="")

    filtered: list[dict[str, Any]] = []
    for row in runs:
        run_id = str(row.get("run_id", ""))
        stage = str(row.get("stage", ""))
        status = str(row.get("status", ""))
        if stage_filter and stage not in stage_filter:
            continue
        if status_filter and status not in status_filter:
            continue
        if run_contains and run_contains.lower() not in run_id.lower():
            continue
        filtered.append(row)

    if not filtered:
        st.info("No runs match current filters.")
        return

    table_rows: list[dict[str, Any]] = []
    for row in filtered:
        summary = row.get("summary", {})
        table_rows.append(
            {
                "run_id": row.get("run_id"),
                "stage": row.get("stage"),
                "status": str(row.get("status", "")).upper(),
                "created_at": row.get("created_at"),
                "errors": row.get("errors_count", 0),
                "quality_passed": summary.get("quality_passed"),
                "primary_count": (
                    summary.get("result_count")
                    or summary.get("candidate_count")
                    or summary.get("hypothesis_count")
                    or summary.get("selected_factor_count")
                    or summary.get("market_rows")
                ),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True)

    options = [f"{row['run_id']} | {row['stage']} | {row['status']}" for row in filtered]
    selected_label = st.selectbox("Select timeline row", options)
    selected = filtered[options.index(selected_label)]

    st.markdown("### Stage Progression")
    lineage = selected.get("lineage", {}) or {}
    stage_run_map = {
        "feature1_ingestion": lineage.get("ingestion_run_id") or (selected["run_id"] if selected.get("stage") == "feature1_ingestion" else None),
        "feature2_hypothesis": lineage.get("hypothesis_run_id") or (selected["run_id"] if selected.get("stage") == "feature2_hypothesis" else None),
        "feature3_factor": lineage.get("factor_run_id") or (selected["run_id"] if selected.get("stage") == "feature3_factor" else None),
        "feature4_evaluation": lineage.get("evaluation_run_id") or (selected["run_id"] if selected.get("stage") == "feature4_evaluation" else None),
        "feature5_report": selected["run_id"] if selected.get("stage") == "feature5_report" else None,
    }
    chips = []
    for stage_name in STAGE_LABELS:
        run_id = stage_run_map.get(stage_name)
        css = "am-chip-ok" if run_id else "am-chip-unknown"
        label = f"{STAGE_LABELS[stage_name]}: {run_id or 'n/a'}"
        chips.append(f"<span class='am-chip {css}'>{label}</span>")
    st.markdown("".join(chips), unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    if q1.button("Use In Monitor"):
        _seed_timeline_defaults(selected)
    if q2.button("Use In Dashboard"):
        _seed_timeline_defaults(selected)
    if q3.button("Use In Factor Library"):
        _seed_timeline_defaults(selected)
    if q4.button("Use In Report Viewer"):
        _seed_timeline_defaults(selected)

    _render_debug_json("timeline_selected", selected)


def _screen_run_monitor() -> None:
    st.subheader("Run Monitor")
    _render_run_story(
        "One run manifest and its artifacts.",
        "You get health, lineage, integrity checks, and issue remediation.",
        "Fix missing paths/errors first, then open debug details if needed.",
    )
    run_types = list(RUN_TYPE_LABEL_TO_STAGE.keys())
    default_type_idx = _choose_default("monitor.run_type", run_types)
    run_type = st.selectbox("Run Type", run_types, index=default_type_idx, key="monitor.run_type")
    stage = RUN_TYPE_LABEL_TO_STAGE[run_type]
    manifest_name = MANIFEST_BY_STAGE[stage]
    run_ids = _list_run_ids(manifest_name)

    if not run_ids:
        st.info("No runs found for this stage.")
        return

    default_run_idx = _choose_default("monitor.run_id", run_ids)
    run_id = st.selectbox("Run ID", run_ids, index=default_run_idx, key="monitor.run_id")

    manifest_path = ARTIFACTS / run_id / manifest_name
    manifest, err = _safe_read_json(manifest_path)
    if err or manifest is None:
        st.error(err or "Unknown manifest load error")
        return

    index_row = _load_run_index_map().get((run_id, stage), {})
    health = _manifest_health(manifest)
    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, "Status", str(index_row.get("status", "unknown")).upper())
    _kpi(c2, "Errors", str(index_row.get("errors_count", 0)))
    _kpi(c3, "Path Checks", str(health["checked"]))
    _kpi(c4, "Missing Paths", str(len(health["missing"])))

    st.markdown("### Run Summary")
    summary_rows = [{"field": key, "value": value} for key, value in index_row.get("summary", {}).items()]
    if summary_rows:
        st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)
    else:
        st.info("No summary metrics available.")

    st.markdown("### Lineage")
    lineage_rows = [{"field": key, "value": value} for key, value in (index_row.get("lineage", {}) or {}).items()]
    st.dataframe(pd.DataFrame(lineage_rows), width="stretch", hide_index=True)

    st.markdown("### Artifact Integrity")
    _render_artifact_integrity_table(health)

    st.markdown("### Issues")
    if health["missing"]:
        st.error("Missing artifact references detected.")
        for row in health["missing"]:
            st.write(f"- `{row['field']}` missing at `{row['path']}`")
        st.info("Remediation: rerun the same stage or regenerate missing upstream artifacts.")
    elif int(index_row.get("errors_count", 0)) > 0:
        st.warning("Run completed with recorded errors. Review debug details for root cause.")
    else:
        st.success("No blocking integrity issues detected.")

    _render_debug_json("manifest", manifest)


def _load_evaluation_bundle(run_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, str | None]:
    manifest, err = _safe_read_json(ARTIFACTS / run_id / "evaluation_manifest.json")
    if err or manifest is None:
        return None, None, None, err
    results, results_err = _safe_read_json(_resolve_path(str(manifest.get("results_path", ""))))
    if results_err:
        return manifest, None, None, results_err
    timeseries, ts_err = _safe_read_json(_resolve_path(str(manifest.get("timeseries_path", ""))))
    if ts_err:
        return manifest, results, None, ts_err
    return manifest, results, timeseries, None


def _screen_results_dashboard() -> None:
    st.subheader("Results Dashboard")
    _render_run_story(
        "Evaluation outputs from Feature 4.",
        "The dashboard highlights winners, risk tradeoffs, and return curves.",
        "Use this to choose candidates for report generation.",
    )
    run_ids = _list_run_ids("evaluation_manifest.json")
    if not run_ids:
        st.info("No Feature 4 evaluation runs found.")
        return

    default_idx = _choose_default("dashboard.eval_run_id", run_ids)
    run_id = st.selectbox("Evaluation Run", run_ids, index=default_idx, key="dashboard.eval_run_id")

    manifest, results_payload, timeseries_payload, err = _load_evaluation_bundle(run_id)
    if err:
        st.error(err)
        return
    if manifest is None or results_payload is None:
        st.error("Incomplete evaluation artifact bundle.")
        return

    results = pd.DataFrame(results_payload.get("results", []))
    ts = pd.DataFrame((timeseries_payload or {}).get("rows", []))

    if results.empty:
        st.warning("Selected run has no result rows.")
        return

    promoted_count = int(results_payload.get("promoted_count", int(results.get("promoted", pd.Series(dtype=bool)).sum())))
    avg_sharpe = float(results["sharpe"].mean()) if "sharpe" in results.columns else 0.0
    best_row = results.sort_values("sharpe", ascending=False).iloc[0] if "sharpe" in results.columns else results.iloc[0]
    rejected_count = len(results) - promoted_count

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, "Evaluated Factors", str(len(results)))
    _kpi(c2, "Promoted", str(promoted_count))
    _kpi(c3, "Rejected", str(rejected_count))
    _kpi(c4, "Average Sharpe", f"{avg_sharpe:.3f}")

    st.markdown(f"**Best Sharpe Factor:** `{best_row.get('factor_id', 'n/a')}`")
    st.code(str(best_row.get("expression", "")))

    view_cols = [
        "factor_id",
        "promoted",
        "sharpe",
        "information_ratio",
        "ic_mean",
        "turnover_monthly_max",
        "oos_score",
        "decay_score",
    ]
    keep_cols = [c for c in view_cols if c in results.columns]
    sortable = "sharpe" if "sharpe" in keep_cols else keep_cols[0]
    st.dataframe(results[keep_cols].sort_values(sortable, ascending=False), width="stretch", hide_index=True)

    top_df = results.sort_values("sharpe", ascending=False).head(10).copy() if "sharpe" in results.columns else results.head(10).copy()
    if alt is not None and not top_df.empty and "factor_id" in top_df.columns and "sharpe" in top_df.columns:
        st.markdown("### Top Factors by Sharpe")
        chart = (
            alt.Chart(top_df)
            .mark_bar()
            .encode(
                x=alt.X("sharpe:Q", title="Sharpe"),
                y=alt.Y("factor_id:N", sort="-x", title="Factor"),
                color=alt.Color("promoted:N", title="Promoted"),
                tooltip=["factor_id", "sharpe", "information_ratio", "ic_mean", "turnover_monthly_max"],
            )
        )
        st.altair_chart(chart, width="stretch")

    if alt is not None and {"ic_mean", "turnover_monthly_max", "factor_id"}.issubset(results.columns):
        st.markdown("### IC vs Turnover")
        scatter = (
            alt.Chart(results)
            .mark_circle(size=90)
            .encode(
                x=alt.X("turnover_monthly_max:Q", title="Max Monthly Turnover"),
                y=alt.Y("ic_mean:Q", title="Mean IC"),
                color=alt.Color("promoted:N", title="Promoted"),
                tooltip=["factor_id", "ic_mean", "turnover_monthly_max", "sharpe"],
            )
        )
        st.altair_chart(scatter, width="stretch")

    if not ts.empty and {"factor_id", "date", "net_return"}.issubset(ts.columns):
        st.markdown("### Net Return Curves")
        ids = sorted(ts["factor_id"].dropna().unique().tolist())
        chart_ids = st.multiselect("Factors to chart", ids, default=ids[:3])
        if chart_ids:
            plot_df = ts[ts["factor_id"].isin(chart_ids)].copy()
            plot_df["date"] = pd.to_datetime(plot_df["date"])
            plot_df.sort_values(["factor_id", "date"], inplace=True)
            plot_df["cum_net"] = plot_df.groupby("factor_id")["net_return"].transform(lambda s: (1.0 + s).cumprod() - 1.0)
            if alt is not None:
                curve = (
                    alt.Chart(plot_df)
                    .mark_line()
                    .encode(
                        x=alt.X("date:T", title="Date"),
                        y=alt.Y("cum_net:Q", title="Cumulative Net Return"),
                        color=alt.Color("factor_id:N", title="Factor"),
                    )
                )
                st.altair_chart(curve, width="stretch")
            else:
                pivot = plot_df.pivot_table(index="date", columns="factor_id", values="cum_net")
                st.line_chart(pivot)

    _render_debug_json("evaluation_manifest", manifest)


def _load_factor_bundle(run_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, str | None]:
    manifest, err = _safe_read_json(ARTIFACTS / run_id / "factor_manifest.json")
    if err or manifest is None:
        return None, None, None, err
    factors, factors_err = _safe_read_json(_resolve_path(str(manifest.get("factors_path", ""))))
    if factors_err:
        return manifest, None, None, factors_err
    validation, validation_err = _safe_read_json(_resolve_path(str(manifest.get("validation_path", ""))))
    if validation_err:
        return manifest, factors, None, validation_err
    return manifest, factors, validation, None


def _screen_factor_library() -> None:
    st.subheader("Factor Library")
    _render_run_story(
        "Factor candidates from Feature 3 with optional Feature 4 joins.",
        "Accepted/rejected states are split for fast review and comparison.",
        "Focus on accepted high-quality factors, then inspect rejects for recovery ideas.",
    )
    factor_runs = _list_run_ids("factor_manifest.json")
    if not factor_runs:
        st.info("No Feature 3 factor runs found.")
        return

    factor_idx = _choose_default("factor_library.factor_run_id", factor_runs)
    factor_run_id = st.selectbox("Factor Run", factor_runs, index=factor_idx, key="factor_library.factor_run_id")
    eval_runs = ["<none>"] + _list_run_ids("evaluation_manifest.json")
    eval_idx = _choose_default("factor_library.eval_run_id", eval_runs, fallback="<none>")
    eval_run_id = st.selectbox("Join Evaluation Run", eval_runs, index=eval_idx, key="factor_library.eval_run_id")

    _, factors_payload, validation_payload, err = _load_factor_bundle(factor_run_id)
    if err:
        st.error(err)
        return
    if factors_payload is None or validation_payload is None:
        st.error("Factor artifact bundle is incomplete.")
        return

    candidates = pd.DataFrame(factors_payload.get("candidates", []))
    if candidates.empty:
        st.warning("No factor candidates available in selected run.")
        return

    accepted_ids = {row.get("factor_id") for row in factors_payload.get("accepted", [])}
    candidates["accepted"] = candidates["factor_id"].isin(accepted_ids)
    dsl_pass = {
        row.get("factor_id"): bool(row.get("passed", False))
        for row in validation_payload.get("rows", [])
        if row.get("stage") == "dsl_validation"
    }
    candidates["dsl_valid"] = candidates["factor_id"].map(lambda x: dsl_pass.get(x, False))

    if eval_run_id != "<none>":
        _, eval_results_payload, _, eval_err = _load_evaluation_bundle(eval_run_id)
        if eval_err:
            st.warning(f"Evaluation join skipped: {eval_err}")
        elif eval_results_payload is not None:
            eval_df = pd.DataFrame(eval_results_payload.get("results", []))
            if not eval_df.empty:
                merge_cols = [
                    "factor_id",
                    "promoted",
                    "sharpe",
                    "information_ratio",
                    "ic_mean",
                    "turnover_monthly_max",
                ]
                merge_cols = [c for c in merge_cols if c in eval_df.columns]
                candidates = candidates.merge(eval_df[merge_cols], on="factor_id", how="left")

    c1, c2, c3 = st.columns(3)
    _kpi(c1, "Total Candidates", str(len(candidates)))
    _kpi(c2, "Accepted", str(int(candidates["accepted"].sum())))
    _kpi(c3, "Rejected", str(int((~candidates["accepted"]).sum())))

    if alt is not None and {"originality_score", "complexity_score"}.issubset(candidates.columns):
        st.markdown("### Originality vs Complexity")
        scatter = (
            alt.Chart(candidates)
            .mark_circle(size=90)
            .encode(
                x=alt.X("complexity_score:Q", title="Complexity"),
                y=alt.Y("originality_score:Q", title="Originality"),
                color=alt.Color("accepted:N", title="Accepted"),
                tooltip=["factor_id", "expression", "complexity_score", "originality_score", "accepted"],
            )
        )
        st.altair_chart(scatter, width="stretch")

    tab_all, tab_accepted, tab_rejected = st.tabs(["All", "Accepted", "Rejected"])
    display_cols = [
        "factor_id",
        "expression",
        "dsl_valid",
        "accepted",
        "complexity_score",
        "originality_score",
        "promoted",
        "sharpe",
        "information_ratio",
        "ic_mean",
        "turnover_monthly_max",
    ]
    display_cols = [c for c in display_cols if c in candidates.columns]

    with tab_all:
        st.dataframe(candidates[display_cols], width="stretch", hide_index=True)
    with tab_accepted:
        st.dataframe(candidates[candidates["accepted"]][display_cols], width="stretch", hide_index=True)
    with tab_rejected:
        st.dataframe(candidates[~candidates["accepted"]][display_cols], width="stretch", hide_index=True)

    compare_ids = st.multiselect(
        "Compare Factors (side-by-side)",
        candidates["factor_id"].tolist(),
        default=candidates["factor_id"].tolist()[:2],
    )
    if compare_ids:
        subset = candidates[candidates["factor_id"].isin(compare_ids)][display_cols].copy()
        st.markdown("### Comparison Table")
        st.dataframe(subset.set_index("factor_id").transpose(), width="stretch")
        _render_debug_json("factor_compare_raw", {"rows": subset.to_dict(orient="records")})


def _load_report_bundle(run_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, str | None, str | None]:
    manifest, err = _safe_read_json(ARTIFACTS / run_id / "report_manifest.json")
    if err or manifest is None:
        return None, None, None, None, err
    payload, payload_err = _safe_read_json(_resolve_path(str(manifest.get("report_payload_path", ""))))
    if payload_err:
        return manifest, None, None, None, payload_err
    quality, quality_err = _safe_read_json(_resolve_path(str(manifest.get("quality_path", ""))))
    if quality_err:
        return manifest, payload, None, None, quality_err
    markdown, markdown_err = _safe_read_text(_resolve_path(str(manifest.get("report_markdown_path", ""))))
    if markdown_err:
        return manifest, payload, quality, None, markdown_err
    return manifest, payload, quality, markdown, None


def _screen_report_viewer() -> None:
    st.subheader("Report Viewer")
    _render_run_story(
        "Final research note and selected factors from Feature 5.",
        "You can review selected factors, risk caveats, and full markdown output.",
        "Promote to stakeholder-ready export only after quality and risk checks pass.",
    )
    report_runs = _list_run_ids("report_manifest.json")
    if not report_runs:
        st.info("No Feature 5 report runs found.")
        return

    default_idx = _choose_default("report_viewer.run_id", report_runs)
    report_run_id = st.selectbox("Report Run", report_runs, index=default_idx, key="report_viewer.run_id")

    manifest, payload, quality, markdown, err = _load_report_bundle(report_run_id)
    if err:
        st.error(err)
        return
    if manifest is None or payload is None or quality is None or markdown is None:
        st.error("Report artifact bundle is incomplete.")
        return

    selected = list(payload.get("selected_factors", []))
    selected_df = pd.DataFrame(selected)
    promoted_count = int(selected_df["promoted"].sum()) if not selected_df.empty and "promoted" in selected_df.columns else 0
    high_turnover_count = int((selected_df["turnover_monthly_max"] > 0.80).sum()) if not selected_df.empty and "turnover_monthly_max" in selected_df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    _kpi(c1, "Quality Passed", "yes" if quality.get("passed", False) else "no")
    _kpi(c2, "Selected Factors", str(len(selected)))
    _kpi(c3, "Promoted in Report", str(promoted_count))
    _kpi(c4, "High Turnover Risks", str(high_turnover_count))

    st.markdown("### Selected Factors")
    if selected_df.empty:
        st.info("No selected factors available in report payload.")
    else:
        keep = [
            "factor_id",
            "expression",
            "promoted",
            "composite_score",
            "sharpe",
            "information_ratio",
            "ic_mean",
            "turnover_monthly_max",
            "oos_score",
            "decay_score",
        ]
        keep = [c for c in keep if c in selected_df.columns]
        st.dataframe(selected_df[keep], width="stretch", hide_index=True)

    st.markdown("### Rendered Research Note")
    st.markdown(markdown)

    _render_debug_json("report_payload", payload)
    _render_debug_json("report_quality", quality)
    _render_debug_json("report_manifest", manifest)


def main() -> None:
    st.set_page_config(page_title="Alpha Miner Console", page_icon="AM", layout="wide")
    _inject_css()
    write_run_index(ARTIFACTS)

    st.title("Alpha Miner Console")
    st.caption("Executive-first run operations and artifact analytics for Features 1-5.")

    tabs = st.tabs(
        [
            "Create Run",
            "Run Timeline",
            "Run Monitor",
            "Results Dashboard",
            "Factor Library",
            "Report Viewer",
        ]
    )

    with tabs[0]:
        _screen_create_run()
    with tabs[1]:
        _screen_run_timeline()
    with tabs[2]:
        _screen_run_monitor()
    with tabs[3]:
        _screen_results_dashboard()
    with tabs[4]:
        _screen_factor_library()
    with tabs[5]:
        _screen_report_viewer()


if __name__ == "__main__":
    main()
