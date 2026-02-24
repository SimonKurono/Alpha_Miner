# Feature 2 Smoke Report (Temporary Gate 0.10)
Date: 2026-02-23

## Objective
Validate Feature 2 run under temporary prototype gate override (`text_coverage_min=0.10`) to unblock Feature 3 kickoff.

## Run
- Run ID: `f2_smoke_gate10_20260223`
- Ingestion source: `f1_smoke_s2_postfix_20260223`
- Model policy: `deterministic_only`
- Runtime budget: `300s`

## Result
- `run.meta.status=partial_success`
- `hypothesis_count=3`
- Gate payload:
  - `passed=true`
  - `market_symbol_coverage=1.0`
  - `text_symbol_coverage=0.1`
  - `warnings=['Ingestion warning: Low text symbol coverage: 10.00%']`

## Output Artifacts
- `artifacts/f2_smoke_gate10_20260223/hypothesis_manifest.json`
- `artifacts/f2_smoke_gate10_20260223/hypothesis_quality_gate.json`
- `artifacts/f2_smoke_gate10_20260223/hypotheses.json`
- `artifacts/f2_smoke_gate10_20260223/debate_log.json`

## Classification
**GO (temporary policy)** for proceeding to Feature 3 implementation and planning.

## Temporary Policy Note
This run uses a temporary gate override (`0.10` vs original `0.20`).
Restore target: raise gate back to `>=0.20` after Feature 1 text pipeline stability improvements.
