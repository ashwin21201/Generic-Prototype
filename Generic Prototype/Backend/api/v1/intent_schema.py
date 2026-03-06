"""Intent schema API: get current, list versions, create, validate."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import IntentSchema

router = APIRouter()


class IntentFieldCreate(BaseModel):
    field_path: str
    section: Optional[str] = None
    field_type: str = "string"
    required: bool = False
    description: Optional[str] = None


class IntentSchemaCreate(BaseModel):
    org_id: str
    version: str
    fields: List[IntentFieldCreate]


class ValidateIntentRequest(BaseModel):
    intent: dict
    org_id: str


@router.get("/")
async def get_current_schema(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IntentSchema).where(IntentSchema.org_id == org_id, IntentSchema.is_active == True).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "No active schema for this org")
    return {"id": row.id, "org_id": row.org_id, "version": row.version, "fields": row.get_fields()}


@router.get("/versions")
async def list_versions(org_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSchema).where(IntentSchema.org_id == org_id).order_by(IntentSchema.created_at.desc()))
    rows = result.scalars().all()
    return [{"id": r.id, "version": r.version, "is_active": r.is_active} for r in rows]


@router.post("/")
async def create_schema(body: IntentSchemaCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSchema).where(IntentSchema.org_id == body.org_id, IntentSchema.version == body.version))
    if result.scalar_one_or_none():
        raise HTTPException(400, "Schema version already exists")
    from sqlalchemy import update
    await db.execute(update(IntentSchema).where(IntentSchema.org_id == body.org_id).values(is_active=False))
    schema_fields = [f.model_dump() for f in body.fields]
    row = IntentSchema(org_id=body.org_id, version=body.version, is_active=True, schema_fields=schema_fields)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "org_id": row.org_id, "version": row.version, "fields": row.get_fields()}


@router.post("/validate")
async def validate_intent(body: ValidateIntentRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IntentSchema).where(IntentSchema.org_id == body.org_id, IntentSchema.is_active == True).limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"valid": True, "errors": []}
    required_paths = [f.get("field_path") or f.get("path") for f in row.get_fields() if f.get("required")]
    errors = []
    for path in required_paths:
        keys = path.split(".")
        obj = body.intent
        for k in keys:
            if isinstance(obj, dict) and k in obj:
                obj = obj[k]
            else:
                errors.append(f"Missing required: {path}")
                break
        if isinstance(obj, dict):
            continue
        if obj is None or (isinstance(obj, str) and not obj.strip()) or (isinstance(obj, (list, dict)) and len(obj) == 0):
            errors.append(f"Missing required: {path}")
    return {"valid": len(errors) == 0, "errors": errors}
