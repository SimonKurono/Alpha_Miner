# Runbook: Feature 2 Hypothesis Generation

## Preconditions
1. Feature 1 ingestion run artifacts exist under `artifacts/<ingestion_run_id>/`.
2. Python env includes `google-adk`.
3. For Claude path: `anthropic` package installed and Vertex ADC configured.
4. Temporary prototype override: default `text_coverage_min` is set to `0.10` (lowered from `0.20`) to unblock Feature 3 while external text providers are unstable.

## Standard Run
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id <feature1_run_id> \
  --run-id <feature2_run_id>
```

## Deterministic Mode (No Claude Dependency)
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id <feature1_run_id> \
  --run-id <feature2_run_id> \
  --model-policy deterministic_only
```

## Output Artifacts
- `artifacts/<run_id>/hypothesis_quality_gate.json`
- `artifacts/<run_id>/hypotheses.json`
- `artifacts/<run_id>/debate_log.json`
- `artifacts/<run_id>/hypothesis_manifest.json`

## Triage
- If `readiness_gate_failed`: inspect `artifacts/<ingestion_run_id>/ingestion_quality.json`.
- If `missing_or_invalid_artifact`: confirm manifest and table paths still exist.
- If `claude_generation_failed`: switch to `--model-policy deterministic_only` and retry.

## Temporary Policy + Restore Trigger
- Current default gate: `text_coverage_min=0.10` (prototype override).
- Restore target: raise back to `>=0.20` once Feature 1 achieves stable text coverage on canonical smoke runs.
