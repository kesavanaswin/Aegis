#!/usr/bin/env bash
set -euo pipefail

python -m uvicorn soc_agent.app.main:app --host 0.0.0.0 --port 8000
