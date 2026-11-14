from __future__ import annotations

import importlib
from tools.registry import ToolRegistry


def load_plugin(module_name: str, registry: ToolRegistry) -> set[str]:
    """Import a trusted module exposing register(registry); return its tools.

    Importing Python plugins runs arbitrary code with this process's privileges.
    No plugin sandbox is provided by this starter.
    """
    before = set(registry._tools)
    module = importlib.import_module(module_name)
    register = getattr(module, "register", None)
    if not callable(register):
        raise ValueError(f"Plugin {module_name!r} must export register(registry).")
    register(registry)
    return set(registry._tools) - before
