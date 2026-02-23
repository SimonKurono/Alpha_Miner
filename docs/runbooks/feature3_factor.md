# Runbook: Feature 3 Factor Construction

## Preconditions
1. Feature 1 ingestion manifest exists: `artifacts/<ingestion_run_id>/ingestion_manifest.json`.
2. Feature 2 hypotheses exist: `artifacts/<hypothesis_run_id>/hypotheses.json`.
3. Python env includes `google-adk`.

## Standard Run
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature3_factor_cli \
  --ingestion-run-id <feature1_run_id> \
  --hypothesis-run-id <feature2_run_id> \
  --run-id <feature3_run_id>
```

## Tuning Knobs
- `--target-factor-count` (default `10`)
- `--originality-min` (default `0.20`)
- `--complexity-max` (default `16`)

## Triage
- If `missing_or_invalid_artifact`: verify upstream run IDs and artifact paths.
- If all factors rejected: relax `--originality-min` or raise `--complexity-max` for prototype iteration.
- If parser errors dominate: inspect rejected rows in `factor_validation.json` and fix generation templates.
