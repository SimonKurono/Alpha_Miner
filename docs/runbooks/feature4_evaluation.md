# Feature 4 Runbook: Evaluation Workflow

## Preconditions
1. Feature 1 ingestion artifacts exist: `artifacts/<ingestion_run_id>/ingestion_manifest.json`
2. Feature 3 factor artifacts exist: `artifacts/<factor_run_id>/factor_manifest.json`
3. Local venv is active and dependencies are installed.

## Command
```bash
PYTHONPATH=src ./venv/bin/python -m alpha_miner.pipelines.feature4_evaluation_cli \
  --run-id f4_smoke_20260224 \
  --ingestion-run-id f1_smoke_s2_postfix_20260223 \
  --factor-run-id f3_smoke_20260223 \
  --max-runtime-sec 300
```

## Expected Outputs
- `artifacts/<run_id>/evaluation_results.json`
- `artifacts/<run_id>/evaluation_metrics_timeseries.json`
- `artifacts/<run_id>/evaluation_manifest.json`

## Troubleshooting
- `missing_or_invalid_artifact`: verify ingestion/factor run IDs and manifest paths.
- `factor_score_failure`: inspect expression validity and market field availability.
- `budget_exceeded`: reduce factor count or date range; rerun with tuned runtime budget.

## Promotion Interpretation
- `promoted=true`: factor met selected profile bars.
- `promoted=false`: check `reject_reasons` for threshold failures.
