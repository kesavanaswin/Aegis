from __future__ import annotations

from typing import Any
from tools.registry import ToolRegistry


def register(registry: ToolRegistry) -> None:
    """Example plugin tool; explicitly opt in using --plugin plugins.example_plugin."""
    def word_count(args: dict[str, Any]) -> dict[str, int]:
        text = args.get("text")
        if not isinstance(text, str) or len(text) > 20000:
            raise ValueError("text must be a string of at most 20,000 characters")
        return {"words": len(text.split()), "characters": len(text)}

    registry.register(name="text_stats", toolset="example", description="Count words and characters in supplied text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False}, handler=word_count)
