from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class NodeData(BaseModel):
    """Display data for a node"""
    label: str
    description: Optional[str] = None


class NodeConfig(BaseModel):
    """Configuration for a node"""
    cpu_count: Optional[int] = None
    ram_gb: Optional[int] = None
    disk_gb: Optional[int] = None
    disk_type: Optional[str] = "ssd"
    min_instances: Optional[int] = None
    max_instances: Optional[int] = None
    public_access: bool = False
    multi_az: bool = False
    scale_type: Optional[str] = None
    replication_role: Optional[str] = None


class Node(BaseModel):
    """Graph node representing an architecture component"""
    id: str
    type: str
    category: str
    region: Optional[str] = None
    capability_ref: Optional[str] = None
    data: NodeData
    config: Optional[NodeConfig] = None
    parent_node: Optional[str] = None  # Parent container (VPC/subnet)


class Edge(BaseModel):
    """Graph edge representing a connection"""
    id: str
    from_node: str = Field(..., alias="from")
    to: str
    protocol: Optional[str] = None
    type: str = "traffic"
    replication_mode: Optional[str] = None
    
    class Config:
        populate_by_name = True


class GraphTopologyJSON(BaseModel):
    """Graph representation of architecture"""
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
