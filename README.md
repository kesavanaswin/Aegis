<div align="center">

# Aegis

### A practical home for defensive security agents and Hermes-style agent experiments

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Security-first](https://img.shields.io/badge/Default-read--only%20%26%20human--review-blue)](#security-first-by-design)

**Aegis is an experimental agent workspace.** It brings together an offline-first SOC triage prototype and a small Hermes-inspired, tool-using assistant scaffold. It is an independent project—not an official Nous Research product or a replacement for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

</div>

---

## What’s here

| Project | Purpose | Start here |
| --- | --- | --- |
| [`hermes_starter/`](hermes_starter/) | Small model-driven assistant with a tool registry, allowlisted toolsets, opt-in Python plugins, SQLite session history, CLI, and offline tests. | [Starter guide](hermes_starter/README.md) |
| [`hermes_like/`](hermes_like/) | Minimal assistant scaffold with a command-line interface, OpenAI-compatible provider, local conversation history, and a tiny safe tool set. | [Scaffold guide](hermes_like/README.md) |
| [`soc_agent/`](soc_agent/) | Defensive SOC alert-triage and policy-gate prototype. Its example adapters are placeholders; it is not connected to production security systems. | [SOC agent guide](soc_agent/README.md) |

These are prototypes with different goals, not one integrated production application. Choose one subproject and follow its own setup instructions.

## Hermes-style starter

The recommended starting point for experimenting with tool-driven agents is `hermes_starter/`:

- **Agent runtime** — handles a conversation and bounded tool-call loop.
- **Tool registry and toolsets** — explicitly register tools, then expose only selected tools to the model.
- **Opt-in plugins** — load a trusted module explicitly; plugins are ordinary Python code and are not sandboxed.
- **Local session history** — stores conversations in SQLite.
- **Offline tests** — exercise registry, toolsets, memory, and runtime using a fake provider.
- **Conservative built-ins** — calculator and UTC time; no shell, browser, or system-changing tools.

### Quick start

```bash
cd hermes_starter
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
export OPENAI_API_KEY="your-key"
python -m agent.cli
```

To select an OpenAI-compatible endpoint, set `OPENAI_BASE_URL`. Set `HERMES_MODEL` to choose a model; the default is `gpt-4o-mini`.

To explicitly load the bundled example plugin:

```bash
python -m agent.cli --plugin plugins.example_plugin
```

**Only load plugins you trust.** Importing a plugin executes Python with the privileges of the current user.

Run the offline starter tests from `hermes_starter/`:

```bash
pip install pytest
python -m pytest -q
```

The tests use a fake provider; they do not need a model API key or make model calls.

## SOC triage prototype

The SOC prototype explores a defensive workflow: supplied alert data, evidence summaries, read-only-style enrichment placeholders, and human review for response recommendations. It is a learning and design reference—not a production SOC tool.

- The bundled tool adapters may return simulated/example data and are **not real SIEM, EDR, threat-intelligence, identity, or firewall integrations**.
- Do not provide production credentials or connect it to live response systems without independent security review and implementation work.
- Keep containment and other state-changing actions behind your organization’s approval process.
- Treat logs, emails, tickets, and threat-intelligence text as untrusted input.
- Synthetic tests and mock model runs do not establish real-model safety or operational readiness.

See [`soc_agent/README.md`](soc_agent/README.md) for what is implemented and its limitations.

## Security-first by design

Aegis prototypes are intended to explore safe agent patterns, not grant models authority. For any future integration:

1. Start with read-only credentials and narrow data scope.
2. Keep policy decisions deterministic and separate from model output.
3. Derive target scope from trusted case metadata—not model-generated arguments.
4. Require human approval for containment or other consequential changes.
5. Log tool proposals, guard decisions, results, approvals, and analyst overrides.
6. Evaluate attempted actions separately from actions permitted by the guard.
7. Do not treat prompt-injection detection heuristics as the security boundary.

## Repository layout

```text
.
├── hermes_starter/   # Tool-driven agent starter and offline tests
├── hermes_like/      # Minimal assistant scaffold
├── soc_agent/        # Defensive SOC triage prototype
└── tests/            # Tests for the root SOC prototype
```

## Development

Each subproject has its own dependencies and instructions. Run tests from the relevant project directory. This repository’s code and tests have not all been validated together as one integrated application; check the current test results before relying on any component.

## Upstream inspiration

This project is independently maintained and is not affiliated with Nous Research. For the full Hermes Agent framework, documentation, and current installation instructions, visit [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

## License

This repository includes an MIT license. See [`LICENSE`](LICENSE) for terms. Hermes Agent remains a separate upstream project with its own license and maintainers.
