# Argus SOC Agent

A defensive cybersecurity agent MVP for alert triage, investigation, structured findings, and human approval gates.

## Features
- Case intake for security alerts
- Read-only evidence gathering via placeholder tool adapters
- Structured investigation results in JSON
- Human approval logic for potentially damaging actions
- SQLite audit logging
- FastAPI service for analyst usage
- Docker and Compose support

## Stack
- Python
- FastAPI
- Anthropic API
- LangGraph
- SQLite
- Docker

## Setup

1. Copy `.env.example` to `.env` and fill in required values.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   uvicorn soc_agent.app.main:app --host 0.0.0.0 --port 8000
   ```

## Notes
This project is intentionally conservative: it does not perform direct destructive actions without policy checks and human approval.
