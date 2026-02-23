# Feature 3: Factor Construction (DSL + Constraints)

## Goal
Transform Feature 2 hypotheses into formulaic factor candidates, validate them through a constrained DSL parser, and filter by originality and complexity constraints.

## Scope
- Minimal DSL parser + AST model.
- Candidate factor generation from hypotheses.
- Validation on allowed fields/functions/operators.
- Complexity and originality scoring.
- Artifact publishing + CLI.

## Locked DSL
Functions: `Rank(x)`, `Normalize(x)`, `WinsorizedSum(x, y, ...)`

Arithmetic: `+`, `-`, `*`, `/`

Fields: `close`, `volume`, `market_cap`, `returns_1d`, `returns_5d`

## Entry Point
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature3_factor_cli \
  --ingestion-run-id <feature1_run_id> \
  --hypothesis-run-id <feature2_run_id> \
  --run-id <feature3_run_id>
```

## Output Artifacts
- `artifacts/<run_id>/factors.json`
- `artifacts/<run_id>/factor_validation.json`
- `artifacts/<run_id>/factor_manifest.json`
