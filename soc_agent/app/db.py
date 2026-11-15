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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                asset_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                owner TEXT NOT NULL,
                environment TEXT NOT NULL,
                criticality TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                vulnerability_id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                case_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                external_reference TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
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


def list_cases(limit: int = 50) -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE_PATH) as conn:
        rows = conn.execute(
            "SELECT case_id, created_at, updated_at, payload_json FROM cases ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "case_id": row[0],
            "created_at": row[1],
            "updated_at": row[2],
            "payload": json.loads(row[3]),
        }
        for row in rows
    ]


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


def save_approval(
    approval_id: str,
    case_id: str | None,
    action: str,
    target: str,
    reason: str,
    risk: str,
    status: str,
    approved_by: str | None = None,
) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            INSERT INTO approvals
                (approval_id, case_id, action, target, reason, risk, status, approved_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (approval_id, case_id or "", action, target, reason, risk, status, approved_by, utc_now()))


def list_approvals(status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query = """
        SELECT approval_id, case_id, action, target, reason, risk, status, approved_by, created_at
        FROM approvals
    """
    params: list[Any] = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DATABASE_PATH) as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "approval_id": row[0],
            "case_id": None if row[1] in {"", "unknown-case"} else row[1],
            "action": row[2],
            "target": row[3],
            "reason": row[4],
            "risk": row[5],
            "status": row[6],
            "approved_by": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


def get_approval(approval_id: str) -> dict[str, Any] | None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute(
            """
            SELECT approval_id, case_id, action, target, reason, risk, status, approved_by, created_at
            FROM approvals WHERE approval_id = ?
            """,
            (approval_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "approval_id": row[0],
        "case_id": None if row[1] in {"", "unknown-case"} else row[1],
        "action": row[2],
        "target": row[3],
        "reason": row[4],
        "risk": row[5],
        "status": row[6],
        "approved_by": row[7],
        "created_at": row[8],
    }


def update_approval_decision(approval_id: str, status: str, approved_by: str) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(
            """
            UPDATE approvals
            SET status = ?, approved_by = ?
            WHERE approval_id = ? AND status = 'pending'
            """,
            (status, approved_by, approval_id),
        )
    return cursor.rowcount == 1


def create_asset(asset: dict[str, Any]) -> None:
    now = utc_now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT INTO assets (asset_id, name, asset_type, owner, environment, criticality, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset["asset_id"],
                asset["name"],
                asset["asset_type"],
                asset["owner"],
                asset["environment"],
                asset["criticality"],
                now,
                now,
            ),
        )


def list_assets(limit: int = 200) -> list[dict[str, Any]]:
    with sqlite3.connect(DATABASE_PATH) as conn:
        rows = conn.execute(
            """
            SELECT asset_id, name, asset_type, owner, environment, criticality, created_at, updated_at
            FROM assets ORDER BY name COLLATE NOCASE LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "asset_id": row[0],
            "name": row[1],
            "asset_type": row[2],
            "owner": row[3],
            "environment": row[4],
            "criticality": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }
        for row in rows
    ]


def asset_exists(asset_id: str) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        row = conn.execute("SELECT 1 FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    return row is not None


def create_vulnerability(vulnerability: dict[str, Any]) -> None:
    now = utc_now()
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            INSERT INTO vulnerabilities (
                vulnerability_id, asset_id, case_id, title, description, severity, status,
                source, external_reference, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vulnerability["vulnerability_id"],
                vulnerability["asset_id"],
                vulnerability.get("case_id"),
                vulnerability["title"],
                vulnerability["description"],
                vulnerability["severity"],
                vulnerability["status"],
                vulnerability["source"],
                vulnerability.get("external_reference"),
                now,
                now,
            ),
        )


def list_vulnerabilities(status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    query = """
        SELECT v.vulnerability_id, v.asset_id, a.name, v.case_id, v.title, v.description,
               v.severity, v.status, v.source, v.external_reference, v.created_at, v.updated_at
        FROM vulnerabilities AS v
        JOIN assets AS a ON a.asset_id = v.asset_id
    """
    params: list[Any] = []
    if status:
        query += " WHERE v.status = ?"
        params.append(status)
    query += " ORDER BY v.updated_at DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(DATABASE_PATH) as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "vulnerability_id": row[0],
            "asset_id": row[1],
            "asset_name": row[2],
            "case_id": row[3],
            "title": row[4],
            "description": row[5],
            "severity": row[6],
            "status": row[7],
            "source": row[8],
            "external_reference": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }
        for row in rows
    ]


def update_vulnerability_status(vulnerability_id: str, status: str) -> bool:
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute(
            """
            UPDATE vulnerabilities SET status = ?, updated_at = ?
            WHERE vulnerability_id = ?
            """,
            (status, utc_now(), vulnerability_id),
        )
    return cursor.rowcount == 1


def get_workbench_counts() -> dict[str, int]:
    with sqlite3.connect(DATABASE_PATH) as conn:
        case_count = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        asset_count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
        open_vulnerabilities = conn.execute(
            "SELECT COUNT(*) FROM vulnerabilities WHERE status IN ('open', 'in_progress')"
        ).fetchone()[0]
        pending_approvals = conn.execute(
            "SELECT COUNT(*) FROM approvals WHERE status = 'pending'"
        ).fetchone()[0]
    return {
        "cases": case_count,
        "assets": asset_count,
        "open_vulnerabilities": open_vulnerabilities,
        "pending_approvals": pending_approvals,
    }


def log_event(case_id: str, event_type: str, detail: dict[str, Any]) -> None:
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute("""
            INSERT INTO audit_events (created_at, case_id, event_type, detail_json)
            VALUES (?, ?, ?, ?)
        """, (utc_now(), case_id, event_type, json.dumps(detail, ensure_ascii=False)))
