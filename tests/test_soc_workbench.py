import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["APP_API_TOKEN"] = "workbench-test-token"
os.environ["APP_API_ROLE"] = "soc_analyst"
os.environ.setdefault("OPENAI_API_KEY", "workbench-test-key")
os.environ["DATABASE_PATH"] = str(Path(tempfile.gettempdir()) / f"aegis-workbench-import-{os.getpid()}.sqlite3")

from soc_agent.app import config, db
import soc_agent.app.main as main_module
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
    assert "ai-provider" in response.text
    assert "Run triage" in response.text


def test_ai_provider_options_only_include_configured_providers(client, monkeypatch):
    monkeypatch.setattr(config, "OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(config, "OPENAI_BASE_URL", "")
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "")

    response = client.get("/ai/providers")

    assert response.status_code == 200
    assert [provider["id"] for provider in response.json()["providers"]] == ["openai"]
    assert "test-openai-key" not in response.text


def test_ai_connect_uses_selected_provider(client, monkeypatch):
    verified = []
    monkeypatch.setattr(
        main_module,
        "create_ai_client",
        lambda provider: (provider, "test-model", object()),
    )
    monkeypatch.setattr(
        main_module,
        "verify_ai_connection",
        lambda provider, client: verified.append(provider),
    )

    response = client.post("/ai/connect", json={"provider": "anthropic"})

    assert response.status_code == 200
    assert verified == ["anthropic"]
    assert response.json() == {
        "provider": "anthropic",
        "model": "test-model",
        "status": "ready",
    }


def test_case_triage_uses_selected_provider(client, monkeypatch):
    case_id = create_case(client)
    selected = []
    monkeypatch.setattr(
        main_module,
        "build_graph",
        lambda: type("Graph", (), {"invoke": lambda self, state: {"evidence": []}})(),
    )

    def fail_triage(alert, evidence, provider=None):
        selected.append(provider)
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(main_module, "triage_with_llm", fail_triage)

    response = client.post(f"/cases/{case_id}/triage?provider=anthropic")

    assert response.status_code == 503
    assert selected == ["anthropic"]
