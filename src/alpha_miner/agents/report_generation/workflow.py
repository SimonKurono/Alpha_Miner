"""Feature 5 root workflow composed from ADK workflow agents."""

from __future__ import annotations

from google.adk.agents import SequentialAgent

from alpha_miner.agents.report_generation.artifact_loader_agent import ReportArtifactLoaderAgent
from alpha_miner.agents.report_generation.artifact_publisher_agent import ReportPublisherAgent
from alpha_miner.agents.report_generation.data_prep_agent import ReportDataPrepAgent
from alpha_miner.agents.report_generation.quality_gate_agent import ReportQualityGateAgent
from alpha_miner.agents.report_generation.report_draft_agent import ReportDraftAgent
from alpha_miner.agents.report_generation.run_config_agent import ReportRunConfigAgent


def build_root_report_workflow(config_path: str = "configs/feature5_report.yaml") -> SequentialAgent:
    return SequentialAgent(
        name="RootReportWorkflow",
        description=(
            "Feature 5 pipeline: run config -> load evaluation artifacts -> "
            "select factors -> draft report -> quality gate -> publish"
        ),
        sub_agents=[
            ReportRunConfigAgent(
                name="ReportRunConfigAgent",
                description="Loads Feature 5 run configuration",
                config_path=config_path,
            ),
            ReportArtifactLoaderAgent(
                name="ReportArtifactLoaderAgent",
                description="Loads Feature 4 evaluation artifacts",
            ),
            ReportDataPrepAgent(
                name="ReportDataPrepAgent",
                description="Selects factors for report inclusion",
            ),
            ReportDraftAgent(
                name="ReportDraftAgent",
                description="Builds deterministic report payload and markdown",
            ),
            ReportQualityGateAgent(
                name="ReportQualityGateAgent",
                description="Validates report sections and disclaimer",
            ),
            ReportPublisherAgent(
                name="ReportPublisherAgent",
                description="Writes report artifacts and manifest",
            ),
        ],
    )


root_agent = build_root_report_workflow()
