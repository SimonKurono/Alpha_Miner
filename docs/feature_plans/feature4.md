# Feature 4 Plan: Evaluation Loop (Backtest + Robustness + Decay)

## Goal
Implement a deterministic evaluation pipeline that scores Feature 3 factors on Feature 1 market artifacts, runs weekly rebalanced long-short backtests, and outputs promotion decisions with robustness and decay diagnostics.

## Locked Defaults
- Rebalance: `weekly`
- OOS: rolling `252` train / `63` test
- Benchmark: `SPY`
- Transaction cost: `10` bps times turnover
- Promotion profile (`moderate`):
  - Sharpe >= `0.8`
  - IR >= `0.3`
  - IC mean >= `0.01`
  - Max monthly turnover <= `0.80`

## Implemented Components
- Agents: `src/alpha_miner/agents/evaluation/`
  - run config, artifact loader, score computation
  - per-factor loop: single-factor backtest, robustness+decay, promotion judge
  - publisher + workflow composition
- Backtesting tools: `src/alpha_miner/tools/backtesting/`
  - DSL score executor (cross-sectional semantics)
  - portfolio construction and metrics
  - rolling OOS and decay analysis
- CLI: `src/alpha_miner/pipelines/feature4_evaluation_cli.py`
- Config: `configs/feature4_evaluation.yaml`
- Tests: `tests/unit/test_backtest_metrics.py`, `tests/unit/test_dsl_executor.py`, `tests/unit/test_promotion_rules.py`, `tests/unit/test_robustness_roll.py`, `tests/unit/test_decay_analysis.py`, `tests/integration/test_feature4_evaluation_e2e.py`

## Artifacts
- `artifacts/<run_id>/evaluation_results.json`
- `artifacts/<run_id>/evaluation_metrics_timeseries.json`
- `artifacts/<run_id>/evaluation_manifest.json`

## Notes
- Feature 4 currently evaluates all DSL-valid factors from Feature 3 validation output.
- Benchmark return defaults to `0.0` when benchmark series is unavailable in market inputs.
