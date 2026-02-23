# Runbook: Feature 1 Ingestion

## Preconditions
- Python environment with `google-adk`, `pydantic`, `requests`, `PyYAML`, `tenacity`
- Environment variable `SEC_USER_AGENT` set for SEC API compliance
- Optional: `FRED_API_KEY` for macro data calls

## Run
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature1_ingestion_cli \
  --run-id alpha_f1_001 \
  --start-date 2020-01-01 \
  --end-date 2024-12-31
```

## Outputs
- Raw artifacts: `data/raw/ingestion/<run_id>/`
- Normalized artifacts: `data/processed/ingestion/<run_id>/`
- Quality report: `artifacts/<run_id>/ingestion_quality.json`
- Manifest: `artifacts/<run_id>/ingestion_manifest.json`

## Failure Triage
1. Check `errors.ingestion` in final state summary.
2. If SEC calls fail: verify `SEC_USER_AGENT` format and throttle.
3. If GDELT calls fail: rerun with same run-id and reduced universe.
4. If coverage < 85%: reduce symbols or inspect provider outage.
5. If parquet not generated: pipeline falls back to JSONL; install pandas+pyarrow for parquet.
