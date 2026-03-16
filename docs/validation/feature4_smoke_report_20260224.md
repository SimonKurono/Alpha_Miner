# Feature 4 Smoke Report (2026-02-24)

## Run Metadata
- Date (UTC): `2026-02-24`
- Run ID: `f4_smoke_20260224`
- Ingestion input: `f1_smoke_s2_postfix_20260223`
- Factor input: `f3_smoke_20260223`
- Command runtime (`/usr/bin/time -p`):
  - `real=2.95s`
  - `user=2.53s`
  - `sys=0.31s`
- Pipeline runtime (`run.meta.duration_sec`): `1.126797s`

## Artifact Checks
- `artifacts/f4_smoke_20260224/evaluation_manifest.json`: present
- `artifacts/f4_smoke_20260224/evaluation_results.json`: present
- `artifacts/f4_smoke_20260224/evaluation_metrics_timeseries.json`: present

## Summary Metrics
- Evaluated factors: `10`
- Promoted factors: `1`
- Errors: `0`
- Status: `success`

Top promoted factor:
- `factor_id=fct_003`
- expression: `Normalize(volume)`
- Sharpe: `0.9545`
- IR: `0.9545`
- IC mean: `0.0576`
- Turnover monthly max: `0.500`
- OOS score: `0.7661`
- Decay score: `1.0000`

## Promotion Rule Behavior
- Moderate profile thresholds correctly enforced.
- Several high-performing factors were rejected for turnover breaches (`turnover_monthly_max > 0.80`).

## Decision
- Classification: `GO`
- Reason: Feature 4 workflow executes end-to-end, emits all required artifacts, computes required metrics, and returns deterministic promotion decisions within runtime budget.

## Remaining Risks
1. Benchmark return uses market artifact availability for `SPY`; if missing, IR can degrade to active return vs zero.
2. Current smoke used prototype artifacts; broader universe/runtime profiling should be validated before demo hardening.
3. Feature 2 remains under temporary text gate `0.10`, so upstream hypothesis quality policy is not yet restored.
