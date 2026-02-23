"""Stable interfaces for Feature 2 hypothesis tools."""

from __future__ import annotations

from alpha_miner.agents.hypothesis_generation.schemas import HypothesisCandidate
from alpha_miner.tools.hypothesis.gating import apply_hypothesis_gate
from alpha_miner.tools.hypothesis.input_snapshot import (
    load_hypothesis_input_snapshot,
    load_ingestion_manifest,
    load_ingestion_quality,
)
from alpha_miner.tools.hypothesis.scoring import score_hypothesis

__all__ = [
    "load_ingestion_manifest",
    "load_ingestion_quality",
    "load_hypothesis_input_snapshot",
    "score_hypothesis",
    "apply_hypothesis_gate",
    "HypothesisCandidate",
]
