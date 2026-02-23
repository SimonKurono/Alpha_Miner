# Feature 1 Live Smoke Validation Report
Date: 2026-02-21

## Scope
Live-provider smoke validation for Feature 1 ingestion on fixed 10-symbol basket:
`AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,UNH,BRK.B`

Runs:
- `f1_smoke_s1_20260221` (2024-01-01 to 2024-12-31)
- `f1_smoke_s2_20260221` (2020-01-01 to 2024-12-31)

## Preflight
- Dependencies: `google.adk`, `requests`, `yaml`, `tenacity` available
- Endpoint checks:
  - Stooq: `200`
  - SEC tickers: `200`
  - GDELT doc API: `429`

## Results

### S1 (`f1_smoke_s1_20260221`)
- Runtime: `real 535.19s`
- `run_meta.duration_sec`: `532.110117`
- Manifest: present (`artifacts/f1_smoke_s1_20260221/ingestion_manifest.json`)
- Quality report: present (`artifacts/f1_smoke_s1_20260221/ingestion_quality.json`)
- Quality: `passed=true`, `market_coverage=1.0`, `text_coverage=0.0`
- Warnings:
  - `Low text symbol coverage: 0.00%`
  - `No text rows were produced`
- Errors:
  - SEC missing all symbols
  - GDELT missing all symbols

### S2 (`f1_smoke_s2_20260221`)
- Runtime: `real 372.85s`
- `run_meta.duration_sec`: `370.343936`
- Manifest: present (`artifacts/f1_smoke_s2_20260221/ingestion_manifest.json`)
- Quality report: present (`artifacts/f1_smoke_s2_20260221/ingestion_quality.json`)
- Quality: `passed=true`, `market_coverage=1.0`, `text_coverage=0.0`
- Warnings:
  - `Low text symbol coverage: 0.00%`
  - `No text rows were produced`
- Errors:
  - SEC missing all symbols
  - GDELT missing all symbols

## Classification
- Final: `NO_GO`

Reasoning:
1. Repeated source failures (SEC/GDELT) across both runs.
2. Runtime exceeded target budget (`300s`) in both runs.
3. Text pipeline produced zero rows in both runs.

## Recommended Immediate Remediation
1. Fix SEC submissions/companyfacts request handling for `data.sec.gov` endpoints.
2. Add explicit GDELT 429 handling with tighter retry budget and skip policy.
3. Enforce hard `max_runtime_sec` termination in workflow.
4. Re-run same smoke matrix and reclassify.
