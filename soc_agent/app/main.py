from __future__ import annotations

import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .adapters import ElasticAdapter, CrowdStrikeAdapter, VirusTotalAdapter, OktaAdapter
from .config import APP_API_TOKEN, ELASTIC_URL, ELASTIC_API_KEY, CROWDSTRIKE_CLIENT_ID, CROWDSTRIKE_CLIENT_SECRET, VIRUSTOTAL_API_KEY, OKTA_DOMAIN, OKTA_API_TOKEN
from .db import ensure_db, save_case, get_case, save_investigation, save_approval, log_event
from .models import AlertInput, ActionRequest, InvestigationResult
from .orchestration import triage_with_llm
from .policy import validate_action
from .graph import build_graph

app = FastAPI(title="Argus SOC Agent", version="1.0.0")
bearer = HTTPBearer()

ensure_db()


def auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials.credentials != APP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/cases", dependencies=[Depends(auth)])
def ingest_case(alert: AlertInput):
    alert.ensure_unique_ids()
    save_case(alert.case_id, alert.model_dump(mode="json"))
    log_event(alert.case_id, "case_received", {"alert_type": alert.alert_type, "source": alert.source})
    return {"case_id": alert.case_id, "status": "received"}


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
