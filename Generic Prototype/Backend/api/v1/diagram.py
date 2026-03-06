"""Diagram API: get diagram-ready JSON for a topology."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import Topology
from services.architecture.diagram_generator import generate_diagram

router = APIRouter()


@router.get("/topologies/{topology_id}/diagram")
async def get_diagram(
    topology_id: str,
    view: str = "logical",
    mode: str = "default",
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Topology).where(Topology.id == topology_id).options(
            selectinload(Topology.nodes),
            selectinload(Topology.edges),
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Topology not found")
    if row.status != "COMPLETED":
        raise HTTPException(400, "Topology is not completed")
    diagram_json = generate_diagram(
        topology_id=topology_id,
        nodes=row.nodes,
        edges=row.edges,
        view=view,
        mode=mode,
        intent_snapshot=row.intent_snapshot or {},
    )
    return diagram_json
