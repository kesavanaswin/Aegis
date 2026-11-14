from __future__ import annotations

import ast
import operator
from datetime import datetime, timezone
from typing import Any

from tools.registry import ToolRegistry

_BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("Exponent magnitude limited to 10.")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    raise ValueError("Only basic arithmetic is permitted.")


def calculate(args: dict[str, Any]) -> int | float:
    expression = args.get("expression")
    if not isinstance(expression, str) or not expression or len(expression) > 200:
        raise ValueError("Provide an arithmetic expression up to 200 characters.")
    result = _eval(ast.parse(expression, mode="eval"))
    return int(result) if isinstance(result, float) and result.is_integer() else result


def utc_now(_: dict[str, Any]) -> str:
    return datetime.now(timezone.utc).isoformat()


def register_builtins(registry: ToolRegistry) -> None:
    registry.register(name="calculate", toolset="safe", description="Calculate a basic arithmetic expression.",
        parameters={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"], "additionalProperties": False}, handler=calculate)
    registry.register(name="current_utc_time", toolset="safe", description="Return the current UTC time.",
        parameters={"type": "object", "properties": {}, "additionalProperties": False}, handler=utc_now)
