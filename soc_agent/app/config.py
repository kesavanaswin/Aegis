from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

APP_API_TOKEN = os.environ.get("APP_API_TOKEN", "").strip()
APP_API_ROLE = os.environ.get("APP_API_ROLE", "soc_analyst").strip()
AI_PROVIDER = os.environ.get("AI_PROVIDER", "openai_compatible").strip().lower()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = (os.environ.get("OPENAI_BASE_URL", "") or "").rstrip("/")
OPENAI_MODEL = (os.environ.get("OPENAI_MODEL", "") or os.environ.get("HERMES_MODEL", "gpt-4o-mini")).strip()
MODEL_NAME = (os.environ.get("MODEL_NAME", "") or OPENAI_MODEL).strip()

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "soc_agent.sqlite3"))

ELASTIC_URL = os.environ.get("ELASTIC_URL", "").strip()
ELASTIC_API_KEY = os.environ.get("ELASTIC_API_KEY", "").strip()

CROWDSTRIKE_CLIENT_ID = os.environ.get("CROWDSTRIKE_CLIENT_ID", "").strip()
CROWDSTRIKE_CLIENT_SECRET = os.environ.get("CROWDSTRIKE_CLIENT_SECRET", "").strip()

VIRUSTOTAL_API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "").strip()
OKTA_DOMAIN = os.environ.get("OKTA_DOMAIN", "").strip()
OKTA_API_TOKEN = os.environ.get("OKTA_API_TOKEN", "").strip()

if not APP_API_TOKEN:
    raise RuntimeError("Set APP_API_TOKEN")

if AI_PROVIDER in {"anthropic", "claude"}:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Set ANTHROPIC_API_KEY")
    DEFAULT_MODEL = ANTHROPIC_MODEL
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install anthropic support with pip install -r requirements.txt") from exc
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
elif AI_PROVIDER in {"openai", "openai_compatible"}:
    if not (OPENAI_API_KEY or OPENAI_BASE_URL):
        raise RuntimeError("Set OPENAI_API_KEY or OPENAI_BASE_URL")
    DEFAULT_MODEL = MODEL_NAME or OPENAI_MODEL
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install openai support with pip install -r requirements.txt") from exc
    client = OpenAI(api_key=OPENAI_API_KEY or "dummy-key", base_url=OPENAI_BASE_URL or None)
else:
    raise RuntimeError(f"Unsupported AI_PROVIDER '{AI_PROVIDER}'. Use 'openai_compatible' or 'anthropic'.")
