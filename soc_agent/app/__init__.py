from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentRole:
    name: str
    purpose: str


TRACE_TRIAGE = AgentRole(
    name="triage_agent",
    purpose="Review alert severity, collect evidence, classify as benign/suspicious/malicious/unknown.",
)

INVESTIGATION = AgentRole(
    name="investigation_agent",
    purpose="Correlate host, user, IP, and domain evidence into a timeline and likely attack path.",
)

RESPONDER = AgentRole(
    name="responder_agent",
    purpose="Recommend the safest actions, maintain approval paths, and avoid destructive automation.",
)


def orchestrate_roles(case_summary: str) -> list[AgentRole]:
    return [TRACE_TRIAGE, INVESTIGATION, RESPONDER]
