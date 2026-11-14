from __future__ import annotations

import argparse
import os
import uuid

from agent.memory import SessionStore
from agent.provider import OpenAICompatibleProvider
from agent.runtime import Agent
from plugins.loader import load_plugin
from tools.builtin import register_builtins
from tools.toolsets import SAFE_TOOLSET
from tools.registry import ToolRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes-style tool-using assistant starter")
    parser.add_argument("--session", default=None, help="Resume a local session ID")
    parser.add_argument("--plugin", action="append", default=[], help="Trusted importable plugin module; can be repeated")
    args = parser.parse_args()

    registry = ToolRegistry()
    register_builtins(registry)
    enabled = set(SAFE_TOOLSET)
    for module_name in args.plugin:
        enabled.update(load_plugin(module_name, registry))

    session_id = args.session or str(uuid.uuid4())
    agent = Agent(registry, SessionStore(), enabled, OpenAICompatibleProvider())
    print(f"Session: {session_id}\nType /new for a new session, /quit to exit.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text in {"/quit", "/exit"}:
            break
        if text == "/new":
            session_id = str(uuid.uuid4())
            print(f"New session: {session_id}")
            continue
        if text:
            try:
                print("\nAssistant: " + agent.run_turn(session_id, text))
            except Exception as exc:
                print(f"Request failed: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
