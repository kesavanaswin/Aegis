from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APP_API_TOKEN = os.environ.get("APP_API_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "soc_agent.sqlite3"))

ELASTIC_URL = os.environ.get("ELASTIC_URL", "")
ELASTIC_API_KEY = os.environ.get("ELASTIC_API_KEY", "")

CROWDSTRIKE_CLIENT_ID = os.environ.get("CROWDSTRIKE_CLIENT_ID", "")
CROWDSTRIKE_CLIENT_SECRET = os.environ.get("CROWDSTRIKE_CLIENT_SECRET", "")

VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
OKTA_DOMAIN = os.environ.get("OKTA_DOMAIN", "")
OKTA_API_TOKEN = os.environ.get("OKTA_API_TOKEN", "")

if not APP_API_TOKEN:
    raise RuntimeError("Set APP_API_TOKEN")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Set ANTHROPIC_API_KEY")
