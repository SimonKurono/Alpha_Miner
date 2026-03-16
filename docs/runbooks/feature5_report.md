# Feature 5 Runbook: Report Generation Workflow

## Preconditions
1. Feature 4 artifacts exist at `artifacts/<evaluation_run_id>/evaluation_manifest.json`.
2. Local environment can run ADK workflows with `PYTHONPATH=src`.

## Command
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature5_report_cli \
  --run-id f5_smoke_20260224 \
  --ingestion-run-id f1_smoke_s2_postfix_20260223 \
  --factor-run-id f3_smoke_20260223 \
  --evaluation-run-id f4_smoke_20260224 \
  --report-mode deterministic_first \
  --factor-selection-policy promoted_plus_top_fallback \
  --max-runtime-sec 300
```

## Expected Outputs
- `artifacts/<run_id>/research_note.md`
- `artifacts/<run_id>/research_note.json`
- `artifacts/<run_id>/report_quality.json`
- `artifacts/<run_id>/report_manifest.json`

## Failure Modes
- `missing_or_invalid_artifact`: invalid/missing evaluation manifest or payload files.
- `empty_selection`: policy produced zero factors (hard fail).
- `quality_gate_failed`: required headings/disclaimer missing.

## Status Semantics
- `success`: quality passed and no warnings.
- `partial_success`: quality passed with warnings (e.g., fallback policy used, high turnover warnings).
- `failed`: artifact load, selection, or quality gate hard failure.
