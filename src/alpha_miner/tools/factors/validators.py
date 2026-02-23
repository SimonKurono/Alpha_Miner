"""AST validation for allowed Feature 3 DSL operations and fields."""

from __future__ import annotations

from dataclasses import dataclass, field

from alpha_miner.tools.factors.ast_nodes import BinaryOp, FunctionCall, Identifier, AstNode, iter_ast_nodes

ALLOWED_FUNCTIONS = {"Rank", "Normalize", "WinsorizedSum"}
ALLOWED_FIELDS = {"close", "volume", "market_cap", "returns_1d", "returns_5d"}
ALLOWED_ARITHMETIC = {"+", "-", "*", "/"}


@dataclass
class ValidationReport:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_factor_ast(ast: AstNode) -> ValidationReport:
    errors: list[str] = []

    for node in iter_ast_nodes(ast):
        if isinstance(node, BinaryOp) and node.op not in ALLOWED_ARITHMETIC:
            errors.append(f"Unsupported binary operator: {node.op}")

        if isinstance(node, Identifier) and node.name not in ALLOWED_FIELDS:
            errors.append(f"Unsupported data field: {node.name}")

        if isinstance(node, FunctionCall):
            if node.name not in ALLOWED_FUNCTIONS:
                errors.append(f"Unsupported function: {node.name}")
            else:
                argc = len(node.args)
                if node.name in {"Rank", "Normalize"} and argc != 1:
                    errors.append(f"Function {node.name} expects exactly 1 arg")
                if node.name == "WinsorizedSum" and argc < 2:
                    errors.append("Function WinsorizedSum expects at least 2 args")

    return ValidationReport(passed=len(errors) == 0, errors=errors, warnings=[])
