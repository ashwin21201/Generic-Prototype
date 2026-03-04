from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RuleCheck(BaseModel):
    """Result of a single rule check"""
    rule_id: str
    status: str  # "pass", "fail", "warning"
    target_category: str
    details: str


class Violation(BaseModel):
    """A compliance violation"""
    rule_id: str
    severity: str
    message: str
    affected_nodes: List[str] = Field(default_factory=list)


class AutoRemediation(BaseModel):
    """Auto-remediation action taken"""
    action: str
    description: str


class ComplianceReportJSON(BaseModel):
    """Compliance evaluation report"""
    compliance_status: str  # "compliant", "non_compliant", "warning"
    risk_score: float
    sector: str
    policy_id: str
    evaluated_at: datetime = Field(default_factory=datetime.now)
    checks: List[RuleCheck] = Field(default_factory=list)
    violations: List[Violation] = Field(default_factory=list)
    auto_remediations_applied: List[str] = Field(default_factory=list)
    forbidden_patterns_checked: List[dict] = Field(default_factory=list)
