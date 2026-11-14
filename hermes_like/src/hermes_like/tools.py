from __future__ import annotations

import ast
import operator
from datetime import datetime, timezone
from typing import Any

from .registry import ToolRegistry


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _calculate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _calculate_node(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left, right = _calculate_node(node.left), _calculate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent magnitude is limited to 10.")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_calculate_node(node.operand))
    raise ValueError("Only basic arithmetic expressions are supported.")


def calculate(args: dict[str, Any]) -> int | float:
    expression = args.get("expression")
    if not isinstance(expression, str) or not expression or len(expression) > 200:
        raise ValueError("Provide an arithmetic expression of at most 200 characters.")
    result = _calculate_node(ast.parse(expression, mode="eval"))
    if isinstance(result, float) and not result.is_integer():
        return result
    return int(result)


def current_utc_time(_: dict[str, Any]) -> str:
    return datetime.now(timezone.utc).isoformat()


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        name="calculate",
        description="Evaluate a basic arithmetic expression.",
        parameters={
            "type": "object",
            "properties": {"expression": {"type": "string", "description": "Arithmetic using numbers and +, -, *, /, **."}},
            "required": ["expression"],
            "additionalProperties": False,
        },
        handler=calculate,
    )
    registry.register(
        name="current_utc_time",
        description="Get the current UTC time.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=current_utc_time,
    )
    return registry
