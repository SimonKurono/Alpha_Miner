# Alpha Miner Research Note

- Run ID: `f5_strict_20260225`
- As of Date: `2026-02-25`

## Executive Summary
Evaluation run `f4_strict_20260225` produced 10 factor result(s); 1 met promotion thresholds. Report includes 1 selected factor(s). Selected 1 promoted factor(s) from evaluation results for reporting.

## Methodology
Factors were evaluated in Feature 4 using deterministic score computation, weekly-rebalanced long-short portfolio construction, 10 bps turnover-based transaction costs, rolling out-of-sample robustness checks, and decay diagnostics.

## Selected Factors
| factor_id | expression | promoted | sharpe | ir | ic_mean | turnover_monthly_max | oos_score | decay_score | composite_score | risk_tags |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| fct_003 | `Normalize(volume)` | yes | 0.9545 | 0.9545 | 0.0576 | 0.5000 | 0.7661 | 1.0000 | 0.7990 | - |

## Key Risks
- Prototype pipeline currently uses temporary text coverage gate (0.10) pending upstream stability restoration.
- Backtest results are historical simulations and can be sensitive to universe, costs, and data quality assumptions.

## Disclaimer
Alpha Miner is an educational and research tool only. This output is not financial advice and should not be used as a sole basis for investment decisions.

## Appendix Metrics
```json
{
  "lineage": {
    "evaluation_run_id": "f4_strict_20260225",
    "factor_run_id": "f3_strict_20260225",
    "hypothesis_run_id": null,
    "ingestion_run_id": "f1_strict_s2_20260225"
  },
  "promoted_selected_count": 1,
  "selected_factor_ids": [
    "fct_003"
  ],
  "selection": {
    "fallback_used": false,
    "policy": "promoted_plus_top_fallback",
    "promoted_source_count": 1,
    "selected_count": 1,
    "source_result_count": 10
  }
}
```
