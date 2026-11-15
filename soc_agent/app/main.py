from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .adapters import CrowdStrikeAdapter, ElasticAdapter, OktaAdapter, VirusTotalAdapter
from .config import (
    APP_API_TOKEN,
    CROWDSTRIKE_CLIENT_ID,
    CROWDSTRIKE_CLIENT_SECRET,
    ELASTIC_API_KEY,
    ELASTIC_URL,
    OKTA_API_TOKEN,
    OKTA_DOMAIN,
    VIRUSTOTAL_API_KEY,
)
from .db import ensure_db, get_case, list_cases, log_event, save_approval, save_case, save_investigation
from .graph import build_graph
from .models import ActionRequest, AlertInput, InvestigationResult
from .orchestration import triage_with_llm
from .policy import validate_action

app = FastAPI(title="Argus SOC Agent", version="1.0.0")
bearer = HTTPBearer()

ensure_db()


def auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials.credentials != APP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    cases = list_cases(limit=10)
    rows = "".join(
        f"<tr><td>{case['case_id']}</td><td>{case['created_at']}</td><td>{case['payload'].get('alert_type', 'unknown')}</td></tr>"
        for case in cases
    )
    return f"""
    <html>
      <head><title>Argus SOC Dashboard</title></head>
      <body style="font-family: sans-serif; margin: 2rem; background: #0b1220; color: #e5e7eb;">
        <h1>Argus SOC Dashboard</h1>
        <p>OpenAI-compatible provider: enabled via environment configuration.</p>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%;">
          <thead>
            <tr><th>Case ID</th><th>Created</th><th>Alert Type</th></tr>
          </thead>
          <tbody>{rows or '<tr><td colspan="3">No cases yet</td></tr>'}</tbody>
        </table>
      </body>
    </html>
    """


@app.get("/cases", dependencies=[Depends(auth)])
def get_cases():
    return {"cases": list_cases(limit=50)}


@app.post("/cases", dependencies=[Depends(auth)])
def ingest_case(alert: AlertInput):
    alert.ensure_unique_ids()
    save_case(alert.case_id, alert.model_dump(mode="json"))
    log_event(alert.case_id, "case_received", {"alert_type": alert.alert_type, "source": alert.source})
    return {"case_id": alert.case_id, "status": "received"}


@app.get("/cases/{case_id}", dependencies=[Depends(auth)])
def get_case_detail(case_id: str):
    stored = get_case(case_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Case not found")
    return stored


@app.post("/cases/{case_id}/triage", response_model=InvestigationResult, dependencies=[Depends(auth)])
def triage_case(case_id: str):
    stored = get_case(case_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Case not found")

    alert = AlertInput.model_validate(stored)
    graph = build_graph()
    graph_result = graph.invoke({"alert": alert, "evidence": [], "findings": [], "recommendations": [], "verdict": "", "confidence": 0.0})
    result = triage_with_llm(alert, graph_result.get("evidence", []))
    save_investigation(case_id, result.model_dump(mode="json"))
    log_event(case_id, "triage_completed", {"verdict": result.verdict.value, "confidence": result.confidence})
    return result


@app.post("/approvals", dependencies=[Depends(auth)])
def request_approval(req: ActionRequest):
    if not validate_action(req.action, req.required_role, req.risk):
        raise HTTPException(status_code=403, detail="Action denied by policy")

    approval_id = f"apr-{uuid.uuid4().hex[:12]}"
    save_approval(approval_id, "unknown-case", req.action, req.target, req.reason, req.risk, "pending")
    return {"approval_id": approval_id, "status": "pending"}


@app.post("/approvals/{approval_id}/decision", dependencies=[Depends(auth)])
def approve_or_reject(approval_id: str, decision: str = Query(...), approved_by: str = Query("analyst")):
    valid = {"approved", "rejected", "expired"}
    if decision not in valid:
        raise HTTPException(status_code=400, detail="Decision must be approved, rejected, or expired")
    return {"approval_id": approval_id, "status": decision, "approved_by": approved_by}


@app.post("/tools/test", dependencies=[Depends(auth)])
def test_tools():
    results = []
    elastic = ElasticAdapter(ELASTIC_URL, ELASTIC_API_KEY)
    results.append(elastic.invoke(query="powershell suspicious").__dict__)

    cs = CrowdStrikeAdapter(CROWDSTRIKE_CLIENT_ID, CROWDSTRIKE_CLIENT_SECRET)
    results.append(cs.invoke(host="host-01").__dict__)

    vt = VirusTotalAdapter(VIRUSTOTAL_API_KEY)
    results.append(vt.invoke(value="198.51.100.4").__dict__)

    okta = OktaAdapter(OKTA_DOMAIN, OKTA_API_TOKEN)
    results.append(okta.invoke(user="alice").__dict__)

    return {"results": results}
