from __future__ import annotations

from agent.memory import SessionStore
from agent.runtime import Agent
from tools.registry import ToolRegistry


class FakeProvider:
    def __init__(self):
        self.turn = 0

    def complete(self, messages, tools):
        self.turn += 1
        if self.turn == 1:
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": "double", "arguments": '{"value": 4}'},
            }]}
        return {"role": "assistant", "content": "The result is 8.", "tool_calls": []}


def test_runtime_tool_round_trip(tmp_path):
    registry = ToolRegistry()
    registry.register(name="double", toolset="test", description="Double a number.",
        parameters={"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]},
        handler=lambda args: args["value"] * 2)
    provider = FakeProvider()
    store = SessionStore(tmp_path / "memory.sqlite3")
    agent = Agent(registry, store, {"double"}, provider=provider)
    assert agent.run_turn("s1", "double 4") == "The result is 8."
    history = store.load("s1")
    assert [item["role"] for item in history] == ["user", "assistant", "tool", "assistant"]


def test_disabled_tool_is_not_dispatched():
    registry = ToolRegistry()
    registry.register(name="hidden", toolset="hidden", description="Hidden.", parameters={"type": "object", "properties": {}}, handler=lambda _: "unexpected")
    result = registry.dispatch("hidden", "{}", set())
    assert '"ok": false' in result
    assert "not enabled" in result
