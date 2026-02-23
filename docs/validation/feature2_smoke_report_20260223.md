# Feature 2 Smoke Report
Date: 2026-02-23

## Objective
Validate Feature 2 live execution against remediated Feature 1 artifacts using model-agnostic mode (`deterministic_only`).

## Run
- Feature 2 run ID: `f2_smoke_postfix_20260223`
- Ingestion dependency: `f1_smoke_s2_postfix_20260223`
- Model policy: `deterministic_only`
- Runtime budget: `300s`

## Output Artifacts
- `artifacts/f2_smoke_postfix_20260223/hypothesis_manifest.json`
- `artifacts/f2_smoke_postfix_20260223/hypothesis_quality_gate.json`
- `artifacts/f2_smoke_postfix_20260223/hypotheses.json`
- `artifacts/f2_smoke_postfix_20260223/debate_log.json`

## Gate Result
- `passed=false`
- `market_symbol_coverage=1.0`
- `text_symbol_coverage=0.1`
- Failure: `Text symbol coverage below minimum: 0.10 < 0.20`

## Runtime Result
- `run.meta.status=failed`
- `duration_sec=0.018778`
- Agents correctly short-circuited after readiness gate and persisted diagnostics.

## Classification
**NO_GO** for Feature 2 full closure under strict gate.

## Notes
Feature 2 implementation behavior is correct; blocker is upstream text coverage from Feature 1 live providers.
