from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class Product(BaseModel):
    """Product definition from a catalog"""
    product_id: str
    product_name: str
    category: str
    capabilities: Dict[str, bool] = Field(default_factory=dict)
    regions_supported: List[str] = Field(default_factory=list)
    performance_tiers: Optional[List[str]] = None
    compliance_tags: List[str] = Field(default_factory=list)
    monthly_cost_usd_estimate: float


class ProductCatalog(BaseModel):
    """Product catalog for a provider"""
    provider: str
    provider_display_name: str
    products: List[Product]


class ResolvedProduct(BaseModel):
    """Resolved product for a node"""
    provider: str
    product_name: str
    product_id: str
    recommended: bool = False


class ResolvedNode(BaseModel):
    """Node with resolved products embedded"""
    id: str
    type: str
    category: str
    region: Optional[str] = None
    capability_ref: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    config: Optional[Dict[str, Any]] = None
    resolved_products: List[ResolvedProduct] = Field(default_factory=list)


class ResolvedArchitectureJSON(BaseModel):
    """Architecture with product mappings embedded in nodes"""
    architecture_id: str
    graph: Dict[str, Any]  # Graph with nodes containing resolved_products
    estimated_monthly_cost_usd: float
