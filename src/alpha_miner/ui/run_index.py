"""Build and persist a run timeline index from stage manifests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_STAGE_ORDER: list[tuple[str, str]] = [
    ("feature1_ingestion", "ingestion_manifest.json"),
    ("feature2_hypothesis", "hypothesis_manifest.json"),
    ("feature3_factor", "factor_manifest.json"),
    ("feature4_evaluation", "evaluation_manifest.json"),
    ("feature5_report", "report_manifest.json"),
]

RUN_INDEX_FILE = "run_index.json"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _resolve_path(artifacts_root: Path, raw_path: Any) -> Path:
    if not raw_path:
        return artifacts_root / "__missing__"
    candidate = Path(str(raw_path))
    if candidate.is_absolute():
        return candidate
    return artifacts_root.parent / candidate


def _to_relative(path: Path, project_root: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except Exception:  # noqa: BLE001
        return str(path)


def _lineage_from_manifest(stage: str, manifest: dict[str, Any]) -> dict[str, str | None]:
    lineage = {
        "ingestion_run_id": None,
        "hypothesis_run_id": None,
        "factor_run_id": None,
        "evaluation_run_id": None,
    }
    for key in lineage:
        value = manifest.get(key)
        lineage[key] = str(value) if value is not None else None

    # Ensure downstream stages self-reference when upstream key absent.
    if stage == "feature4_evaluation":
        lineage["evaluation_run_id"] = str(manifest.get("run_id", lineage["evaluation_run_id"]))
    if stage == "feature5_report":
        lineage["evaluation_run_id"] = str(manifest.get("evaluation_run_id", lineage["evaluation_run_id"]))
    return lineage


def _summarize_stage(stage: str, artifacts_root: Path, manifest: dict[str, Any]) -> tuple[dict[str, Any], str, int]:
    summary: dict[str, Any] = {}
    status = "unknown"
    errors_count = 0

    if stage == "feature1_ingestion":
        quality = _read_json(_resolve_path(artifacts_root, manifest.get("quality_path")))
        row_counts = manifest.get("row_counts", {})
        if quality:
            warnings = quality.get("warnings", []) or []
            failures = quality.get("failures", []) or []
            summary = {
                "market_coverage": quality.get("market_symbol_coverage"),
                "text_coverage": quality.get("text_symbol_coverage"),
                "market_rows": row_counts.get("market"),
                "text_rows": row_counts.get("text"),
                "quality_passed": quality.get("passed"),
                "warnings_count": len(warnings),
                "failures_count": len(failures),
            }
            errors_count = len(failures)
            if quality.get("passed"):
                status = "partial_success" if warnings else "success"
            else:
                status = "failed"
        else:
            summary = {"market_rows": row_counts.get("market"), "text_rows": row_counts.get("text"), "quality_passed": None}
            status = "failed"
            errors_count = 1

    elif stage == "feature2_hypothesis":
        gate = _read_json(_resolve_path(artifacts_root, manifest.get("quality_gate_path")))
        hypotheses = _read_json(_resolve_path(artifacts_root, manifest.get("hypotheses_path")))
        model_trace = _read_json(_resolve_path(artifacts_root, manifest.get("model_trace_path")))
        hypothesis_count = len((hypotheses or {}).get("hypotheses", []))
        trace_rows = list((model_trace or {}).get("trace", []))
        providers = sorted(
            {
                str(row.get("provider", "")).lower()
                for row in trace_rows
                if str(row.get("provider", "")).strip()
            }
        )
        if gate:
            warnings = gate.get("warnings", []) or []
            failures = gate.get("failures", []) or []
            summary = {
                "hypothesis_count": hypothesis_count,
                "market_coverage": gate.get("market_symbol_coverage"),
                "text_coverage": gate.get("text_symbol_coverage"),
                "quality_passed": gate.get("passed"),
                "warnings_count": len(warnings),
                "failures_count": len(failures),
                "model_providers": providers,
            }
            errors_count = len(failures)
            if gate.get("passed"):
                status = "partial_success" if warnings else "success"
                if hypothesis_count == 0:
                    status = "failed"
                    errors_count += 1
            else:
                status = "failed"
        else:
            summary = {"hypothesis_count": hypothesis_count, "quality_passed": None}
            status = "failed"
            errors_count = 1

    elif stage == "feature3_factor":
        factors = _read_json(_resolve_path(artifacts_root, manifest.get("factors_path")))
        candidate_count = int((factors or {}).get("candidate_count", 0))
        accepted_count = int((factors or {}).get("accepted_count", 0))
        rejected_count = int((factors or {}).get("rejected_count", 0))
        summary = {
            "candidate_count": candidate_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "quality_passed": accepted_count > 0,
        }
        if candidate_count == 0:
            status = "failed"
            errors_count = 1
        elif accepted_count == 0:
            status = "failed"
            errors_count = rejected_count or 1
        elif rejected_count > 0:
            status = "partial_success"
            errors_count = 0
        else:
            status = "success"

    elif stage == "feature4_evaluation":
        results = _read_json(_resolve_path(artifacts_root, manifest.get("results_path")))
        result_count = int((results or {}).get("result_count", 0))
        promoted_count = int((results or {}).get("promoted_count", 0))
        summary = {
            "result_count": result_count,
            "promoted_count": promoted_count,
            "quality_passed": result_count > 0,
        }
        if result_count == 0:
            status = "failed"
            errors_count = 1
        else:
            status = "success"

    elif stage == "feature5_report":
        quality = _read_json(_resolve_path(artifacts_root, manifest.get("quality_path")))
        payload = _read_json(_resolve_path(artifacts_root, manifest.get("report_payload_path")))
        selected_count = len((payload or {}).get("selected_factors", []))
        warnings = (quality or {}).get("warnings", []) or []
        failures = (quality or {}).get("failures", []) or []
        passed = bool((quality or {}).get("passed", False))
        summary = {
            "selected_factor_count": selected_count,
            "quality_passed": passed,
            "warnings_count": len(warnings),
            "failures_count": len(failures),
        }
        errors_count = len(failures)
        if passed:
            status = "partial_success" if warnings else "success"
        else:
            status = "failed"
            if errors_count == 0:
                errors_count = 1

    # Normalize any accidentally relative manifest-linked file paths.
    for key, value in list(summary.items()):
        if isinstance(value, Path):
            summary[key] = str(value)

    return summary, status, errors_count


def build_run_index(artifacts_root: Path) -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    if not artifacts_root.exists():
        return {"generated_at": datetime.now(timezone.utc).isoformat(), "runs": runs}

    for run_dir in sorted([p for p in artifacts_root.iterdir() if p.is_dir()], key=lambda p: p.name):
        for stage, manifest_name in MANIFEST_STAGE_ORDER:
            manifest_path = run_dir / manifest_name
            manifest = _read_json(manifest_path)
            if manifest is None:
                continue

            summary, status, errors_count = _summarize_stage(stage, artifacts_root, manifest)
            runs.append(
                {
                    "run_id": run_dir.name,
                    "stage": stage,
                    "status": status,
                    "created_at": manifest.get("created_at"),
                    "manifest_path": _to_relative(manifest_path, artifacts_root.parent),
                    "summary": summary,
                    "lineage": _lineage_from_manifest(stage, manifest),
                    "errors_count": errors_count,
                }
            )

    runs.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("run_id"))), reverse=True)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "runs": runs}


def write_run_index(artifacts_root: Path) -> Path:
    payload = build_run_index(artifacts_root)
    artifacts_root.mkdir(parents=True, exist_ok=True)
    target = artifacts_root / RUN_INDEX_FILE
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_run_index(artifacts_root: Path) -> dict[str, Any]:
    path = artifacts_root / RUN_INDEX_FILE
    payload = _read_json(path)
    if payload is not None:
        return payload
    return build_run_index(artifacts_root)
