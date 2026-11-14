from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]

    def model_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Explicit allowlist of tools available to the model."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        if not name or name in self._tools:
            raise ValueError(f"Invalid or duplicate tool name: {name!r}")
        self._tools[name] = Tool(name, description, parameters, handler)

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.model_schema() for tool in self._tools.values()]

    def call(self, name: str, arguments_json: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"Tool not allowed: {name}"})
        try:
            arguments = json.loads(arguments_json or "{}")
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object.")
            result = tool.handler(arguments)
            return json.dumps({"ok": True, "result": result}, ensure_ascii=False)
        except Exception as exc:
            return json.dumps({
                "ok": False,
                "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            }, ensure_ascii=False)
