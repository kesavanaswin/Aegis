from agent.memory import SessionStore
from agent.provider import OpenAICompatibleProvider
from plugins.example_plugin import register
from tools.builtin import calculate, register_builtins
from tools.registry import ToolRegistry
from tools.toolsets import SAFE_TOOLSET


def test_provider_loads_dotenv_before_reading_api_key(monkeypatch):
    import openai
    import dotenv

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        dotenv,
        "load_dotenv",
        lambda: monkeypatch.setenv("OPENAI_API_KEY", "test-key"),
    )
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: kwargs)

    provider = OpenAICompatibleProvider()

    assert provider.client["api_key"] == "test-key"


def test_calculator_supports_arithmetic():
    assert calculate({"expression": "2 + 3 * 4"}) == 14


def test_calculator_rejects_python_code():
    try:
        calculate({"expression": "__import__('os').system('echo unsafe')"})
    except (ValueError, SyntaxError):
        pass
    else:
        raise AssertionError("Non-arithmetic input was accepted")


def test_toolset_schemas_are_allowlisted():
    registry = ToolRegistry()
    register_builtins(registry)
    assert {item["function"]["name"] for item in registry.schemas(set(SAFE_TOOLSET))} == set(SAFE_TOOLSET)


def test_plugin_registration_is_explicit():
    registry = ToolRegistry()
    register(registry)
    assert registry.names_for_toolset("example") == {"text_stats"}
    assert registry.schemas(set()) == []


def test_session_store_roundtrip_and_clear(tmp_path):
    store = SessionStore(tmp_path / "sessions.sqlite3")
    store.append("case-1", {"role": "user", "content": "hello"})
    assert store.load("case-1") == [{"role": "user", "content": "hello"}]
    store.clear("case-1")
    assert store.load("case-1") == []
