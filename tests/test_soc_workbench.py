import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["APP_API_TOKEN"] = "workbench-test-token"
os.environ["APP_API_ROLE"] = "soc_analyst"
os.environ.setdefault("OPENAI_API_KEY", "workbench-test-key")
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / f"aegis-workbench-import-{os.getpid()}.sqlite3")

from soc_agent.app import db
from soc_agent.app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATABASE_PATH", str(tmp_path / "soc.sqlite3"))
    db.ensure_db()
    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": "Bearer workbench-test-token"})
        yield test_client


def create_case(client):
    response = client.post(
        "/cases",
        json={
            "case_id": "CASE-200",
            "alert_type": "suspicious_login",
            "source": "test",
            "occurred_at": "2026-11-15T10:00:00+00:00",
            "severity": "high",
            "host": "workstation-01",
            "evidence": [{"id": "ev-1", "source": "test", "text": "Analyst-submitted evidence."}],
        },
    )
    assert response.status_code == 200
    return response.json()["case_id"]


def test_workbench_tracks_assets_findings_and_counts(client):
    case_id = create_case(client)

    asset = {
        "asset_id": "asset-01",
        "name": "workstation-01",
        "asset_type": "host",
        "owner": "IT",
        "environment": "production",
        "criticality": "high",
    }
    assert client.post("/assets", json=asset).status_code == 201
    assert client.post("/assets", json=asset).status_code == 409

    finding = {
        "vulnerability_id": "finding-01",
        "asset_id": "asset-01",
        "case_id": case_id,
        "title": "Outdated endpoint software",
        "description": "A manually recorded finding.",
        "severity": "medium",
        "source": "analyst",
    }
    assert client.post("/vulnerabilities", json={**finding, "asset_id": "missing"}).status_code == 404
    assert client.post("/vulnerabilities", json=finding).status_code == 201

    listed = client.get("/vulnerabilities").json()["vulnerabilities"]
    assert listed[0]["asset_name"] == "workstation-01"
    assert listed[0]["case_id"] == case_id
    assert client.get("/workbench/summary").json()["open_vulnerabilities"] == 1

    updated = client.patch("/vulnerabilities/finding-01", json={"status": "remediated"})
    assert updated.status_code == 200
    assert client.patch("/vulnerabilities/finding-01", json={"status": "executed"}).status_code == 422

    assert client.get("/workbench/summary").json() == {
        "cases": 1,
        "assets": 1,
        "open_vulnerabilities": 0,
        "pending_approvals": 0,
    }


def test_approval_is_role_gated_and_decision_is_one_time(client):
    case_id = create_case(client)
    high_risk = client.post(
        "/approvals",
        json={
            "case_id": case_id,
            "action": "host_isolate",
            "target": "workstation-01",
            "reason": "Review",
            "risk": "high",
            "required_role": "incident_manager",
        },
    )
    assert high_risk.status_code == 422
    denied = client.post(
        "/approvals",
        json={"case_id": case_id, "action": "host_isolate", "target": "workstation-01", "reason": "Review", "risk": "high"},
    )
    assert denied.status_code == 403

    request = client.post(
        "/approvals",
        json={"case_id": case_id, "action": "ticket_create", "target": "CASE-200", "reason": "Track analyst review", "risk": "low"},
    )
    assert request.status_code == 200
    approval_id = request.json()["approval_id"]
    assert client.get("/approvals?status=pending").json()["approvals"][0]["case_id"] == case_id

    decision_url = f"/approvals/{approval_id}/decision?decision=approved&approved_by=Analyst"
    assert client.post(decision_url).json()["status"] == "approved"
    assert client.post(decision_url).status_code == 409


def test_workbench_api_rejects_invalid_bearer_token(client):
    response = client.get("/assets", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401


def test_dashboard_is_available_without_exposing_case_data(client):
    create_case(client)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Aegis SOC Workbench" in response.text
    assert "CASE-200" not in response.text
