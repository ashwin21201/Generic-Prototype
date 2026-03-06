"""Topology editing: add/remove blocks and edges, edit spec, save layout."""
import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models import Topology, TopologyNode, TopologyEdge

logger = logging.getLogger(__name__)


async def add_block(
    db: AsyncSession,
    topology_id: str,
    block_id: str,
    instance_name: Optional[str] = None,
    placement_hint: Optional[Dict] = None,
    spec_overrides: Optional[Dict] = None,
    target_node_ids: Optional[List[str]] = None,
) -> tuple:
    """Add a node for block_id to topology; optionally wire to target_node_ids. Returns (added_node_ids, new_edges, topology_version)."""
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalar_one_or_none()
    if not topo:
        raise ValueError("Topology not found")
    node_id = f"{block_id}_{uuid.uuid4().hex[:6]}"
    spec = dict(spec_overrides or {})
    if not spec:
        spec = {"cpu_count": 2, "ram_gb": 8}
    node = TopologyNode(
        id=node_id,
        topology_id=topology_id,
        block_id=block_id,
        instance_name=instance_name or block_id,
        layer=2,
        region=(placement_hint or {}).get("region"),
        spec=spec,
        capability_ref=block_id,
        category="compute",
        node_type="default",
        data_label=instance_name or block_id,
    )
    db.add(node)
    new_edges = []
    if target_node_ids:
        for tid in target_node_ids[:5]:
            edge_id = f"e_{uuid.uuid4().hex[:8]}"
            db.add(TopologyEdge(id=edge_id, topology_id=topology_id, source_node_id=node_id, target_node_id=tid, protocol="http", edge_type="traffic"))
            new_edges.append({"id": edge_id, "source": node_id, "target": tid})
    topo.version = (topo.version or 1) + 1
    await db.flush()
    return ([node_id], new_edges, topo.version)


async def remove_block(db: AsyncSession, topology_id: str, node_id: str, cascade: bool = True) -> tuple:
    """Remove node and edges involving it. Returns (removed_node_ids, removed_edge_ids, topology_version)."""
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalar_one_or_none()
    if not topo:
        raise ValueError("Topology not found")
    await db.execute(delete(TopologyNode).where(TopologyNode.topology_id == topology_id, TopologyNode.id == node_id))
    await db.execute(delete(TopologyEdge).where(
        TopologyEdge.topology_id == topology_id,
        or_(TopologyEdge.source_node_id == node_id, TopologyEdge.target_node_id == node_id),
    ))
    topo.version = (topo.version or 1) + 1
    await db.flush()
    return ([node_id], [], topo.version)


async def edit_spec(db: AsyncSession, topology_id: str, node_id: str, spec: Dict[str, Any]) -> tuple:
    """Update node spec. Returns (adjusted_spec, topology_version)."""
    result = await db.execute(select(TopologyNode).where(TopologyNode.topology_id == topology_id, TopologyNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise ValueError("Node not found")
    node.spec = {**(node.spec or {}), **spec}
    topo_result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = topo_result.scalar_one_or_none()
    if topo:
        topo.version = (topo.version or 1) + 1
    await db.flush()
    return (node.spec, topo.version if topo else 1)


async def add_edge(db: AsyncSession, topology_id: str, source_node_id: str, target_node_id: str, protocol: str = "http", edge_type: str = "traffic") -> Dict:
    """Create edge. Returns edge dict."""
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalar_one_or_none()
    if not topo:
        raise ValueError("Topology not found")
    edge_id = f"e_{uuid.uuid4().hex[:8]}"
    edge = TopologyEdge(id=edge_id, topology_id=topology_id, source_node_id=source_node_id, target_node_id=target_node_id, protocol=protocol, edge_type=edge_type)
    db.add(edge)
    topo.version = (topo.version or 1) + 1
    await db.flush()
    return {"id": edge_id, "source_node_id": source_node_id, "target_node_id": target_node_id}


async def remove_edge(db: AsyncSession, topology_id: str, edge_id: str) -> tuple:
    """Delete edge. Returns (removed_edge_ids, topology_version)."""
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalar_one_or_none()
    if not topo:
        raise ValueError("Topology not found")
    await db.execute(delete(TopologyEdge).where(TopologyEdge.topology_id == topology_id, TopologyEdge.id == edge_id))
    topo.version = (topo.version or 1) + 1
    await db.flush()
    return ([edge_id], topo.version)


async def save_layout(db: AsyncSession, topology_id: str, layout_mode: Optional[str] = None, node_positions: Optional[Dict[str, Any]] = None) -> int:
    """Save layout_mode and node_positions. Returns topology_version."""
    result = await db.execute(select(Topology).where(Topology.id == topology_id))
    topo = result.scalar_one_or_none()
    if not topo:
        raise ValueError("Topology not found")
    if layout_mode is not None:
        topo.layout_mode = layout_mode
    if node_positions is not None:
        topo.node_positions = node_positions
    topo.version = (topo.version or 1) + 1
    await db.flush()
    return topo.version
