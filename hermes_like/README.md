# Hermes-like starter scaffold

A small Python assistant scaffold with a command-line interface, OpenAI-compatible model client, SQLite conversation history, and an explicit allowlist of tools. It has no shell, browser, or system-changing tools.

## Install

From this directory:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
export OPENAI_API_KEY="your-key"
hermes-like
```

Set `OPENAI_BASE_URL` for an OpenAI-compatible API endpoint and `HERMES_LIKE_MODEL` to select a model. Conversation data is stored locally under `~/.hermes-like/sessions.sqlite3` by default; set `HERMES_LIKE_HOME` to change the directory. Prompts are sent to the configured model provider, so review data-handling requirements before using sensitive information.

Run offline tests with `pytest` from this directory.

## Scope and safety

This is a starter scaffold, not a clone of Hermes or a production-ready autonomous agent. The model may request only registered tools. Tool dispatch validates JSON and denies unknown tool names. The sample calculator parses a restricted arithmetic AST; it does not use Python `eval`. Add integrations as separately reviewed tools with least privilege and human approval for state-changing operations.
