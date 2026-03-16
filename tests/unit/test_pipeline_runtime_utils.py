from __future__ import annotations

from alpha_miner.pipelines.runtime_utils import canonical_app_name, validate_agent_health


class _Agent:
    def __init__(self, name: str):
        self.name = name


def test_canonical_app_name_prefers_root_agent_name():
    assert canonical_app_name(_Agent("RootEvaluationWorkflow"), "alpha_miner_feature4") == "RootEvaluationWorkflow"


def test_canonical_app_name_falls_back_when_missing():
    assert canonical_app_name(object(), "alpha_miner_featureX") == "alpha_miner_featureX"


def test_validate_agent_health_ok():
    report = validate_agent_health(_Agent("RootHypothesisWorkflow"), "RootHypothesisWorkflow")
    assert report.status == "ok"


def test_validate_agent_health_fails_for_generic_name():
    report = validate_agent_health(_Agent("agents"), "agents")
    assert report.status == "failed"
    assert "generic app_name" in str(report.failure_reason)

