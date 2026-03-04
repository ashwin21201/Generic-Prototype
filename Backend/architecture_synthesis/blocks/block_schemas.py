from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class IntentFieldMapping(BaseModel):
    """Maps an intent JSON path to a variable name for formula evaluation (Configurator §5)."""
    intent_path: str  # e.g. "non_functional_requirements.expected_rps_peak"
    maps_to: str      # e.g. "rps"
    required: bool = False
    default_value: Optional[Any] = None


class ResourceBenchmarks(BaseModel):
    """Resource benchmarks for sizing calculations"""
    rps_per_cpu: Optional[int] = None
    ram_per_cpu_gb: Optional[int] = None
    min_cpu: int = 1
    min_ram_gb: int = 4
    disk_gb_default: Optional[int] = None
    data_per_cpu_gb: Optional[int] = None
    disk_multiplier: Optional[float] = None
    cache_per_cpu_gb: Optional[int] = None
    ram_multiplier: Optional[float] = None
    events_per_cpu: Optional[int] = None
    metrics_per_cpu: Optional[int] = None


class PerformanceProfile(BaseModel):
    """Performance characteristics of a block"""
    max_rps_supported: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    max_throughput_per_sec: Optional[int] = None
    max_throughput_mbps: Optional[int] = None
    max_events_per_sec: Optional[int] = None
    max_metrics_per_sec: Optional[int] = None


class CostProfile(BaseModel):
    """Cost characteristics of a block"""
    base_monthly_cost_usd: float
    cost_per_million_requests_usd: Optional[float] = None
    cost_per_million_events_usd: Optional[float] = None
    cost_per_gb_month: Optional[float] = None
    cost_per_gb_ingested: Optional[float] = None


class Interfaces(BaseModel):
    """Network interfaces for a block"""
    ingress: List[str] = Field(default_factory=list)
    egress: List[str] = Field(default_factory=list)


class BlockDefinition(BaseModel):
    """Architecture building block definition (Configurator §5, §17)."""
    block_id: str
    category: str
    capabilities_provided: Dict[str, bool] = Field(default_factory=dict)
    interfaces: Interfaces
    requires: List[str] = Field(default_factory=list)
    optional_dependencies: List[str] = Field(default_factory=list)
    compatible_with: List[str] = Field(default_factory=list)
    conflicts_with: List[str] = Field(default_factory=list)
    performance_profile: PerformanceProfile
    cost_profile: CostProfile
    compliance_tags: List[str] = Field(default_factory=list)
    complexity_score: int = 5
    resource_benchmarks: Optional[ResourceBenchmarks] = None
    # Configurator: data-driven field mapping and sizing (§5, §6)
    intent_field_mappings: List[IntentFieldMapping] = Field(default_factory=list)
    sizing_formulas: Dict[str, str] = Field(default_factory=dict)  # e.g. {"cpu_count": "max(min_cpu, ceil(rps / rps_per_cpu))"}


class BlockRegistry(BaseModel):
    """Registry of all available blocks"""
    blocks: List[BlockDefinition]


class DeploymentTopology(BaseModel):
    """Deployment topology metadata"""
    regions: List[str] = Field(default_factory=list)
    active_active: bool = False
    multi_az: bool = False
    replication_required: bool = False


class ScoringDetail(BaseModel):
    """Detailed scoring for a block"""
    performance_score: float = 0.0
    cost_score: float = 0.0
    compliance_score: float = 0.0
    simplicity_score: float = 0.0
    final_weighted_score: float = 0.0


class SelectedArchitectureJSON(BaseModel):
    """Output of block selection"""
    architecture_id: str
    selected_blocks: List[str]
    deployment_topology: DeploymentTopology
    scoring_summary: ScoringDetail
    estimated_monthly_cost_usd: float
    compliance_alignment: List[str] = Field(default_factory=list)
