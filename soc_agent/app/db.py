import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATABASE_PATH


def ensure_db():
    path = Path(DATABASE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS investigations (
                case_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                reason TEXT NOT NULL,
                risk TEXT NOT NULL,
                status TEXT NOT NULL,
                approved_by TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                case_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                detail_json TEXT NOT NULL
            )
        """)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_case(case_id: str, payload: dict[str, Any]) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        now = utc_now()
        conn.execute("""
            INSERT INTO cases (case_id, created_at, updated_at, payload_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                payload_json = excluded.payload_json
        """, (case_id, now, now, json.dumps(payload, ensure_ascii=False)))


def get_case(case_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute("SELECT payload_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
    if row:
        return json.loads(row[0])
    return None


def save_investigation(case_id: str, result: dict[str, Any]) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        now = utc_now()
        conn.execute("""
            INSERT INTO investigations (case_id, created_at, updated_at, result_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(case_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                result_json = excluded.result_json
        """, (case_id, now, now, json.dumps(result, ensure_ascii=False)))


def save_approval(approval_id: str, case_id: str, action: str, target: str, reason: str, risk: str, status: str, approved_by: str | None = None) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            INSERT INTO approvals
                (approval_id, case_id, action, target, reason, risk, status, approved_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (approval_id, case_id, action, target, reason, risk, status, approved_by, utc_now()))


def log_event(case_id: str, event_type: str, detail: dict[str, Any]) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            INSERT INTO audit_events (created_at, case_id, event_type, detail_json)
            VALUES (?, ?, ?, ?)
        """, (utc_now(), case_id, event_type, json.dumps(detail, ensure_ascii=False)))
