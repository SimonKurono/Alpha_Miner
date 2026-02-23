"""Recursive-descent parser for the minimal Feature 3 factor DSL."""

from __future__ import annotations

import re
from dataclasses import dataclass

from alpha_miner.tools.factors.ast_nodes import BinaryOp, ExpressionRoot, FunctionCall, Identifier, NumberLiteral, UnaryOp


_TOKEN_RE = re.compile(
    r"\s*(?:(?P<number>\d+(?:\.\d+)?)|(?P<identifier>[A-Za-z_][A-Za-z0-9_]*)|(?P<op>[+\-*/(),]))"
)


@dataclass
class Token:
    kind: str
    value: str


class DslParseError(ValueError):
    pass


class _Parser:
    def __init__(self, expr: str):
        self.expr = expr
        self.tokens = self._tokenize(expr)
        self.idx = 0

    @staticmethod
    def _tokenize(expr: str) -> list[Token]:
        pos = 0
        tokens: list[Token] = []
        while pos < len(expr):
            match = _TOKEN_RE.match(expr, pos)
            if not match:
                raise DslParseError(f"Unexpected token near: {expr[pos:pos+20]}")
            pos = match.end()
            if match.group("number"):
                tokens.append(Token("number", match.group("number")))
            elif match.group("identifier"):
                tokens.append(Token("identifier", match.group("identifier")))
            else:
                tokens.append(Token("op", match.group("op")))
        return tokens

    def _peek(self) -> Token | None:
        if self.idx >= len(self.tokens):
            return None
        return self.tokens[self.idx]

    def _take(self) -> Token:
        token = self._peek()
        if token is None:
            raise DslParseError("Unexpected end of expression")
        self.idx += 1
        return token

    def _expect_op(self, value: str) -> None:
        token = self._take()
        if token.kind != "op" or token.value != value:
            raise DslParseError(f"Expected '{value}', got '{token.value}'")

    def parse(self) -> ExpressionRoot:
        expr = self._parse_expr()
        if self._peek() is not None:
            raise DslParseError(f"Unexpected trailing token: {self._peek().value}")
        return ExpressionRoot(expr)

    def _parse_expr(self):
        node = self._parse_term()
        while True:
            token = self._peek()
            if token and token.kind == "op" and token.value in {"+", "-"}:
                op = self._take().value
                rhs = self._parse_term()
                node = BinaryOp(op, node, rhs)
                continue
            break
        return node

    def _parse_term(self):
        node = self._parse_unary()
        while True:
            token = self._peek()
            if token and token.kind == "op" and token.value in {"*", "/"}:
                op = self._take().value
                rhs = self._parse_unary()
                node = BinaryOp(op, node, rhs)
                continue
            break
        return node

    def _parse_unary(self):
        token = self._peek()
        if token and token.kind == "op" and token.value in {"+", "-"}:
            op = self._take().value
            operand = self._parse_unary()
            if op == "+":
                return operand
            return UnaryOp(op, operand)
        return self._parse_primary()

    def _parse_primary(self):
        token = self._peek()
        if token is None:
            raise DslParseError("Expected expression term")

        if token.kind == "number":
            self._take()
            return NumberLiteral(float(token.value))

        if token.kind == "identifier":
            ident = self._take().value
            nxt = self._peek()
            if nxt and nxt.kind == "op" and nxt.value == "(":
                self._expect_op("(")
                args = self._parse_arg_list()
                self._expect_op(")")
                return FunctionCall(ident, args)
            return Identifier(ident)

        if token.kind == "op" and token.value == "(":
            self._take()
            node = self._parse_expr()
            self._expect_op(")")
            return node

        raise DslParseError(f"Unexpected token: {token.value}")

    def _parse_arg_list(self):
        args = []
        token = self._peek()
        if token and token.kind == "op" and token.value == ")":
            return args

        args.append(self._parse_expr())
        while True:
            token = self._peek()
            if token and token.kind == "op" and token.value == ",":
                self._take()
                args.append(self._parse_expr())
                continue
            break
        return args


def parse_factor_expression(expr: str) -> ExpressionRoot:
    if not str(expr).strip():
        raise DslParseError("Expression cannot be empty")
    parser = _Parser(expr)
    return parser.parse()
