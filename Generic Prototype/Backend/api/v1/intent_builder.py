"""Intent builder API: sessions, start-chat, chat, truncate, submit."""
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_db
from models import IntentSession, IntentSchema
from services.llm.intent_chat_service import IntentChatService
from services.completeness import calculate_score

router = APIRouter()


class CreateSessionRequest(BaseModel):
    org_id: str
    project_id: Optional[str] = None


class ChatRequest(BaseModel):
    message: str


class TruncateRequest(BaseModel):
    keep_history_count: int


class SubmitRequest(BaseModel):
    finalize: bool = True


def _get_required_recommended_paths(fields: list) -> tuple:
    required = [f.get("field_path") or f.get("path") for f in fields if f.get("required")]
    recommended = [f.get("field_path") or f.get("path") for f in fields if not f.get("required")]
    if not required:
        required = ["request_metadata.sector", "functional_requirements.application_type"]
    return required, recommended


def _set_intent_field(intent: dict, path: str, value: Any) -> None:
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in intent:
            intent[k] = {}
        intent = intent[k]
    intent[keys[-1]] = value


@router.get("/sessions")
async def list_sessions(org_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IntentSession).where(IntentSession.org_id == org_id).order_by(IntentSession.created_at.desc()).limit(limit)
    )
    rows = result.scalars().all()
    return [{"id": r.id, "org_id": r.org_id, "project_id": r.project_id, "status": r.status, "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/sessions")
async def create_session(body: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    sid = str(uuid.uuid4())
    session = IntentSession(
        id=sid,
        org_id=body.org_id,
        project_id=body.project_id,
        status="IN_PROGRESS",
        inferred_intent={},
        conversation_history=[],
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return {"id": session.id, "org_id": session.org_id, "project_id": session.project_id, "status": session.status}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSession).where(IntentSession.id == session_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Session not found")
    return {
        "id": row.id,
        "org_id": row.org_id,
        "project_id": row.project_id,
        "status": row.status,
        "inferred_intent": row.inferred_intent or {},
        "conversation_history": row.conversation_history or [],
        "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
    }


@router.post("/sessions/{session_id}/start-chat")
async def start_chat(session_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSession).where(IntentSession.id == session_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Session not found")
    if row.conversation_history:
        last = row.conversation_history[-1]
        if last.get("role") == "assistant":
            required, recommended = await _get_required_recommended_paths_from_db(db, row.org_id)
            comp = calculate_score(row.inferred_intent or {}, required, recommended)
            return {"bot_message": last.get("content", ""), "suggested_options": [], "completeness": comp}
    svc = IntentChatService()
    out = await svc.get_initial_greeting(row.org_id, row.inferred_intent or {})
    for k, v in (out.get("intent_updates") or {}).items():
        _set_intent_field(row.inferred_intent, k, v)
    row.conversation_history = [
        {"role": "user", "content": "Hello! I want to define my architecture requirements."},
        {"role": "assistant", "content": out["bot_message"]},
    ]
    await db.commit()
    await db.refresh(row)
    required, recommended = await _get_required_recommended_paths_from_db(db, row.org_id)
    comp = calculate_score(row.inferred_intent or {}, required, recommended)
    return {"bot_message": out["bot_message"], "suggested_options": out.get("suggested_options", []), "completeness": comp}


async def _get_required_recommended_paths_from_db(db: AsyncSession, org_id: str) -> tuple:
    result = await db.execute(select(IntentSchema).where(IntentSchema.org_id == org_id, IntentSchema.is_active == True).limit(1))
    row = result.scalar_one_or_none()
    if not row or not row.get_fields():
        # Default schema fallback (chatbot must ask the fields that materially affect topology)
        required = [
            "request_metadata.sector",
            "request_metadata.business_criticality",
            "functional_requirements.application_type",
            "non_functional_requirements.expected_rps_peak",
        ]
        recommended = [
            "functional_requirements.services",
            "data_requirements.storage_types",
            "data_requirements.data_types",
            "non_functional_requirements.concurrent_users_peak",
            "non_functional_requirements.response_time_p99_ms",
            "security_requirements.compliance_standards",
            "functional_requirements.architecture_pattern",
        ]
        return required, recommended
    return _get_required_recommended_paths(row.get_fields())


@router.post("/sessions/{session_id}/chat")
async def chat(session_id: str, body: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSession).where(IntentSession.id == session_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Session not found")
    if row.status == "SUBMITTED":
        raise HTTPException(400, "Session already submitted")
    if not row.conversation_history:
        row.conversation_history = []
    row.conversation_history.append({"role": "user", "content": body.message})
    svc = IntentChatService()
    out = await svc.process_message(row.org_id, body.message, row.inferred_intent or {}, row.conversation_history)
    for k, v in (out.get("intent_updates") or {}).items():
        _set_intent_field(row.inferred_intent, k, v)
    row.conversation_history.append({"role": "assistant", "content": out["bot_message"]})
    if out.get("is_complete"):
        row.status = "PREVIEW"
    await db.commit()
    await db.refresh(row)
    required, recommended = await _get_required_recommended_paths_from_db(db, row.org_id)
    comp = calculate_score(row.inferred_intent or {}, required, recommended)
    return {"bot_message": out["bot_message"], "intent_updates": out.get("intent_updates", {}), "completeness": comp}


@router.post("/sessions/{session_id}/truncate")
async def truncate_history(session_id: str, body: TruncateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSession).where(IntentSession.id == session_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Session not found")
    hist = row.conversation_history or []
    row.conversation_history = hist[: body.keep_history_count]
    svc = IntentChatService()
    extracted = await svc.re_extract_intent(row.conversation_history)
    if extracted:
        row.inferred_intent = extracted
    row.status = "IN_PROGRESS"
    await db.commit()
    await db.refresh(row)
    last_bot = ""
    for m in reversed(row.conversation_history):
        if m.get("role") == "assistant":
            last_bot = m.get("content", "")
            break
    required, recommended = await _get_required_recommended_paths_from_db(db, row.org_id)
    comp = calculate_score(row.inferred_intent or {}, required, recommended)
    return {"bot_message": last_bot, "intent": row.inferred_intent, "completeness": comp}


@router.post("/sessions/{session_id}/submit")
async def submit_intent(session_id: str, body: SubmitRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(IntentSession).where(IntentSession.id == session_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Session not found")
    required, recommended = await _get_required_recommended_paths_from_db(db, row.org_id)
    comp = calculate_score(row.inferred_intent or {}, required, recommended)
    if row.status == "SUBMITTED":
        return {"intent_json": row.inferred_intent, "completeness": comp, "gaps": comp.get("gaps", [])}
    if body.finalize:
        row.status = "SUBMITTED"
        row.submitted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(row)
    return {"intent_json": row.inferred_intent, "completeness": comp, "gaps": comp.get("gaps", [])}
