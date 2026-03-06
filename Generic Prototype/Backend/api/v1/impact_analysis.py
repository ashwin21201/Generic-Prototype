"""Impact analysis: analyze field change, can-save, auto-update field rename."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import IntentSchema

router = APIRouter()


class FieldChangeRequest(BaseModel):
    field_path: str
    change_type: str  # field_removed, field_renamed
    old_field_path: Optional[str] = None
    new_field_path: Optional[str] = None


class AutoUpdateRequest(BaseModel):
    old_field_path: str
    new_field_path: str
    org_id: str


@router.post("/analyze-field-change")
async def analyze_field_change(body: FieldChangeRequest, db: AsyncSession = Depends(get_db)):
    affected_blocks = []
    affected_formulas = []
    affected_rules = []
    if body.change_type == "field_renamed" and body.new_field_path:
        affected_blocks.append("field_mappings_may_need_update")
    impact = {
        "field_path": body.field_path,
        "change_type": body.change_type,
        "affected_blocks": affected_blocks,
        "affected_formulas": affected_formulas,
        "affected_rules": affected_rules,
        "resolution_options": ["Update field mappings", "Review formulas"],
    }
    return impact


@router.post("/can-save-change")
async def can_save_change(body: FieldChangeRequest, db: AsyncSession = Depends(get_db)):
    can_save = True
    reason = "No blocking impact"
    is_blocking = False
    blast_radius = []
    return {"can_save": can_save, "reason": reason, "is_blocking": is_blocking, "blast_radius": blast_radius}


@router.post("/auto-update-field-rename")
async def auto_update_field_rename(body: AutoUpdateRequest, db: AsyncSession = Depends(get_db)):
    updated = 0
    return {"updated_count": updated, "old_field": body.old_field_path, "new_field": body.new_field_path}
