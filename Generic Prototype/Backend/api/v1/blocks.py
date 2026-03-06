"""Blocks API: list and get from registry (JSON); create/update/delete to DB."""
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import Block

router = APIRouter()


def _load_registry_blocks():
    """Load blocks from JSON registry."""
    try:
        from architecture_synthesis.blocks import BlockRegistryStore
        store = BlockRegistryStore()
        store.load()
        return store.get_all_blocks()
    except Exception:
        return []


@router.get("/")
async def list_blocks(category: Optional[str] = None, active: bool = True):
    blocks = _load_registry_blocks()
    out = []
    for b in blocks:
        if category and (getattr(b, "category", None) or "") != category:
            continue
        out.append({
            "block_id": b.block_id,
            "name": getattr(b, "name", b.block_id),
            "category": getattr(b, "category", ""),
            "version": getattr(b, "version", "1.0"),
            "capabilities": getattr(b, "capabilities", {}) or {},
        })
    return out


@router.get("/{block_id}")
async def get_block(block_id: str):
    from architecture_synthesis.blocks import BlockRegistryStore
    store = BlockRegistryStore()
    store.load()
    b = store.get_block(block_id)
    if not b:
        raise HTTPException(404, "Block not found")
    return {
        "block_id": b.block_id,
        "name": getattr(b, "name", b.block_id),
        "category": getattr(b, "category", ""),
        "version": getattr(b, "version", "1.0"),
        "capabilities": getattr(b, "capabilities", {}) or {},
    }


class BlockCreate(BaseModel):
    name: str
    category: str
    block_id: str
    version: str = "1.0"
    capabilities: dict = {}


@router.post("/")
async def create_block(body: BlockCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.block_id == body.block_id))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Block ID already exists")
    block = Block(block_id=body.block_id, name=body.name, category=body.category, version=body.version, capabilities=body.capabilities, active=True)
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return {"block_id": block.block_id, "name": block.name, "category": block.category}


@router.put("/{block_id}")
async def update_block(block_id: str, body: BlockCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.block_id == block_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Block not found in DB")
    row.name = body.name
    row.category = body.category
    row.version = body.version
    row.capabilities = body.capabilities
    await db.commit()
    return {"block_id": row.block_id}


@router.delete("/{block_id}")
async def deactivate_block(block_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Block).where(Block.block_id == block_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Block not found in DB")
    row.active = False
    await db.commit()
    return {"block_id": block_id, "active": False}
