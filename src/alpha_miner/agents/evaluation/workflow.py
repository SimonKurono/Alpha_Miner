"""Feature 4 root workflow composed from ADK workflow agents."""

from __future__ import annotations

from google.adk.agents import LoopAgent, SequentialAgent

from alpha_miner.agents.evaluation.artifact_loader_agent import EvalArtifactLoaderAgent
from alpha_miner.agents.evaluation.artifact_publisher_agent import EvalPublisherAgent
from alpha_miner.agents.evaluation.promotion_judge_agent import PromotionJudgeAgent
from alpha_miner.agents.evaluation.robustness_decay_agent import RobustnessDecayAgent
from alpha_miner.agents.evaluation.run_config_agent import EvalRunConfigAgent
from alpha_miner.agents.evaluation.score_computation_agent import ScoreComputationAgent
from alpha_miner.agents.evaluation.single_factor_backtest_agent import SingleFactorBacktestAgent


def build_root_evaluation_workflow(config_path: str = "configs/feature4_evaluation.yaml") -> SequentialAgent:
    loop = LoopAgent(
        name="BacktestLoopAgent",
        description="Iterates factor-level backtest + robustness/decay + promotion",
        sub_agents=[
            SingleFactorBacktestAgent(
                name="SingleFactorBacktestAgent",
                description="Runs one factor backtest per loop iteration",
            ),
            RobustnessDecayAgent(
                name="RobustnessDecayAgent",
                description="Computes rolling OOS robustness and decay diagnostics",
            ),
            PromotionJudgeAgent(
                name="PromotionJudgeAgent",
                description="Applies promotion rules and appends factor result",
            ),
        ],
        max_iterations=500,
    )

    return SequentialAgent(
        name="RootEvaluationWorkflow",
        description=(
            "Feature 4 pipeline: run config -> load artifacts -> compute scores -> "
            "looped factor evaluation -> publish"
        ),
        sub_agents=[
            EvalRunConfigAgent(
                name="EvalRunConfigAgent",
                description="Loads Feature 4 run configuration",
                config_path=config_path,
            ),
            EvalArtifactLoaderAgent(
                name="EvalArtifactLoaderAgent",
                description="Loads market + factor artifacts",
            ),
            ScoreComputationAgent(
                name="ScoreComputationAgent",
                description="Computes factor score tables from DSL",
            ),
            loop,
            EvalPublisherAgent(
                name="EvalPublisherAgent",
                description="Publishes evaluation results and manifest",
            ),
        ],
    )


root_agent = build_root_evaluation_workflow()
