from __future__ import annotations

import sqlite3
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .adapters import CrowdStrikeAdapter, ElasticAdapter, OktaAdapter, VirusTotalAdapter
from .config import (
    APP_API_TOKEN,
    APP_API_ROLE,
    CROWDSTRIKE_CLIENT_ID,
    CROWDSTRIKE_CLIENT_SECRET,
    ELASTIC_API_KEY,
    ELASTIC_URL,
    OKTA_API_TOKEN,
    OKTA_DOMAIN,
    VIRUSTOTAL_API_KEY,
)
from .db import (
    asset_exists,
    create_asset,
    create_vulnerability,
    ensure_db,
    get_approval,
    get_case,
    get_workbench_counts,
    list_approvals,
    list_assets,
    list_cases,
    list_vulnerabilities,
    log_event,
    save_approval,
    save_case,
    save_investigation,
    update_approval_decision,
    update_vulnerability_status,
)
from .graph import build_graph
from .models import (
    ActionRequest,
    AlertInput,
    AssetInput,
    InvestigationResult,
    VulnerabilityInput,
    VulnerabilityStatus,
    VulnerabilityStatusUpdate,
)
from .orchestration import triage_with_llm
from .policy import validate_action

app = FastAPI(title="Aegis SOC Workbench", version="1.0.0")
bearer = HTTPBearer(auto_error=True)

ensure_db()


def auth(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if credentials.credentials != APP_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return f"""
    <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Aegis SOC Workbench</title>
        <style>
          :root {{ color-scheme: dark; font-family: Segoe UI, sans-serif; background: #0b1220; color: #e5e7eb; }}
          body {{ max-width: 1440px; margin: 0 auto; padding: 2rem; }}
          h1, h2 {{ margin-top: 0; }} h1 {{ color: #93c5fd; }}
          section, .panel {{ background: #111c2f; border: 1px solid #26364f; border-radius: 12px; padding: 1rem; }}
          .connect, .metrics, .grid, .forms {{ display: grid; gap: 1rem; }}
          .connect {{ grid-template-columns: minmax(220px, 2fr) minmax(180px, 1fr) auto; align-items: end; }}
          .metrics {{ grid-template-columns: repeat(4, minmax(130px, 1fr)); margin: 1rem 0; }}
          .grid, .forms {{ grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 1rem 0; }}
          .metric strong {{ display: block; font-size: 1.8rem; color: #93c5fd; }}
          label {{ display: grid; gap: .35rem; font-size: .9rem; }}
          input, select, textarea, button {{ box-sizing: border-box; border-radius: 6px; border: 1px solid #40516a; padding: .6rem; background: #0b1220; color: inherit; }}
          form.stack {{ display: grid; gap: .65rem; }}
          button {{ background: #1d4ed8; border: 0; cursor: pointer; }} button.secondary {{ background: #334155; }}
          table {{ width: 100%; border-collapse: collapse; font-size: .9rem; }}
          th, td {{ text-align: left; padding: .55rem; border-bottom: 1px solid #26364f; vertical-align: top; }}
          .scroll {{ overflow-x: auto; }} .muted {{ color: #9ca3af; }} #message {{ min-height: 1.3rem; }}
          @media (max-width: 760px) {{ body {{ padding: 1rem; }} .connect, .metrics, .grid, .forms {{ grid-template-columns: 1fr; }} }}
        </style>
      </head>
      <body>
        <h1>Aegis SOC Workbench</h1>
        <p class="muted">Track cases, owned assets, vulnerability findings, and analyst decisions. This workbench does not execute response actions.</p>
        <form id="connect" class="panel connect">
          <label>API token<input id="token" type="password" autocomplete="off" required></label>
          <label>Analyst name (audit label)<input id="analyst" maxlength="120" value="analyst"></label>
          <button type="submit">Connect</button>
        </form>
        <p id="message" role="status" aria-live="polite"></p>
        <div id="workbench" hidden>
          <div class="metrics">
            <section class="metric">Cases<strong id="case-count">0</strong></section>
            <section class="metric">Assets<strong id="asset-count">0</strong></section>
            <section class="metric">Open findings<strong id="finding-count">0</strong></section>
            <section class="metric">Pending approvals<strong id="approval-count">0</strong></section>
          </div>
          <div class="grid">
            <section><h2>Cases</h2><div class="scroll"><table><thead><tr><th>Case</th><th>Alert</th><th>Severity</th><th>Host / User</th></tr></thead><tbody id="cases"></tbody></table></div></section>
            <section><h2>Assets</h2><div class="scroll"><table><thead><tr><th>Asset</th><th>Type</th><th>Owner</th><th>Criticality</th></tr></thead><tbody id="assets"></tbody></table></div></section>
            <section><h2>Vulnerability findings</h2><div class="scroll"><table><thead><tr><th>Finding</th><th>Asset</th><th>Severity</th><th>Status</th><th>Case</th></tr></thead><tbody id="vulnerabilities"></tbody></table></div></section>
            <section><h2>Approval inbox</h2><div class="scroll"><table><thead><tr><th>Action</th><th>Target</th><th>Risk</th><th>Case</th><th>Reason</th><th>Decision</th></tr></thead><tbody id="approvals"></tbody></table></div></section>
          </div>
          <div class="forms">
            <section><h2>Register an asset</h2>
              <form id="asset-form" class="stack">
                <label>Asset ID<input name="asset_id" maxlength="120" required></label>
                <label>Name<input name="name" maxlength="240" required></label>
                <label>Type<select name="asset_type"><option>host</option><option>ip</option><option>domain</option><option>service</option><option>cloud_resource</option></select></label>
                <label>Owner<input name="owner" maxlength="200"></label>
                <label>Environment<input name="environment" maxlength="100" value="unknown"></label>
                <label>Criticality<select name="criticality"><option>informational</option><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></label>
                <button type="submit">Add asset</button>
              </form>
            </section>
            <section><h2>Record a vulnerability finding</h2>
              <form id="vulnerability-form" class="stack">
                <label>Finding ID<input name="vulnerability_id" maxlength="120" required></label>
                <label>Asset ID<input name="asset_id" maxlength="120" required></label>
                <label>Related case ID (optional)<input name="case_id" maxlength="200"></label>
                <label>Title<input name="title" maxlength="300" required></label>
                <label>Description<textarea name="description" maxlength="4000"></textarea></label>
                <label>Severity<select name="severity"><option>informational</option><option>low</option><option>medium</option><option>high</option><option>critical</option></select></label>
                <label>Source<input name="source" maxlength="120" value="analyst" required></label>
                <button type="submit">Record finding</button>
              </form>
            </section>
            <section><h2>Request analyst approval</h2>
              <form id="approval-form" class="stack">
                <label>Related case ID (optional)<input name="case_id" maxlength="200"></label>
                <label>Action<select name="action"><option>ticket_create</option><option>host_isolate</option><option>account_disable</option><option>ip_block</option><option>domain_block</option><option>log_delete</option></select></label>
                <label>Target<input name="target" maxlength="300" required></label>
                <label>Risk<select name="risk"><option>low</option><option selected>medium</option><option>high</option></select></label>
                <label>Reason<textarea name="reason" maxlength="2000" required></textarea></label>
                <button type="submit">Submit for review</button>
              </form>
            </section>
          </div>
        </div>
        <script>
          let apiToken = "";
          const byId = (id) => document.getElementById(id);
          const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[char]));
          function message(text, isError = false) {{ byId("message").textContent = text; byId("message").style.color = isError ? "#fca5a5" : "#86efac"; }}
          async function api(path, options = {{}}) {{
            const headers = {{ Authorization: `Bearer ${{apiToken}}`, ...(options.headers || {{}}) }};
            if (options.body) headers["Content-Type"] = "application/json";
            const response = await fetch(path, {{ ...options, headers }});
            const body = await response.json().catch(() => ({{}}));
            if (!response.ok) throw new Error(body.detail || `Request failed (${{response.status}})`);
            return body;
          }}
          const cell = (value) => `<td>${{escapeHtml(value)}}</td>`;
          async function refresh() {{
            const [summary, cases, assets, findings, approvals] = await Promise.all([
              api("/workbench/summary"), api("/cases"), api("/assets"),
              api("/vulnerabilities"), api("/approvals?status=pending")
            ]);
            byId("case-count").textContent = summary.cases;
            byId("asset-count").textContent = summary.assets;
            byId("finding-count").textContent = summary.open_vulnerabilities;
            byId("approval-count").textContent = summary.pending_approvals;
            byId("cases").innerHTML = cases.cases.map((item) => `<tr>${{cell(item.case_id)}}${{cell(item.payload.alert_type)}}${{cell(item.payload.severity)}}${{cell([item.payload.host, item.payload.user].filter(Boolean).join(" / "))}}</tr>`).join("") || "<tr><td colspan='4'>No cases</td></tr>";
            byId("assets").innerHTML = assets.assets.map((item) => `<tr>${{cell(item.name)}}${{cell(item.asset_type)}}${{cell(item.owner)}}${{cell(item.criticality)}}</tr>`).join("") || "<tr><td colspan='4'>No assets</td></tr>";
            byId("vulnerabilities").innerHTML = findings.vulnerabilities.map((item) => {{
              const statuses = ["open", "in_progress", "accepted", "remediated", "false_positive"];
              const options = statuses.map((value) => `<option value="${{value}}" ${{value === item.status ? "selected" : ""}}>${{value.replace("_", " ")}}</option>`).join("");
              return `<tr>${{cell(item.title)}}${{cell(item.asset_name)}}${{cell(item.severity)}}<td><select aria-label="Finding status">${{options}}</select> <button class="secondary" data-vulnerability="${{escapeHtml(item.vulnerability_id)}}">Save</button></td>${{cell(item.case_id || "-")}}</tr>`;
            }}).join("") || "<tr><td colspan='5'>No findings</td></tr>";
            byId("approvals").innerHTML = approvals.approvals.map((item) => `<tr>${{cell(item.action)}}${{cell(item.target)}}${{cell(item.risk)}}${{cell(item.case_id || "-")}}${{cell(item.reason)}}<td><button data-approval="${{escapeHtml(item.approval_id)}}" data-decision="approved">Approve</button> <button class="secondary" data-approval="${{escapeHtml(item.approval_id)}}" data-decision="rejected">Reject</button></td></tr>`).join("") || "<tr><td colspan='6'>No pending approvals</td></tr>";
          }}
          byId("connect").addEventListener("submit", async (event) => {{
            event.preventDefault(); apiToken = byId("token").value;
            try {{ await refresh(); byId("workbench").hidden = false; byId("token").value = ""; message("Connected."); }}
            catch (error) {{ apiToken = ""; message(error.message, true); }}
          }});
          byId("asset-form").addEventListener("submit", async (event) => {{
            event.preventDefault();
            const asset = Object.fromEntries(new FormData(event.currentTarget).entries());
            try {{ await api("/assets", {{ method: "POST", body: JSON.stringify(asset) }}); event.currentTarget.reset(); await refresh(); message("Asset registered."); }}
            catch (error) {{ message(error.message, true); }}
          }});
          byId("vulnerability-form").addEventListener("submit", async (event) => {{
            event.preventDefault();
            const finding = Object.fromEntries(new FormData(event.currentTarget).entries());
            finding.case_id = finding.case_id || null;
            try {{ await api("/vulnerabilities", {{ method: "POST", body: JSON.stringify(finding) }}); event.currentTarget.reset(); await refresh(); message("Finding recorded."); }}
            catch (error) {{ message(error.message, true); }}
          }});
          byId("approval-form").addEventListener("submit", async (event) => {{
            event.preventDefault();
            const approval = Object.fromEntries(new FormData(event.currentTarget).entries());
            approval.case_id = approval.case_id || null;
            try {{ await api("/approvals", {{ method: "POST", body: JSON.stringify(approval) }}); event.currentTarget.reset(); await refresh(); message("Approval request submitted; no action was executed."); }}
            catch (error) {{ message(error.message, true); }}
          }});
          byId("approvals").addEventListener("click", async (event) => {{
            const button = event.target.closest("button[data-approval]");
            if (!button) return;
            const params = new URLSearchParams({{ decision: button.dataset.decision, approved_by: byId("analyst").value || "analyst" }});
            try {{ await api(`/approvals/${{encodeURIComponent(button.dataset.approval)}}/decision?${{params}}`, {{ method: "POST" }}); await refresh(); message("Decision recorded."); }}
            catch (error) {{ message(error.message, true); }}
          }});
          byId("vulnerabilities").addEventListener("click", async (event) => {{
            const button = event.target.closest("button[data-vulnerability]");
            if (!button) return;
            const status = button.closest("tr").querySelector("select").value;
            try {{
              await api(`/vulnerabilities/${{encodeURIComponent(button.dataset.vulnerability)}}`, {{ method: "PATCH", body: JSON.stringify({{ status }}) }});
              await refresh(); message("Finding status updated.");
            }} catch (error) {{ message(error.message, true); }}
          }});
        </script>
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


@app.get("/workbench/summary", dependencies=[Depends(auth)])
def workbench_summary():
    return get_workbench_counts()


@app.get("/assets", dependencies=[Depends(auth)])
def get_assets():
    return {"assets": list_assets()}


@app.post("/assets", status_code=201, dependencies=[Depends(auth)])
def register_asset(asset: AssetInput):
    try:
        create_asset(asset.model_dump(mode="json"))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Asset ID already exists") from exc
    log_event("", "asset_registered", {"asset_id": asset.asset_id, "asset_type": asset.asset_type})
    return {"asset": asset.model_dump(mode="json"), "status": "created"}


@app.get("/vulnerabilities", dependencies=[Depends(auth)])
def get_vulnerabilities(status: VulnerabilityStatus | None = Query(default=None)):
    return {"vulnerabilities": list_vulnerabilities(status=status)}


@app.post("/vulnerabilities", status_code=201, dependencies=[Depends(auth)])
def record_vulnerability(vulnerability: VulnerabilityInput):
    if not asset_exists(vulnerability.asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    if vulnerability.case_id and not get_case(vulnerability.case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    try:
        create_vulnerability(vulnerability.model_dump(mode="json"))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Finding ID already exists") from exc
    log_event(
        vulnerability.case_id or "",
        "vulnerability_recorded",
        {
            "vulnerability_id": vulnerability.vulnerability_id,
            "asset_id": vulnerability.asset_id,
            "severity": vulnerability.severity.value,
        },
    )
    return {"vulnerability": vulnerability.model_dump(mode="json"), "status": "created"}


@app.patch("/vulnerabilities/{vulnerability_id}", dependencies=[Depends(auth)])
def update_vulnerability(vulnerability_id: str, update: VulnerabilityStatusUpdate):
    if not update_vulnerability_status(vulnerability_id, update.status):
        raise HTTPException(status_code=404, detail="Finding not found")
    log_event("", "vulnerability_status_changed", {
        "vulnerability_id": vulnerability_id,
        "status": update.status,
    })
    return {"vulnerability_id": vulnerability_id, "status": update.status}


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
    if req.case_id and not get_case(req.case_id):
        raise HTTPException(status_code=404, detail="Case not found")
    if not validate_action(req.action, APP_API_ROLE, req.risk):
        raise HTTPException(status_code=403, detail="Action denied by policy")

    approval_id = f"apr-{uuid.uuid4().hex[:12]}"
    save_approval(approval_id, req.case_id, req.action, req.target, req.reason, req.risk, "pending")
    log_event(req.case_id or "", "approval_requested", {"approval_id": approval_id, "action": req.action})
    return {"approval_id": approval_id, "case_id": req.case_id, "status": "pending"}


@app.get("/approvals", dependencies=[Depends(auth)])
def get_approvals(
    status: str | None = Query(default=None, pattern="^(pending|approved|rejected|expired)$"),
):
    return {"approvals": list_approvals(status=status)}


@app.post("/approvals/{approval_id}/decision", dependencies=[Depends(auth)])
def approve_or_reject(
    approval_id: str,
    decision: str = Query(...),
    approved_by: str = Query("analyst", min_length=1, max_length=120),
):
    valid = {"approved", "rejected", "expired"}
    if decision not in valid:
        raise HTTPException(status_code=400, detail="Decision must be approved, rejected, or expired")
    if not approved_by.strip():
        raise HTTPException(status_code=422, detail="Approver name is required")
    approval = get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if not update_approval_decision(approval_id, decision, approved_by.strip()):
        raise HTTPException(status_code=409, detail="Approval has already been decided")
    log_event(
        approval["case_id"] or "",
        "approval_decided",
        {"approval_id": approval_id, "status": decision, "approved_by": approved_by.strip()},
    )
    return {"approval_id": approval_id, "status": decision, "approved_by": approved_by.strip()}


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
