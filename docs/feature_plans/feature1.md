# Feature 1: Parallel Data Ingestion

## Goal
Implement Stage 1 of Alpha Miner: parallel ingestion of market and text data, plus normalization, validation, and artifact publishing for downstream factor research workflows.

## Scope
- Universe loading for Top-100 S&P from `configs/feature1_ingestion.yaml`
- Parallel market + text ingestion using ADK `ParallelAgent`
- Normalized artifact persistence under `data/processed/ingestion/<run_id>/`
- Quality report + ingestion manifest under `artifacts/<run_id>/`

## Agent Tree
- `RootIngestionWorkflow` (`SequentialAgent`)
- `RunConfigAgent` (custom)
- `ParallelIngestion` (`ParallelAgent`)
  - `MarketDataIngestionAgent` (custom)
  - `TextDataIngestionAgent` (custom)
- `IngestionQualityGateAgent` (custom)
- `ArtifactPublisherAgent` (custom)

## Session State Keys
- `run.config`
- `run.meta`
- `ingestion.market.raw`
- `ingestion.text.raw`
- `ingestion.market.normalized`
- `ingestion.text.normalized`
- `ingestion.quality`
- `artifacts.ingestion.manifest`
- `errors.ingestion`

## Runtime Controls
- Retries: 3 attempts with exponential backoff (SEC/GDELT/Stooq)
- Request timeout: 30s
- Coverage gate: market symbol coverage must be >= 85%
- Partial failures are persisted in `errors.ingestion`

## Entry Point
```bash
PYTHONPATH=src python3 -m alpha_miner.pipelines.feature1_ingestion_cli --run-id feature1_demo
```
