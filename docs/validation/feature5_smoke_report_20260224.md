# Feature 5 Smoke Report (2026-02-24)

## Run Metadata
- Date (UTC): `2026-02-24`
- Run ID: `f5_smoke_20260224`
- Upstream artifacts:
  - ingestion: `f1_smoke_s2_postfix_20260223`
  - factors: `f3_smoke_20260223`
  - evaluation: `f4_smoke_20260224`
- Command runtime (`/usr/bin/time -p`):
  - `real=1.43s`
  - `user=1.27s`
  - `sys=0.13s`
- Pipeline runtime (`run.meta.duration_sec`): `0.007891s`

## Artifact Checks
- `artifacts/f5_smoke_20260224/report_manifest.json`: present
- `artifacts/f5_smoke_20260224/research_note.md`: present
- `artifacts/f5_smoke_20260224/research_note.json`: present
- `artifacts/f5_smoke_20260224/report_quality.json`: present

## Quality and Selection
- quality passed: `true`
- failures: `0`
- warnings: `0`
- selected factors: `1`
- selected factor ids: `fct_003`
- fallback path used: `false`

## Decision
- Classification: `GO`
- Reason: Feature 5 workflow runs end-to-end and produces all required report artifacts with passing quality checks within runtime budget.

## Remaining Risks
1. Temporary upstream text gate (`0.10`) remains active and is documented in the report risk section.
2. LLM enrichment path is intentionally deferred; current output is deterministic-first.
