# Feature 2: Hypothesis Generation With Light Debate

## Goal
Generate 3 structured, ranked hypotheses from Feature 1 artifacts using role-specialized analyst agents, then refine via a 2-round max debate loop.

## Hard Gates
- Feature 1 artifacts must exist for `ingestion_run_id`.
- Feature 1 quality must be `passed=true`.
- `market_symbol_coverage >= 0.85`.
- `text_symbol_coverage >= 0.20`.

## Agent Tree
- `RootHypothesisWorkflow` (`SequentialAgent`)
- `HypothesisRunConfigAgent` (custom)
- `Feature1ArtifactLoaderAgent` (custom)
- `DataReadinessGateAgent` (custom)
- `ParallelRoleDrafting` (`ParallelAgent`)
  - `FundamentalAnalystAgent` (custom, Claude optional)
  - `SentimentAnalystAgent` (custom, Claude optional)
  - `ValuationAnalystAgent` (custom, Claude optional)
- `DebateLoop` (`LoopAgent`, max 2)
  - `DebateCoordinatorAgent` (custom)
  - `ConsensusSynthesisAgent` (custom)
- `HypothesisPublisherAgent` (custom)

## Entry Point
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature2_hypothesis_cli \
  --ingestion-run-id f1_smoke_s1_postfix_20260223 \
  --run-id f2_demo_20260223
```
