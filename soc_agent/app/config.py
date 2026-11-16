from __future__ import annotations

import os
from pathlib import Path
from typing import Any

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


def normalize_ai_provider(provider: str | None = None) -> str:
    selected = (AI_PROVIDER if provider is None else provider).strip().lower()
    if selected in {"openai", "openai_compatible"}:
        return "openai"
    if selected in {"anthropic", "claude"}:
        return "anthropic"
    raise ValueError(f"Unsupported AI provider '{selected}'. Choose 'openai' or 'anthropic'.")


DEFAULT_PROVIDER = normalize_ai_provider()
DEFAULT_MODEL = ANTHROPIC_MODEL if DEFAULT_PROVIDER == "anthropic" else (MODEL_NAME or OPENAI_MODEL)


def list_ai_providers() -> list[dict[str, str]]:
    providers = []
    if OPENAI_API_KEY or OPENAI_BASE_URL:
        providers.append({"id": "openai", "name": "OpenAI", "model": MODEL_NAME or OPENAI_MODEL})
    if ANTHROPIC_API_KEY:
        providers.append({"id": "anthropic", "name": "Anthropic", "model": ANTHROPIC_MODEL})
    return providers


def create_ai_client(provider: str | None = None) -> tuple[str, str, Any]:
    selected = normalize_ai_provider(provider)
    if selected == "openai":
        if not (OPENAI_API_KEY or OPENAI_BASE_URL):
            raise RuntimeError("Configure OPENAI_API_KEY or OPENAI_BASE_URL in .env.")
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Install OpenAI support with pip install -r requirements.txt") from exc
        return selected, MODEL_NAME or OPENAI_MODEL, OpenAI(
            api_key=OPENAI_API_KEY or "dummy-key",
            base_url=OPENAI_BASE_URL or None,
        )

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Configure ANTHROPIC_API_KEY in .env.")
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install Anthropic support with pip install -r requirements.txt") from exc
    return selected, ANTHROPIC_MODEL, anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def verify_ai_connection(provider: str, client: Any) -> None:
    if provider == "openai":
        from openai import APIError
    elif provider == "anthropic":
        from anthropic import APIError
    else:
        raise ValueError(f"Unsupported AI provider '{provider}'.")

    try:
        client.models.list()
    except APIError as exc:
        raise RuntimeError(
            f"Could not connect to {provider}: {type(exc).__name__}. "
            "Check the configured API key, model access, and network."
        ) from exc
