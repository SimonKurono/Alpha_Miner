"""Feature 1 root workflow composed from ADK workflow agents."""

from __future__ import annotations

from google.adk.agents import ParallelAgent, SequentialAgent

from alpha_miner.agents.data_ingestion.artifact_publisher_agent import ArtifactPublisherAgent
from alpha_miner.agents.data_ingestion.market_agent import MarketDataIngestionAgent
from alpha_miner.agents.data_ingestion.quality_gate_agent import IngestionQualityGateAgent
from alpha_miner.agents.data_ingestion.run_config_agent import RunConfigAgent
from alpha_miner.agents.data_ingestion.text_agent import TextDataIngestionAgent


def build_root_ingestion_workflow(config_path: str = "configs/feature1_ingestion.yaml") -> SequentialAgent:
    run_config = RunConfigAgent(
        name="RunConfigAgent",
        description="Loads run config into session.state",
        config_path=config_path,
    )

    market = MarketDataIngestionAgent(
        name="MarketDataIngestionAgent",
        description="Fetches market prices and derives returns/market_cap",
    )

    text = TextDataIngestionAgent(
        name="TextDataIngestionAgent",
        description="Fetches SEC filings and GDELT documents",
    )

    ingestion_parallel = ParallelAgent(
        name="ParallelIngestion",
        description="Runs market and text ingestion concurrently",
        sub_agents=[market, text],
    )

    quality_gate = IngestionQualityGateAgent(
        name="IngestionQualityGateAgent",
        description="Validates ingestion outputs",
    )

    artifact_publisher = ArtifactPublisherAgent(
        name="ArtifactPublisherAgent",
        description="Publishes ingestion manifest and quality artifacts",
    )

    return SequentialAgent(
        name="RootIngestionWorkflow",
        description="Feature 1 pipeline: run config -> parallel ingestion -> quality gate -> artifacts",
        sub_agents=[run_config, ingestion_parallel, quality_gate, artifact_publisher],
    )


root_agent = build_root_ingestion_workflow()
