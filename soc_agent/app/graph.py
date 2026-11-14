from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from .adapters import ElasticAdapter, CrowdStrikeAdapter, VirusTotalAdapter, OktaAdapter
from .config import ELASTIC_URL, ELASTIC_API_KEY, CROWDSTRIKE_CLIENT_ID, CROWDSTRIKE_CLIENT_SECRET, VIRUSTOTAL_API_KEY, OKTA_DOMAIN, OKTA_API_TOKEN
from .models import AlertInput


class GraphState(TypedDict):
    alert: AlertInput
    evidence: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    verdict: str
    confidence: float


def build_graph():
    graph = StateGraph(GraphState)

    def collect_sources(state):
        alert = state["alert"]
        evidence = []

        if alert.host:
            adapter = CrowdStrikeAdapter(CROWDSTRIKE_CLIENT_ID, CROWDSTRIKE_CLIENT_SECRET)
            result = adapter.invoke(host=alert.host)
            evidence.append({"source": "crowdstrike", "result": result.__dict__})

        if alert.ip:
            adapter = VirusTotalAdapter(VIRUSTOTAL_API_KEY)
            result = adapter.invoke(value=alert.ip)
            evidence.append({"source": "virustotal_ip", "result": result.__dict__})

        if alert.domain:
            adapter = VirusTotalAdapter(VIRUSTOTAL_API_KEY)
            result = adapter.invoke(value=alert.domain)
            evidence.append({"source": "virustotal_domain", "result": result.__dict__})

        if alert.user:
            adapter = OktaAdapter(OKTA_DOMAIN, OKTA_API_TOKEN)
            result = adapter.invoke(user=alert.user)
            evidence.append({"source": "okta", "result": result.__dict__})

        adapter = ElasticAdapter(ELASTIC_URL, ELASTIC_API_KEY)
        result = adapter.invoke(query=f"{alert.alert_type} AND {alert.host or alert.user or alert.ip or 'unknown'}")
        evidence.append({"source": "elastic", "result": result.__dict__})

        return {"evidence": evidence}

    def summarize_triage(state):
        alert = state["alert"]
        evidence = state["evidence"]

        suspicious_count = 0
        malicious_count = 0

        for item in evidence:
            result = item["result"]
            details = result.get("details", {})
            if "malicious" in str(details).lower() or "suspicious" in str(details).lower():
                suspicious_count += 1
            if "malicious" in str(details).lower():
                malicious_count += 1

        if malicious_count > 0 or alert.severity in {"high", "critical"}:
            verdict = "suspicious"
        elif suspicious_count > 0:
            verdict = "suspicious"
        else:
            verdict = "unknown"

        findings = [{
            "statement": "The alert includes suspicious external infrastructure and enriched host activity.",
            "evidence_ids": ["tool:elastic", "tool:virustotal_ip", "tool:crowdstrike"],
            "confidence": 0.82 if verdict == "suspicious" else 0.49,
        }]

        recommendations = [{
            "step": "Review the host and identity context, then confirm with the analyst before any blocking action.",
            "rationale": "The evidence is suspicious but not yet confirmed malicious.",
            "evidence_ids": ["tool:elastic", "tool:virustotal_ip"],
            "requires_human_review": True,
        }]

        return {
            "findings": findings,
            "recommendations": recommendations,
            "verdict": verdict,
            "confidence": 0.82 if verdict == "suspicious" else 0.49,
        }

    graph.add_node("collect_sources", collect_sources)
    graph.add_node("summarize_triage", summarize_triage)
    graph.set_entry_point("collect_sources")
    graph.add_edge("collect_sources", "summarize_triage")
    graph.add_edge("summarize_triage", END)

    return graph.compile()
