"""Stable interfaces for Feature 3 factor tooling."""

from __future__ import annotations

from alpha_miner.tools.factors.ast_nodes import AstNode
from alpha_miner.tools.factors.dsl_parser import parse_factor_expression
from alpha_miner.tools.factors.scoring import (
    compute_complexity_score,
    compute_originality_score,
    score_hypothesis_alignment,
)
from alpha_miner.tools.factors.validators import ValidationReport, validate_factor_ast

__all__ = [
    "AstNode",
    "ValidationReport",
    "parse_factor_expression",
    "validate_factor_ast",
    "compute_complexity_score",
    "compute_originality_score",
    "score_hypothesis_alignment",
]
