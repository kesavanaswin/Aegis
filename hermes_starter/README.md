# Hermes-style agent starter

This standalone Python project demonstrates a small model-driven agent runtime with explicit tool registration, named toolsets, opt-in Python plugins, and SQLite session history. It is not a clone of Hermes. The built-in tools are offline-only (calculator and UTC clock); it has no shell, browser, network-search, or system-changing tools.

## Layout

```text
hermes_starter/
├── agent/       # Provider adapter, agent loop, SQLite history, CLI
├── tools/       # Tool registry, built-ins, toolsets
├── plugins/     # Explicitly loaded plugin examples
├── tests/       # Offline unit tests using a fake provider
├── requirements.txt
└── README.md
```

## Setup and run

```bash
cd hermes_starter
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
python -m agent.cli
```

The provider uses the OpenAI Chat Completions API. Set `OPENAI_BASE_URL` for an OpenAI-compatible endpoint and `HERMES_MODEL` to select the model (default: `gpt-4o-mini`). To load the bundled plugin explicitly, run `python -m agent.cli --plugin plugins.example_plugin`; plugin Python executes with the current user's privileges, so only load code you trust.

Conversation records are stored in `~/.hermes-starter/sessions.sqlite3` by default. Set `HERMES_STARTER_HOME` to use a different local data directory. Prompts go to the configured model provider; do not send confidential incident data unless your data-handling rules permit it.

## Build a Windows executable

Build on Windows with Python 3.11 or newer. From this directory, install the dependencies and create a single-file console executable:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm pyinstaller.spec
```

The executable is written to `dist/aegis-hermes-starter.exe`. Set `OPENAI_API_KEY` in the environment before launching it. The executable stores session history in the same per-user location as the Python CLI; it does not bundle credentials or conversation data.

## Offline tests

```bash
pip install pytest
python -m pytest -q
```

The tests use a fake provider and do not need an API key or make model/network calls.

## Extension contract

Tools register with `ToolRegistry.register(...)` and belong to a toolset. The agent receives only the explicitly selected tool names. Plugins are not auto-discovered: pass `--plugin module.path` to load a trusted module exposing `register(registry)`. A plugin can execute arbitrary Python and is not sandboxed. Keep the system prompt stable and treat tool results as untrusted data. Add human approval and deterministic policy checks before introducing state-changing tools.

## Limitations

This is a minimal educational starter, not a production-ready agent framework. It has no provider retries, streaming, sandboxing, credential vault, multi-user access controls, or production audit guarantees. The SQLite database is local storage, not tamper-proof audit storage.
