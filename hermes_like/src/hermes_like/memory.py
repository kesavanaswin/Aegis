from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    root = Path(os.environ.get("HERMES_LIKE_HOME", Path.home() / ".hermes-like"))
    root.mkdir(parents=True, exist_ok=True)
    return root / "sessions.sqlite3"


class MemoryStore:
    """Minimal SQLite conversation history, stored locally."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    message_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS messages_session_id_id
                ON messages(session_id, id)
            """)

    def load(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT message_json FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
        return [json.loads(row["message_json"]) for row in rows]

    def append(self, session_id: str, message: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, message_json) VALUES (?, ?)",
                (session_id, json.dumps(message, ensure_ascii=False)),
            )

    def clear(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
