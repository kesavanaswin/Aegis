from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class Verdict(str, Enum):
    benign = "benign"
    suspicious = "suspicious"
    malicious = "malicious"
    unknown = "unknown"


class Severity(str, Enum):
    informational = "informational"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=80)
    source: str = Field(..., min_length=1, max_length=200)
    observed_at: datetime | None = None
    text: str = Field(..., min_length=1, max_length=12000)


class AlertInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., min_length=1, max_length=200)
    alert_type: str = Field(..., min_length=1, max_length=200)
    source: str = Field(..., min_length=1, max_length=200)
    occurred_at: datetime
    severity: Severity
    host: str | None = None
    user: str | None = None
    ip: str | None = None
    domain: str | None = None
    raw_summary: str | None = None
    evidence: list[Evidence] = Field(..., min_length=1, max_length=60)

    def ensure_unique_ids(self):
        ids = [item.id for item in self.evidence]
        if len(ids) != len(set(ids)):
            raise ValueError("Evidence IDs must be unique.")


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(..., min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    confidence: float = Field(..., ge=0.0, le=1.0)


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str = Field(..., min_length=1, max_length=500)
    rationale: str = Field(..., min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    requires_human_review: bool = True


class InvestigationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    verdict: Verdict
    severity: Severity
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str = Field(..., min_length=1, max_length=4000)
    findings: list[Finding] = Field(default_factory=list, max_length=20)
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=20)
    uncertainties: list[str] = Field(default_factory=list, max_length=20)
    evidence_used: list[str] = Field(default_factory=list, max_length=50)
    analyst_review_required: bool = True


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(..., min_length=1, max_length=200)
    target: str = Field(..., min_length=1, max_length=300)
    reason: str = Field(..., min_length=1, max_length=2000)
    risk: Literal["low", "medium", "high"] = "medium"
    required_role: str = "soc_analyst"
