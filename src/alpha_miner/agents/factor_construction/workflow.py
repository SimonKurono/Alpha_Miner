"""Feature 3 root workflow composed from ADK workflow agents."""

from __future__ import annotations

from google.adk.agents import SequentialAgent

from alpha_miner.agents.factor_construction.artifact_loader_agent import UpstreamArtifactLoaderAgent
from alpha_miner.agents.factor_construction.artifact_publisher_agent import FactorPublisherAgent
from alpha_miner.agents.factor_construction.dsl_validation_agent import DslValidationAgent
from alpha_miner.agents.factor_construction.factor_generation_agent import FactorGenerationAgent
from alpha_miner.agents.factor_construction.originality_complexity_agent import OriginalityComplexityAgent
from alpha_miner.agents.factor_construction.run_config_agent import FactorRunConfigAgent


def build_root_factor_workflow(config_path: str = "configs/feature3_factor.yaml") -> SequentialAgent:
    return SequentialAgent(
        name="RootFactorWorkflow",
        description=(
            "Feature 3 pipeline: run config -> load artifacts -> factor generation -> "
            "dsl validation -> originality/complexity -> publish"
        ),
        sub_agents=[
            FactorRunConfigAgent(
                name="FactorRunConfigAgent",
                description="Loads Feature 3 run configuration",
                config_path=config_path,
            ),
            UpstreamArtifactLoaderAgent(
                name="UpstreamArtifactLoaderAgent",
                description="Loads hypotheses and ingestion manifests",
            ),
            FactorGenerationAgent(
                name="FactorGenerationAgent",
                description="Generates candidate factor expressions from hypotheses",
            ),
            DslValidationAgent(
                name="DslValidationAgent",
                description="Parses and validates DSL expressions",
            ),
            OriginalityComplexityAgent(
                name="OriginalityComplexityAgent",
                description="Scores and filters candidates by originality and complexity",
            ),
            FactorPublisherAgent(
                name="FactorPublisherAgent",
                description="Publishes Feature 3 artifacts and manifest",
            ),
        ],
    )


root_agent = build_root_factor_workflow()
