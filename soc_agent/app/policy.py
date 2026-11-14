from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ActionPolicy:
    action: str
    allowed_roles: tuple[str, ...]
    risk: Literal["low", "medium", "high"]
    requires_approval: bool = True


POLICIES = {
    "ticket_create": ActionPolicy("ticket_create", ("soc_analyst", "incident_manager"), "low", True),
    "host_isolate": ActionPolicy("host_isolate", ("incident_manager",), "high", True),
    "account_disable": ActionPolicy("account_disable", ("incident_manager",), "high", True),
    "ip_block": ActionPolicy("ip_block", ("incident_manager",), "high", True),
    "domain_block": ActionPolicy("domain_block", ("incident_manager",), "high", True),
    "log_delete": ActionPolicy("log_delete", ("security_admin",), "high", True),
}


def validate_action(action: str, role: str, risk: str) -> bool:
    policy = POLICIES.get(action)
    if not policy:
        return False
    if role not in policy.allowed_roles:
        return False
    if risk not in {"low", "medium", "high"}:
        return False
    if risk == "low" and policy.risk == "high":
        return False
    if risk == "medium" and policy.risk == "high":
        return False
    return True
