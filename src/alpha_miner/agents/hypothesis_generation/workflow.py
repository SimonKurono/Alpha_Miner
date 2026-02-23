"""Feature 2 root workflow composed from ADK workflow agents."""

from __future__ import annotations

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from alpha_miner.agents.hypothesis_generation.artifact_loader_agent import Feature1ArtifactLoaderAgent
from alpha_miner.agents.hypothesis_generation.artifact_publisher_agent import HypothesisPublisherAgent
from alpha_miner.agents.hypothesis_generation.consensus_synthesis_agent import ConsensusSynthesisAgent
from alpha_miner.agents.hypothesis_generation.data_readiness_gate_agent import DataReadinessGateAgent
from alpha_miner.agents.hypothesis_generation.debate_coordinator_agent import DebateCoordinatorAgent
from alpha_miner.agents.hypothesis_generation.role_agents import RoleHypothesisAgent
from alpha_miner.agents.hypothesis_generation.run_config_agent import HypothesisRunConfigAgent


def build_root_hypothesis_workflow(config_path: str = "configs/feature2_hypothesis.yaml") -> SequentialAgent:
    run_config = HypothesisRunConfigAgent(
        name="HypothesisRunConfigAgent",
        description="Loads Feature 2 run config into session.state",
        config_path=config_path,
    )

    artifact_loader = Feature1ArtifactLoaderAgent(
        name="Feature1ArtifactLoaderAgent",
        description="Loads Feature 1 manifest and quality artifacts",
    )

    readiness_gate = DataReadinessGateAgent(
        name="DataReadinessGateAgent",
        description="Applies hard quality gate before role generation",
    )

    fundamental = RoleHypothesisAgent(
        name="FundamentalAnalystAgent",
        description="Generates fundamental-tilted hypothesis",
        role_name="fundamental",
    )
    sentiment = RoleHypothesisAgent(
        name="SentimentAnalystAgent",
        description="Generates sentiment-tilted hypothesis",
        role_name="sentiment",
    )
    valuation = RoleHypothesisAgent(
        name="ValuationAnalystAgent",
        description="Generates valuation/liquidity hypothesis",
        role_name="valuation",
    )

    role_parallel = ParallelAgent(
        name="ParallelRoleDrafting",
        description="Runs role analysts in parallel",
        sub_agents=[fundamental, sentiment, valuation],
    )

    debate = LoopAgent(
        name="DebateLoop",
        description="Light debate and synthesis loop",
        sub_agents=[
            DebateCoordinatorAgent(
                name="DebateCoordinatorAgent",
                description="Controls round-robin consensus loop",
            ),
            ConsensusSynthesisAgent(
                name="ConsensusSynthesisAgent",
                description="Synthesizes consensus and top hypotheses",
            ),
        ],
        max_iterations=2,
    )

    publisher = HypothesisPublisherAgent(
        name="HypothesisPublisherAgent",
        description="Publishes Feature 2 artifacts and manifest",
    )

    return SequentialAgent(
        name="RootHypothesisWorkflow",
        description=(
            "Feature 2 pipeline: run config -> load artifacts -> readiness gate "
            "-> parallel role drafting -> debate loop -> publish"
        ),
        sub_agents=[run_config, artifact_loader, readiness_gate, role_parallel, debate, publisher],
    )


root_agent = build_root_hypothesis_workflow()
