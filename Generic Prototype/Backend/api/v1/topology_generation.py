"""Topology generation: POST generate, GET list, GET by id."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import Topology, TopologyNode, TopologyEdge
from services.architecture.topology_generator import generate_topology

router = APIRouter()


class GenerateTopologyRequest(BaseModel):
    intent_json: dict
    project_id: str
    org_id: str
    schema_version: Optional[str] = None
    session_id: Optional[str] = None


@router.post("")
async def generate_topology_route(body: GenerateTopologyRequest, db: AsyncSession = Depends(get_db)):
    try:
        topology_id, selected_blocks, warnings = await generate_topology(
            db,
            org_id=body.org_id,
            project_id=body.project_id,
            intent_json=body.intent_json,
            schema_version=body.schema_version,
            session_id=body.session_id,
        )
        result = await db.execute(select(Topology).where(Topology.id == topology_id))
        topo = result.scalar_one_or_none()
        if body.session_id and topo:
            topo.session_id = body.session_id
            await db.commit()
        return {
            "topology_id": topology_id,
            "selected_blocks": selected_blocks,
            "warnings": warnings,
            "status": "COMPLETED",
        }
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Topology generation failed: {e}")


@router.get("")
async def list_topologies(org_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Topology).where(Topology.org_id == org_id).order_by(Topology.created_at.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "topology_id": r.id,
            "project_id": r.project_id,
            "org_id": r.org_id,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "session_id": r.session_id,
        }
        for r in rows
    ]


@router.get("/{topology_id}")
async def get_topology(topology_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Topology).where(Topology.id == topology_id).options(
            selectinload(Topology.nodes),
            selectinload(Topology.edges),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Topology not found")
    nodes = [
        {
            "id": n.id,
            "block_id": n.block_id,
            "category": n.category,
            "layer": n.layer,
            "region": n.region,
            "data_label": n.data_label,
            "spec": n.spec or {},
        }
        for n in row.nodes
    ]
    edges = [
        {"id": e.id, "source_node_id": e.source_node_id, "target_node_id": e.target_node_id, "protocol": e.protocol, "edge_type": e.edge_type}
        for e in row.edges
    ]
    return {
        "topology_id": row.id,
        "project_id": row.project_id,
        "org_id": row.org_id,
        "status": row.status,
        "session_id": row.session_id,
        "nodes": nodes,
        "edges": edges,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
