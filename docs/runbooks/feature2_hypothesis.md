# Runbook: Feature 2 Hypothesis Generation

## Preconditions
1. Feature 1 ingestion artifacts exist under `artifacts/<ingestion_run_id>/`.
2. Strict baseline gate remains `text_coverage_min=0.20`.
3. For Gemini path: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, ADC configured.
4. For Claude path: `anthropic` package installed and Vertex ADC configured.

## Standard Run (Gemini + Google Search)
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id <feature1_run_id> \
  --run-id <feature2_run_id> \
  --model-policy gemini_with_search \
  --gemini-model gemini-2.5-flash \
  --enable-google-search-tool
```

## Deterministic Run
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id <feature1_run_id> \
  --run-id <feature2_run_id> \
  --model-policy deterministic_only
```

## Strict Gemini Run (No Fallback)
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id <feature1_run_id> \
  --run-id <feature2_run_id> \
  --model-policy gemini_only \
  --gemini-model gemini-2.5-flash \
  --enable-google-search-tool
```

## Output Artifacts
1. `artifacts/<run_id>/hypothesis_quality_gate.json`
2. `artifacts/<run_id>/hypotheses.json`
3. `artifacts/<run_id>/debate_log.json`
4. `artifacts/<run_id>/model_trace.json`
5. `artifacts/<run_id>/hypothesis_manifest.json`

## Model Policy Semantics
1. `gemini_with_search`: Gemini+Search first; deterministic fallback on failure.
2. `gemini_only`: Gemini+Search required; fail on generation/backend failure.
3. `claude_with_fallback`: Claude first; deterministic fallback on failure.
4. `claude_only`: Claude required; fail on generation/backend failure.
5. `deterministic_only`: No LLM call.

## Triage
1. `readiness_gate_failed`:
   - Check `artifacts/<ingestion_run_id>/ingestion_quality.json`.
2. `model_fallback`:
   - Inspect `model_trace.json` and verify env/auth/model availability.
3. `gemini_generation_failed` / `gemini_only` failure:
   - Verify ADC and Vertex project/location settings.
4. `missing_or_invalid_artifact`:
   - Confirm manifest/table paths from Feature 1 still exist.

