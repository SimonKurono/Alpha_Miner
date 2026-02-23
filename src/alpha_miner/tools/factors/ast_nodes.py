"""AST node definitions and helpers for Feature 3 factor DSL."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class AstNode:
    node_type: str


@dataclass
class Identifier(AstNode):
    name: str

    def __init__(self, name: str):
        super().__init__(node_type="Identifier")
        self.name = name


@dataclass
class NumberLiteral(AstNode):
    value: float

    def __init__(self, value: float):
        super().__init__(node_type="NumberLiteral")
        self.value = float(value)


@dataclass
class FunctionCall(AstNode):
    name: str
    args: list[AstNode] = field(default_factory=list)

    def __init__(self, name: str, args: list[AstNode]):
        super().__init__(node_type="FunctionCall")
        self.name = name
        self.args = args


@dataclass
class BinaryOp(AstNode):
    op: str
    left: AstNode
    right: AstNode

    def __init__(self, op: str, left: AstNode, right: AstNode):
        super().__init__(node_type="BinaryOp")
        self.op = op
        self.left = left
        self.right = right


@dataclass
class UnaryOp(AstNode):
    op: str
    operand: AstNode

    def __init__(self, op: str, operand: AstNode):
        super().__init__(node_type="UnaryOp")
        self.op = op
        self.operand = operand


@dataclass
class ArgList(AstNode):
    args: list[AstNode] = field(default_factory=list)

    def __init__(self, args: list[AstNode]):
        super().__init__(node_type="ArgList")
        self.args = args


@dataclass
class ExpressionRoot(AstNode):
    expr: AstNode

    def __init__(self, expr: AstNode):
        super().__init__(node_type="ExpressionRoot")
        self.expr = expr


@dataclass
class ValidationErrorNode(AstNode):
    message: str

    def __init__(self, message: str):
        super().__init__(node_type="ValidationErrorNode")
        self.message = message


@dataclass
class ConstraintTag(AstNode):
    tag: str

    def __init__(self, tag: str):
        super().__init__(node_type="ConstraintTag")
        self.tag = tag


@dataclass
class MetadataNode(AstNode):
    data: dict[str, Any]

    def __init__(self, data: dict[str, Any]):
        super().__init__(node_type="MetadataNode")
        self.data = data


def iter_ast_nodes(node: AstNode) -> Iterable[AstNode]:
    yield node
    if isinstance(node, ExpressionRoot):
        yield from iter_ast_nodes(node.expr)
    elif isinstance(node, BinaryOp):
        yield from iter_ast_nodes(node.left)
        yield from iter_ast_nodes(node.right)
    elif isinstance(node, UnaryOp):
        yield from iter_ast_nodes(node.operand)
    elif isinstance(node, FunctionCall):
        for arg in node.args:
            yield from iter_ast_nodes(arg)
    elif isinstance(node, ArgList):
        for arg in node.args:
            yield from iter_ast_nodes(arg)


def ast_depth(node: AstNode) -> int:
    if isinstance(node, ExpressionRoot):
        return 1 + ast_depth(node.expr)
    if isinstance(node, BinaryOp):
        return 1 + max(ast_depth(node.left), ast_depth(node.right))
    if isinstance(node, UnaryOp):
        return 1 + ast_depth(node.operand)
    if isinstance(node, FunctionCall):
        if not node.args:
            return 1
        return 1 + max(ast_depth(arg) for arg in node.args)
    if isinstance(node, ArgList):
        if not node.args:
            return 1
        return 1 + max(ast_depth(arg) for arg in node.args)
    return 1


def ast_serialize(node: AstNode) -> str:
    if isinstance(node, ExpressionRoot):
        return f"R({ast_serialize(node.expr)})"
    if isinstance(node, BinaryOp):
        return f"B({node.op},{ast_serialize(node.left)},{ast_serialize(node.right)})"
    if isinstance(node, UnaryOp):
        return f"U({node.op},{ast_serialize(node.operand)})"
    if isinstance(node, FunctionCall):
        inner = ",".join(ast_serialize(arg) for arg in node.args)
        return f"F({node.name},{inner})"
    if isinstance(node, Identifier):
        return f"I({node.name})"
    if isinstance(node, NumberLiteral):
        return f"N({node.value:g})"
    if isinstance(node, ArgList):
        return "A(" + ",".join(ast_serialize(arg) for arg in node.args) + ")"
    if isinstance(node, ValidationErrorNode):
        return f"E({node.message})"
    if isinstance(node, ConstraintTag):
        return f"C({node.tag})"
    if isinstance(node, MetadataNode):
        return f"M({sorted(node.data.items())})"
    return node.node_type
