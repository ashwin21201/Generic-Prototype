"""Policy API: CRUD CompliancePolicy and ConstraintRule."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import CompliancePolicy, ConstraintRule

router = APIRouter()


class ConstraintRuleCreate(BaseModel):
    resource_type: Optional[str] = None
    operation: Optional[str] = None
    policy_field: Optional[str] = None
    policy_value: Optional[str] = None


class PolicyCreate(BaseModel):
    org_id: str
    level: Optional[str] = None
    version: str = "1.0"
    constraint_rules: List[ConstraintRuleCreate] = []


class PolicyUpdate(BaseModel):
    level: Optional[str] = None
    version: Optional[str] = None
    constraint_rules: Optional[List[ConstraintRuleCreate]] = None


@router.get("/")
async def list_policies(org_id: str, level: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    q = select(CompliancePolicy).where(CompliancePolicy.org_id == org_id)
    if level:
        q = q.where(CompliancePolicy.level == level)
    result = await db.execute(q.order_by(CompliancePolicy.created_at.desc()))
    rows = result.scalars().all()
    return [{"id": r.id, "org_id": r.org_id, "level": r.level, "version": r.version} for r in rows]


@router.get("/{policy_id}")
async def get_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CompliancePolicy).where(CompliancePolicy.id == policy_id).options(selectinload(CompliancePolicy.constraint_rules))
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Policy not found")
    return {
        "id": row.id,
        "org_id": row.org_id,
        "level": row.level,
        "version": row.version,
        "constraint_rules": [{"id": r.id, "resource_type": r.resource_type, "operation": r.operation, "policy_field": r.policy_field, "policy_value": r.policy_value} for r in row.constraint_rules],
    }


@router.post("/")
async def create_policy(body: PolicyCreate, db: AsyncSession = Depends(get_db)):
    policy = CompliancePolicy(org_id=body.org_id, level=body.level, version=body.version)
    db.add(policy)
    await db.flush()
    for r in body.constraint_rules:
        rule = ConstraintRule(policy_id=policy.id, resource_type=r.resource_type, operation=r.operation, policy_field=r.policy_field, policy_value=r.policy_value)
        db.add(rule)
    await db.commit()
    await db.refresh(policy)
    return {"id": policy.id, "org_id": policy.org_id}


@router.put("/{policy_id}")
async def update_policy(policy_id: int, body: PolicyUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompliancePolicy).where(CompliancePolicy.id == policy_id).options(selectinload(CompliancePolicy.constraint_rules)))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Policy not found")
    if body.level is not None:
        row.level = body.level
    if body.version is not None:
        row.version = body.version
    if body.constraint_rules is not None:
        for r in row.constraint_rules:
            await db.delete(r)
        for r in body.constraint_rules:
            db.add(ConstraintRule(policy_id=policy_id, resource_type=r.resource_type, operation=r.operation, policy_field=r.policy_field, policy_value=r.policy_value))
    await db.commit()
    return {"id": row.id}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompliancePolicy).where(CompliancePolicy.id == policy_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Policy not found")
    await db.delete(row)
    await db.commit()
    return {"deleted": policy_id}
