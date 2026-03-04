from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class PolicyMetadata(BaseModel):
    policy_id: str
    policy_name: str
    sector: str
    region: Optional[str] = None
    version: str
    status: Literal["active", "inactive", "draft"]
    priority: int = 1
    enforcement_mode: Literal["strict", "permissive", "audit"]
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None


class Applicability(BaseModel):
    environments: List[str] = Field(default_factory=list)
    business_criticality: List[str] = Field(default_factory=list)
    cloud_providers: List[str] = Field(default_factory=list)


class Condition(BaseModel):
    field: Optional[str] = None
    operator: Optional[Literal["equals", "not_equals", "greater_than", "less_than", "greater_or_equal", "less_or_equal", "in", "not_in"]] = None
    value: Optional[Any] = None
    must_be_preceded_by: Optional[str] = None  # For relationship rules


class AutoRemediation(BaseModel):
    enabled: bool
    action: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Rule(BaseModel):
    rule_id: str
    description: str
    rule_type: Literal["capability", "deployment", "topology", "relationship", "quantitative"]
    target_category: str
    severity: Literal["critical", "high", "medium", "low"]
    condition: Optional[Condition] = None
    additional_constraints: Optional[Dict[str, Any]] = None
    auto_remediation: Optional[AutoRemediation] = None


class ForbiddenPattern(BaseModel):
    pattern_id: str
    description: str
    detection_logic: Dict[str, Any]
    severity: Literal["critical", "high", "medium", "low"]


class MandatoryBlock(BaseModel):
    block_id: str
    reason: str


class PolicyException(BaseModel):
    exception_id: str
    applies_to: List[str]
    expires_at: Optional[datetime] = None


class EvaluationStrategy(BaseModel):
    conflict_resolution: str = "highest_priority_wins"
    rule_aggregation: str = "all_must_pass"
    custom_plugins_allowed: bool = False


class Reporting(BaseModel):
    generate_violation_report: bool = True
    include_auto_remediation_details: bool = True
    include_risk_score: bool = True


class PolicyJSON(BaseModel):
    policy_metadata: PolicyMetadata
    applicability: Applicability
    rules: List[Rule] = Field(default_factory=list)
    forbidden_patterns: List[ForbiddenPattern] = Field(default_factory=list)
    mandatory_blocks: List[MandatoryBlock] = Field(default_factory=list)
    policy_exceptions: List[PolicyException] = Field(default_factory=list)
    evaluation_strategy: EvaluationStrategy
    reporting: Reporting


class MergedPolicy(BaseModel):
    """Merged policy from multiple policy sources"""
    policy_metadata: PolicyMetadata
    applicability: Applicability
    rules: List[Rule] = Field(default_factory=list)
    forbidden_patterns: List[ForbiddenPattern] = Field(default_factory=list)
    mandatory_blocks: List[MandatoryBlock] = Field(default_factory=list)
    policy_exceptions: List[PolicyException] = Field(default_factory=list)
    evaluation_strategy: EvaluationStrategy
    reporting: Reporting
    source_policies: List[str] = Field(default_factory=list)
