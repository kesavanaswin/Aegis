from hermes_like.memory import MemoryStore
from hermes_like.tools import build_registry, calculate


def test_calculator_basic_arithmetic():
    assert calculate({"expression": "2 + 3 * 4"}) == 14


def test_calculator_rejects_code():
    try:
        calculate({"expression": "__import__('os').system('echo unsafe')"})
    except ValueError:
        pass
    else:
        raise AssertionError("Unexpectedly accepted non-arithmetic expression")


def test_registry_denies_unknown_tool():
    result = build_registry().call("run_shell", "{}")
    assert '"error"' in result
    assert "not allowed" in result


def test_memory_session_round_trip(tmp_path):
    store = MemoryStore(tmp_path / "sessions.sqlite3")
    store.append("case-1", {"role": "user", "content": "hello"})
    assert store.load("case-1") == [{"role": "user", "content": "hello"}]
    store.clear("case-1")
    assert store.load("case-1") == []
