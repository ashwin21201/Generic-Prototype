"""Governance: audit logs, approve/reject, rollback schema, export/import."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import AuditLog, IntentSchema

router = APIRouter()


class ApprovalRequest(BaseModel):
    approved_by: Optional[str] = None
    comment: Optional[str] = None


class RejectionRequest(BaseModel):
    rejected_by: Optional[str] = None
    reason: Optional[str] = None


class RollbackRequest(BaseModel):
    target_version: str
    rolled_back_by: Optional[str] = None


@router.get("/audit-logs")
async def get_audit_logs(org_id: str, entity_type: Optional[str] = None, entity_id: Optional[str] = None, limit: int = 50, offset: int = 0, db: AsyncSession = Depends(get_db)):
    q = select(AuditLog).where(AuditLog.org_id == org_id)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    result = await db.execute(q.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset))
    rows = result.scalars().all()
    return [{"id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id, "action": r.action, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.get("/audit-logs/pending")
async def get_pending_approvals(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.org_id == org_id, AuditLog.status == "pending"))
    rows = result.scalars().all()
    return [{"id": r.id, "entity_type": r.entity_type, "entity_id": r.entity_id, "action": r.action} for r in rows]


@router.get("/audit-logs/{log_id}")
async def get_audit_log(log_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Audit log not found")
    return {"id": row.id, "org_id": row.org_id, "entity_type": row.entity_type, "entity_id": row.entity_id, "action": row.action, "payload": row.payload, "status": row.status, "created_at": row.created_at.isoformat() if row.created_at else None}


@router.post("/audit-logs/{log_id}/approve")
async def approve_change(log_id: int, body: ApprovalRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Audit log not found")
    row.status = "approved"
    await db.commit()
    return {"id": row.id, "status": "approved"}


@router.post("/audit-logs/{log_id}/reject")
async def reject_change(log_id: int, body: RejectionRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Audit log not found")
    row.status = "rejected"
    await db.commit()
    return {"id": row.id, "status": "rejected"}


@router.get("/entities/{entity_type}/{entity_id}/history")
async def get_entity_history(entity_type: str, entity_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id).order_by(AuditLog.created_at.desc()))
    rows = result.scalars().all()
    return [{"id": r.id, "action": r.action, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]


@router.post("/schemas/{org_id}/rollback")
async def rollback_schema(org_id: str, body: RollbackRequest, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update
    result = await db.execute(select(IntentSchema).where(IntentSchema.org_id == org_id, IntentSchema.version == body.target_version))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Schema version not found")
    await db.execute(update(IntentSchema).where(IntentSchema.org_id == org_id).values(is_active=False))
    row.is_active = True
    await db.commit()
    return {"org_id": org_id, "active_version": body.target_version}


@router.post("/export")
async def export_config():
    return {"message": "Export not implemented", "data": {}}


@router.post("/import")
async def import_config():
    return {"message": "Import not implemented"}
