# Feature 1 Post-Fix Smoke Validation Report
Date: 2026-02-23

## Scope
Step 1 completion validation for remediated Feature 1 ingestion pipeline using live providers.

Universe (fixed 10 symbols):
`AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,UNH,BRK.B`

Runs:
- `f1_smoke_s1_postfix_20260223` (2024-01-01 to 2024-12-31)
- `f1_smoke_s2_postfix_20260223` (2020-01-01 to 2024-12-31)

Gate requirements:
1. Runtime <= 300s for both runs
2. Market coverage >= 0.85 for both runs
3. Text coverage > 0 on at least one run (strict gate)
4. Manifest + quality artifacts exist for both runs

## Preflight
- `SEC_USER_AGENT`: set
- Dependencies:
  - `google.adk`: present
  - `requests`: present
  - `yaml`: present
  - `tenacity`: present
- Endpoint checks:
  - Stooq: `200`
  - SEC tickers: `200`
  - SEC submissions (`data.sec.gov`): `200`
  - SEC companyfacts (`data.sec.gov`): `200`
  - GDELT probe: `200` (live run still showed intermittent timeout behavior)

## Run Results

### Run S1: `f1_smoke_s1_postfix_20260223`
- Runtime (`/usr/bin/time -p`): `real 253.83s`, `user 9.46s`, `sys 0.43s`
- `run_meta.duration_sec`: `251.155566`
- Artifact checks:
  - `artifacts/f1_smoke_s1_postfix_20260223/ingestion_manifest.json`: present
  - `artifacts/f1_smoke_s1_postfix_20260223/ingestion_quality.json`: present
- Quality metrics:
  - `passed`: `true`
  - `market_symbol_coverage`: `1.0`
  - `text_symbol_coverage`: `0.1`
  - `warnings`: `['Low text symbol coverage: 10.00%']`
  - `failures`: `[]`
- Error summary:
  - SEC missing symbols: 9/10
  - GDELT missing symbols: 10/10

### Run S2: `f1_smoke_s2_postfix_20260223`
- Runtime (`/usr/bin/time -p`): `real 236.66s`, `user 9.30s`, `sys 0.33s`
- `run_meta.duration_sec`: `234.39146`
- Artifact checks:
  - `artifacts/f1_smoke_s2_postfix_20260223/ingestion_manifest.json`: present
  - `artifacts/f1_smoke_s2_postfix_20260223/ingestion_quality.json`: present
- Quality metrics:
  - `passed`: `true`
  - `market_symbol_coverage`: `1.0`
  - `text_symbol_coverage`: `0.1`
  - `warnings`: `['Low text symbol coverage: 10.00%']`
  - `failures`: `[]`
- Error summary:
  - SEC missing symbols: 9/10
  - GDELT missing symbols: 10/10

## Classification
Final result: **`GO_WITH_WARNINGS`**

Reasoning:
1. Both runs met runtime budget (`<=300s`).
2. Both runs met market coverage threshold (`>=0.85`).
3. Strict text gate passed (`text_symbol_coverage > 0`, observed `0.1` on both runs).
4. Warnings remain due low text coverage and unstable external text retrieval.

## Remaining Risks to Carry Forward
1. Text data reliability is low under live provider instability.
2. SEC filings selection currently yields coverage for only a small subset of symbols.
3. Additional observability (per-tool persisted latency/retry summary) still needed.

## Step 1 Completion Decision
**Step 1 is complete under strict gate with warning status (`GO_WITH_WARNINGS`).**
