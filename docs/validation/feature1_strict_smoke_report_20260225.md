# Feature 1 Strict Smoke Report (2026-02-25)

## Objective
Validate strict-gate readiness for Feature 2 by confirming Feature 1 market/text coverage and runtime constraints on both canonical smoke windows.

Gate requirements:
1. `runtime <= 300s`
2. `market_symbol_coverage >= 0.85`
3. `text_symbol_coverage >= 0.20`
4. manifest + quality + coverage breakdown artifacts exist

## Preflight
- `SEC_USER_AGENT` provided in run environment: yes
- Endpoint checks (live):
  - Stooq: `200`
  - SEC ticker map: `200`
  - SEC submissions: `200`
  - SEC companyfacts: `200`
  - GDELT doc API: `200`

## Run Matrix
Symbols: `AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,UNH,BRK.B`

### Run S1
- Run ID: `f1_strict_s1_20260225`
- Window: `2024-01-01` to `2024-12-31`
- Runtime (`/usr/bin/time -p`): `real=58.77s`, `user=9.84s`, `sys=0.46s`
- Pipeline duration (`run.meta.duration_sec`): `56.352603s`
- Quality:
  - `market_symbol_coverage=1.00`
  - `text_symbol_coverage=0.80`
  - `passed=true`
- Artifacts present:
  - `artifacts/f1_strict_s1_20260225/ingestion_manifest.json`
  - `artifacts/f1_strict_s1_20260225/ingestion_quality.json`
  - `artifacts/f1_strict_s1_20260225/text_coverage_breakdown.json`

### Run S2
- Run ID: `f1_strict_s2_20260225`
- Window: `2020-01-01` to `2024-12-31`
- Runtime (`/usr/bin/time -p`): `real=23.82s`, `user=9.99s`, `sys=0.50s`
- Pipeline duration (`run.meta.duration_sec`): `21.106027s`
- Quality:
  - `market_symbol_coverage=1.00`
  - `text_symbol_coverage=0.80`
  - `passed=true`
- Artifacts present:
  - `artifacts/f1_strict_s2_20260225/ingestion_manifest.json`
  - `artifacts/f1_strict_s2_20260225/ingestion_quality.json`
  - `artifacts/f1_strict_s2_20260225/text_coverage_breakdown.json`

## Observability Notes
- GDELT was rate-limited during both runs; RSS fallback did not add in-window docs for these windows.
- SEC 10-K/10-Q coverage carried text coverage to `0.80` on both runs.
- Top missing reasons from coverage breakdown:
  - `gdelt_missing: 10`
  - `gdelt_rate_limited: 10`
  - `rss_missing: 10`
  - `no_text_docs: 2`
  - `sec_missing: 1`

## Decision
- Classification: `GO`
- Result: strict Feature 1 prerequisites are satisfied for both canonical smoke windows.
