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
- Coverage breakdown: `artifacts/<run_id>/text_coverage_breakdown.json`

## Text Fallback Behavior
- Primary text source is GDELT.
- RSS fallback is enabled for symbols missing from GDELT in the same run.
- Fallback is skipped if runtime budget remaining is below configured threshold.
- Coverage breakdown includes `sec_docs`, `gdelt_docs`, `rss_docs`, and missing reasons.

## Failure Triage
1. Check `errors.ingestion` in final state summary.
2. If SEC calls fail: verify `SEC_USER_AGENT` format and throttle.
3. If GDELT calls fail or rate-limit: inspect fallback usage in `text_coverage_breakdown.json`.
4. If RSS calls fail: inspect `data/raw/ingestion/<run_id>/text_rss_news.json`.
5. If coverage < 85%: reduce symbols or inspect provider outage.
6. If parquet not generated: pipeline falls back to JSONL; install pandas+pyarrow for parquet.
