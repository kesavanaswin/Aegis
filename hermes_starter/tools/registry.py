from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    toolset: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]

    def schema(self) -> dict[str, Any]:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description, "parameters": self.parameters}}


class ToolRegistry:
    """Explicit tool registry; an enabled-name set is the execution boundary."""

    def __init__(self, max_result_chars: int = 12000):
        self._tools: dict[str, Tool] = {}
        self.max_result_chars = max_result_chars

    def register(self, *, name: str, toolset: str, description: str,
                 parameters: dict[str, Any], handler: Callable[[dict[str, Any]], Any]) -> None:
        if not name or name in self._tools:
            raise ValueError(f"Empty or duplicate tool name: {name!r}")
        self._tools[name] = Tool(name, toolset, description, parameters, handler)

    def schemas(self, enabled_tools: set[str]) -> list[dict[str, Any]]:
        return [tool.schema() for name, tool in self._tools.items() if name in enabled_tools]

    def names_for_toolset(self, toolset: str) -> set[str]:
        return {name for name, tool in self._tools.items() if tool.toolset == toolset}

    def dispatch(self, name: str, arguments_json: str, enabled_tools: set[str]) -> str:
        tool = self._tools.get(name)
        if tool is None or name not in enabled_tools:
            return json.dumps({"ok": False, "error": f"Tool not enabled: {name}"})
        try:
            args = json.loads(arguments_json or "{}")
            if not isinstance(args, dict):
                raise ValueError("Arguments must be a JSON object.")
            result = tool.handler(args)
            output = json.dumps({"ok": True, "result": result}, ensure_ascii=False, default=str)
            return output[:self.max_result_chars]
        except Exception as exc:
            return json.dumps({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
