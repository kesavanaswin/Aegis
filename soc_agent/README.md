# Aegis SOC workbench

The SOC prototype provides a small, defense-first workbench for reviewing alert cases, recording owned assets and vulnerability findings, and tracking analyst approval decisions. It is an educational prototype, not a production security platform.

## Run locally

From the repository root, install the root dependencies and configure `.env`:

```powershell
python -m pip install -r requirements.txt
```

Set `APP_API_TOKEN` to a private token and configure at least one AI provider key in `.env`:

```dotenv
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
AI_PROVIDER=openai
```

Only providers with configured credentials appear in the dashboard menu. After connecting with the app token, choose a provider to check the connection, then run triage from a case row; the choice lasts for the current dashboard session. `AI_PROVIDER` sets the default selection, and `OPENAI_BASE_URL` can point to an OpenAI-compatible endpoint. Keep keys on the server—never embed or commit them. The default `APP_API_ROLE=soc_analyst` can request low-risk ticket creation. The server-side role `incident_manager` is required for high-risk approval requests.

Start the API and open the dashboard:

```powershell
python -m uvicorn soc_agent.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/dashboard` and enter the API token. The dashboard keeps the token in memory for the current page; it is not persisted in browser storage.

## Workbench API

All data endpoints require `Authorization: Bearer <APP_API_TOKEN>`.

- `GET /workbench/summary` returns case, asset, open-finding, and pending-approval counts.
- `GET /cases` and `POST /cases` list and ingest alert cases.
- `GET /assets` and `POST /assets` list and register assets.
- `GET /vulnerabilities`, `POST /vulnerabilities`, and `PATCH /vulnerabilities/{id}` record findings and update their lifecycle status.
- `GET /approvals`, `POST /approvals`, and `POST /approvals/{id}/decision` track requested decisions.

Vulnerability findings must reference a registered asset; case links are validated when supplied. Approval decisions are recorded in the audit log and **do not execute the requested action**.

## Security and limitations

- The bearer token is a shared service credential, not multi-user authentication. `APP_API_ROLE` is configured by the server and applies to every caller; it is not a per-user role system. `approved_by` is an audit label supplied by the caller, not an authenticated identity.
- Keep the API on a trusted network, protect the token, and do not expose the dashboard publicly.
- Example enrichment adapters return simulated data. They are not real SIEM, EDR, threat-intelligence, or identity integrations.
- This workbench does not scan targets, exploit vulnerabilities, or execute response actions. Connectors and any future state-changing workflow need independent security review and explicit organizational authorization.
- Do not use prototype results as production incident-response evidence.

Run the focused SOC tests from the repository root:

```powershell
python -m pytest -q tests/test_soc_agent.py tests/test_soc_workbench.py
```
