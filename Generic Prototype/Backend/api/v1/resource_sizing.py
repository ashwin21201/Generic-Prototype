"""Resource sizing: size block from intent, validate formula, get rules."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import CompliancePolicy, ConstraintRule

router = APIRouter()


class SizingRequest(BaseModel):
    block_id: str
    intent_json: dict
    org_id: str
    project_id: Optional[str] = None
    environment_id: Optional[str] = None


class FormulaValidationRequest(BaseModel):
    formula: str
    variables: dict = {}


@router.post("/size")
async def size_block(body: SizingRequest, db: AsyncSession = Depends(get_db)):
    try:
        from architecture_synthesis.blocks import BlockRegistryStore
        from architecture_synthesis.engines import resolve_variable_context, evaluate_sizing_formulas
        store = BlockRegistryStore()
        store.load()
        block = store.get_block(body.block_id)
        if not block:
            raise HTTPException(404, "Block not found")
        ctx = resolve_variable_context(body.intent_json, block)
        formulas = getattr(block, "sizing_formulas", None) or {}
        spec = dict(evaluate_sizing_formulas(formulas, ctx)) if formulas else {}
        bench = getattr(block, "resource_benchmarks", None)
        if not spec and bench:
            spec = {"cpu_count": getattr(bench, "min_cpu", 2), "ram_gb": getattr(bench, "min_ram_gb", 8)}
        if not spec:
            spec = {"cpu_count": 2, "ram_gb": 8}
        return {"block_id": body.block_id, "spec": spec}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/validate-formula")
async def validate_formula(body: FormulaValidationRequest):
    try:
        from architecture_synthesis.engines.formula_engine import evaluate_expression
        result = evaluate_expression(body.formula, body.variables)
        return {"valid": True, "error_message": None, "result": result}
    except Exception as e:
        return {"valid": False, "error_message": str(e), "result": None}


@router.get("/rules")
async def get_rules(org_id: str, project_id: Optional[str] = None, environment_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CompliancePolicy).where(CompliancePolicy.org_id == org_id))
    rows = result.scalars().all()
    rules = []
    for p in rows:
        r_result = await db.execute(select(ConstraintRule).where(ConstraintRule.policy_id == p.id))
        for r in r_result.scalars().all():
            rules.append({"policy_id": p.id, "resource_type": r.resource_type, "operation": r.operation, "policy_field": r.policy_field, "policy_value": r.policy_value})
    return rules
