# Feature 3 Smoke Report
Date: 2026-02-23

## Objective
Validate initial Feature 3 factor-construction pipeline end-to-end using existing Feature 1/2 artifacts.

## Run
- Run ID: `f3_smoke_20260223`
- Ingestion source: `f1_smoke_s2_postfix_20260223`
- Hypothesis source: `f2_smoke_gate10_20260223`
- Target factor count: `10`

## Result
- `run.meta.status=partial_success`
- Candidate generation: `10`
- DSL validation pass: `10`
- Constraint filtering:
  - accepted: `3`
  - rejected: `7`

## Output Artifacts
- `artifacts/f3_smoke_20260223/factor_manifest.json`
- `artifacts/f3_smoke_20260223/factors.json`
- `artifacts/f3_smoke_20260223/factor_validation.json`

## Acceptance Check
- Requirement: Feature 3 CLI produces at least 10 candidates with validation metadata.
- Observed: **PASS** (`candidate_count=10`, validation rows persisted).

## Notes
High reject rate is expected at strict defaults (`originality_min=0.20`, `complexity_max=16`) and can be tuned in later iterations.
