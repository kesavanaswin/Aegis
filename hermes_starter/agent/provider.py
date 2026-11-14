from __future__ import annotations

import os
from typing import Any


class OpenAICompatibleProvider:
    """Thin adapter returning normalized assistant messages from OpenAI SDK."""

    def __init__(self, model: str | None = None, client: Any | None = None):
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("Install requirements.txt to use the model provider.") from exc
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("Set OPENAI_API_KEY before starting the agent.")
            client = OpenAI(api_key=api_key, base_url=os.environ.get("OPENAI_BASE_URL") or None)
        self.client = client
        self.model = model or os.environ.get("HERMES_MODEL", "gpt-4o-mini")

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools or None,
            tool_choice="auto" if tools else "none",
        )
        message = response.choices[0].message
        tool_calls = []
        for call in message.tool_calls or []:
            tool_calls.append({
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            })
        return {"role": "assistant", "content": message.content, "tool_calls": tool_calls}
