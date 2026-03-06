"""Topology editing: add/remove blocks and edges, edit spec, save layout."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from services.architecture.topology_editor import (
    add_block as editor_add_block,
    remove_block as editor_remove_block,
    edit_spec as editor_edit_spec,
    add_edge as editor_add_edge,
    remove_edge as editor_remove_edge,
    save_layout as editor_save_layout,
)

router = APIRouter()


class AddBlockRequest(BaseModel):
    block_id: str
    instance_name: Optional[str] = None
    placement_hint: Optional[dict] = None
    spec_overrides: Optional[dict] = None
    target_node_ids: Optional[List[str]] = None


class EditSpecRequest(BaseModel):
    cpu_count: Optional[int] = None
    ram_gb: Optional[int] = None
    disk_gb: Optional[int] = None
    min_instances: Optional[int] = None
    max_instances: Optional[int] = None


class AddEdgeRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    protocol: str = "http"
    edge_type: str = "traffic"


class SaveLayoutRequest(BaseModel):
    layout_mode: Optional[str] = None
    node_positions: Optional[dict] = None


@router.post("/{topology_id}/blocks")
async def add_block_route(topology_id: str, body: AddBlockRequest, db: AsyncSession = Depends(get_db)):
    try:
        added, new_edges, version = await editor_add_block(
            db, topology_id, body.block_id,
            instance_name=body.instance_name,
            placement_hint=body.placement_hint,
            spec_overrides=body.spec_overrides,
            target_node_ids=body.target_node_ids,
        )
        await db.commit()
        return {"added_nodes": added, "new_edges": new_edges, "topology_version": version}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{topology_id}/blocks/{node_id}")
async def remove_block_route(topology_id: str, node_id: str, cascade: bool = True, db: AsyncSession = Depends(get_db)):
    try:
        removed, removed_edges, version = await editor_remove_block(db, topology_id, node_id, cascade=cascade)
        await db.commit()
        return {"removed_nodes": removed, "removed_edges": removed_edges, "topology_version": version}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.patch("/{topology_id}/blocks/{node_id}")
async def swap_block_route(topology_id: str, node_id: str, db: AsyncSession = Depends(get_db)):
    raise HTTPException(501, "Swap block not implemented")


@router.patch("/{topology_id}/blocks/{node_id}/spec")
async def edit_spec_route(topology_id: str, node_id: str, body: EditSpecRequest, db: AsyncSession = Depends(get_db)):
    try:
        spec = body.model_dump(exclude_none=True)
        adjusted, version = await editor_edit_spec(db, topology_id, node_id, spec)
        await db.commit()
        return {"adjusted_spec": adjusted, "topology_version": version}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{topology_id}/edges")
async def add_edge_route(topology_id: str, body: AddEdgeRequest, db: AsyncSession = Depends(get_db)):
    try:
        edge = await editor_add_edge(db, topology_id, body.source_node_id, body.target_node_id, body.protocol, body.edge_type)
        await db.commit()
        return edge
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{topology_id}/edges/{edge_id}")
async def remove_edge_route(topology_id: str, edge_id: str, db: AsyncSession = Depends(get_db)):
    try:
        removed, version = await editor_remove_edge(db, topology_id, edge_id)
        await db.commit()
        return {"removed_edges": removed, "topology_version": version}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.put("/{topology_id}/layout")
async def save_layout_route(topology_id: str, body: SaveLayoutRequest, db: AsyncSession = Depends(get_db)):
    try:
        version = await editor_save_layout(db, topology_id, body.layout_mode, body.node_positions)
        await db.commit()
        return {"topology_version": version}
    except ValueError as e:
        raise HTTPException(404, str(e))
