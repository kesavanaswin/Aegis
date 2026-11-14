from datetime import datetime

from soc_agent.app.models import AlertInput, Evidence, Severity


def build_alert():
    return AlertInput(
        case_id="CASE-100",
        alert_type="suspicious_powershell_execution",
        source="CrowdStrike",
        occurred_at=datetime.fromisoformat("2026-11-14T09:57:00+00:00"),
        severity=Severity.high,
        host="host-01",
        user="alice",
        ip="198.51.100.4",
        domain="malware.example",
        raw_summary="PowerShell executed and connected to suspicious infrastructure.",
        evidence=[
            Evidence(id="ev-1", source="EDR", observed_at=datetime.fromisoformat("2026-11-14T09:58:00+00:00"), text="powershell.exe launched with an encoded command."),
            Evidence(id="ev-2", source="SIEM", observed_at=datetime.fromisoformat("2026-11-14T09:59:00+00:00"), text="Outbound HTTP to 198.51.100.4 occurred immediately after execution."),
        ],
    )


def test_alert_valid():
    alert = build_alert()
    alert.ensure_unique_ids()
    assert alert.case_id == "CASE-100"
    assert len(alert.evidence) == 2


def test_action_policy_high_risk():
    from soc_agent.app.policy import validate_action
    assert validate_action("host_isolate", "incident_manager", "high") is True
    assert validate_action("host_isolate", "soc_analyst", "high") is False
