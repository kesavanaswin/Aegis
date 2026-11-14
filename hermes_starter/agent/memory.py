from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def default_db_path() -> Path:
    home = Path(os.environ.get("HERMES_STARTER_HOME", Path.home() / ".hermes-starter"))
    home.mkdir(parents=True, exist_ok=True)
    return home / "sessions.sqlite3"


class SessionStore:
    """Local SQLite conversation history, isolated by session identifier."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, session_id TEXT NOT NULL, payload TEXT NOT NULL)")
            conn.execute("CREATE INDEX IF NOT EXISTS messages_session_order ON messages(session_id, id)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def load(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT payload FROM messages WHERE session_id = ? ORDER BY id", (session_id,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def append(self, session_id: str, message: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute("INSERT INTO messages(session_id, payload) VALUES (?, ?)",
                         (session_id, json.dumps(message, ensure_ascii=False)))

    def clear(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
