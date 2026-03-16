# Full-Chain Sign-Off Report (2026-02-25)

## Objective
Confirm canonical end-to-end pipeline execution under strict gate policy and produce GO/NO_GO decision for baseline project sign-off.

Canonical lineage:
- Ingestion: `f1_strict_s2_20260225`
- Hypothesis: `f2_strict_20260225`
- Factors: `f3_strict_20260225`
- Evaluation: `f4_strict_20260225`
- Report: `f5_strict_20260225`

## Feature 2 Strict Gate Restoration
- `configs/feature2_hypothesis.yaml`: `text_coverage_min` restored to `0.20`
- `src/alpha_miner/agents/hypothesis_generation/config_loader.py`: fallback default restored to `0.20`
- Runbook updated: `docs/runbooks/feature2_hypothesis.md`

## Canonical Run Results

### F2 — Hypothesis
- Run ID: `f2_strict_20260225`
- Runtime (`/usr/bin/time -p`): `real=3.12s`, `user=1.36s`, `sys=0.25s`
- Pipeline duration: `0.031010s`
- Gate: `passed=true`, `market_symbol_coverage=1.00`, `text_symbol_coverage=0.80`
- Output: `artifacts/f2_strict_20260225/hypothesis_manifest.json`

### F3 — Factor Construction
- Run ID: `f3_strict_20260225`
- Runtime (`/usr/bin/time -p`): `real=1.47s`, `user=1.31s`, `sys=0.14s`
- Pipeline duration: `0.007241s`
- Candidates: `10`, accepted: `3`, rejected: `7`
- Output: `artifacts/f3_strict_20260225/factor_manifest.json`

### F4 — Evaluation
- Run ID: `f4_strict_20260225`
- Runtime (`/usr/bin/time -p`): `real=2.76s`, `user=2.47s`, `sys=0.28s`
- Pipeline duration: `1.083479s`
- Results: `10`, promoted: `1`
- Output: `artifacts/f4_strict_20260225/evaluation_manifest.json`

### F5 — Report
- Run ID: `f5_strict_20260225`
- Runtime (`/usr/bin/time -p`): `real=1.43s`, `user=1.29s`, `sys=0.13s`
- Pipeline duration: `0.005942s`
- Selected factors: `1`
- Quality: `passed=true`, `warnings=[]`, `failures=[]`
- Outputs:
  - `artifacts/f5_strict_20260225/report_manifest.json`
  - `artifacts/f5_strict_20260225/research_note.md`
  - `artifacts/f5_strict_20260225/report_quality.json`

## GO Rule Evaluation
1. Both strict F1 runs pass thresholds: `PASS`
2. F2 strict default gate (0.20) active and passed: `PASS`
3. Canonical F2→F5 chain completed with no fatal errors: `PASS`
4. Validation artifacts and tracking updates published: `PASS`

## Final Decision
- Classification: `GO`
- Baseline status: strict-gate canonical chain is sign-off ready for continued UI/deployment hardening.

## Residual Risks
1. GDELT throttling remains frequent; SEC currently carries text coverage in canonical runs.
2. RSS fallback is implemented, but historical-window usefulness is limited by feed recency.
3. Temporary quality bypass is removed; future regressions in SEC yield can re-open gate risk.
