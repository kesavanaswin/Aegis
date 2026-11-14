from __future__ import annotations

import argparse
import os
import sys
import uuid

from .agent import Agent
from .memory import MemoryStore
from .tools import build_registry


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes-like assistant starter")
    parser.add_argument("--session", default=None, help="Conversation session ID")
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY before starting.", file=sys.stderr)
        raise SystemExit(2)

    session_id = args.session or str(uuid.uuid4())
    agent = Agent(registry=build_registry(), memory=MemoryStore())
    print(f"Session: {session_id}")
    print("Type /quit to exit or /new to start a fresh session.")

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
        if not text:
            continue
        try:
            print(f"\nAssistant: {agent.run_turn(session_id, text)}")
        except Exception as exc:
            print(f"\nRequest failed: {type(exc).__name__}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
