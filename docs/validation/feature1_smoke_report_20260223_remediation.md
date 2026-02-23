# Feature 1 Remediation Smoke Report
Date: 2026-02-23

## Objective
Validate SEC run-window alignment remediation and confirm whether Feature 1 can satisfy Feature 2 strict gate prerequisites.

## Run Matrix
Universe (fixed 10 symbols):
`AAPL,MSFT,NVDA,AMZN,GOOGL,META,JPM,XOM,UNH,BRK.B`

Runs:
- `f1_smoke_s1_postfix_20260223` (`2024-01-01` to `2024-12-31`)
- `f1_smoke_s2_postfix_20260223` (`2020-01-01` to `2024-12-31`)

Runtime budget per run: `300s`

## Code Changes Exercised
1. `SecFilingsRequest` now supports `start_date`, `end_date`, `anchor_mode`.
2. `TextDataIngestionAgent` sends SEC requests with `anchor_mode=run_window`.
3. `fetch_sec_filings()` uses inclusive run-window filtering with lookback fallback.
4. New artifact: `artifacts/<run_id>/text_coverage_breakdown.json`.

## Results
### S1 (`f1_smoke_s1_postfix_20260223`)
- Runtime: `real 90.80s` (`duration_sec=88.38`)
- Manifest + quality: present
- Market coverage: `1.00`
- Text coverage: `0.10`
- Quality: `passed=true` with warning
- Top missing reasons: `gdelt_missing=10`, `sec_missing=9`, `no_text_docs=9`

### S2 (`f1_smoke_s2_postfix_20260223`)
- Runtime: `real 238.52s` (`duration_sec=236.36`)
- Manifest + quality: present
- Market coverage: `1.00`
- Text coverage: `0.10`
- Quality: `passed=true` with warning
- Top missing reasons: `gdelt_missing=10`, `sec_missing=9`, `no_text_docs=9`

## Gate Evaluation
Feature 1 runtime and market coverage constraints pass, but text coverage remains below Feature 2 strict requirement.

- Required for Feature 2: `text_symbol_coverage >= 0.20`
- Observed: `0.10` on both runs

## Classification
**NO_GO for Feature 2 full-closure prerequisites** (strict gate unmet).

## Next Remediation Actions
1. Add SEC provider request pacing/jitter between per-symbol `data.sec.gov/submissions` calls and classify SEC failures by status/type.
2. Add fallback text source when GDELT fully misses (RSS/news API fallback) to guarantee at least 2/10 symbol text coverage.
3. Re-run the same S1/S2 matrix after remediation.
