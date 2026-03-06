"""Intent chat: schema-aware LLM greeting and message processing."""
import logging
from typing import Dict, Any, List, Optional

from .llm_provider import call_llm, parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM_TEMPLATE = """You are an Intelligent Cloud Architecture Discovery Agent.
Gather the following intent fields. Ask ONE question at a time. Use MCQ (A/B/C) when suitable, open response for numbers.

Current intent (already filled):
{current_intent}

Schema - required (must collect): {required_fields}
Schema - recommended: {recommended_fields}
Missing required: {missing_required}
Missing recommended: {missing_recommended}

Rules:
- Reply with ONLY a JSON object, no markdown.
- Keys: "bot_message" (string), "intent_updates" (object: field dot-path -> value), "is_complete" (boolean), "suggested_options" (array of strings, optional), "off_topic_response" (optional).
- When all required are filled set is_complete true and put final intent in intent_updates if needed.
- suggested_options: e.g. ["BFSI", "Healthcare", "E-commerce"] for sector.
- One question per turn. Accept free-text and suggest options when useful.
"""


async def _get_schema_context(org_id: str, current_intent: Dict[str, Any]) -> tuple:
    """Load active schema for org and return (schema_text, missing_required, missing_recommended, required_paths, recommended_paths)."""
    # Fallback schema MUST include fields that affect topology richness (distributed vs monolithic, sizing, policies)
    required = [
        "request_metadata.sector",
        "request_metadata.business_criticality",
        "functional_requirements.application_type",
        "non_functional_requirements.expected_rps_peak",
    ]
    recommended = [
        "functional_requirements.services",
        "functional_requirements.architecture_pattern",
        "data_requirements.storage_types",
        "data_requirements.data_types",
        "security_requirements.compliance_standards",
        "non_functional_requirements.concurrent_users_peak",
        "non_functional_requirements.response_time_p99_ms",
        "non_functional_requirements.availability_target_percent",
    ]
    default = (
        "Required: sector, business_criticality, application_type, expected_rps_peak. "
        "Recommended: services, architecture_pattern, storage_types, compliance, availability.",
        required,
        recommended,
        required,
        recommended,
    )
    try:
        from sqlalchemy import select
        from db.base import AsyncSessionLocal
        from models import IntentSchema
    except Exception as e:
        logger.warning("Schema load failed, using defaults: %s", e)
        return default

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(IntentSchema).where(IntentSchema.org_id == org_id, IntentSchema.is_active == True).limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return default
        fields = row.get_fields()
        if not fields:
            return default
        required_paths = [f.get("field_path") or f.get("path") for f in fields if f.get("required")]
        recommended_paths = [f.get("field_path") or f.get("path") for f in fields if not f.get("required")]
        if not required_paths:
            required_paths = ["request_metadata.sector", "functional_requirements.application_type"]
        missing_r = [p for p in required_paths if not _is_filled(current_intent, p)]
        missing_rec = [p for p in recommended_paths if not _is_filled(current_intent, p)]
        schema_text = "Required: " + ", ".join(required_paths) + ". Recommended: " + ", ".join(recommended_paths[:5])
        return schema_text, missing_r, missing_rec, required_paths, recommended_paths


def _is_filled(intent: Dict, path: str) -> bool:
    keys = path.split(".")
    obj = intent
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return False
    return obj is not None and obj != "" and (not isinstance(obj, (list, dict)) or len(obj) > 0)


def _set_intent_path(intent: Dict, path: str, value: Any) -> None:
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in intent:
            intent[k] = {}
        intent = intent[k]
    intent[keys[-1]] = value


class IntentChatService:
    def __init__(self):
        pass

    def get_schema_context(self, org_id: str, current_intent: Dict[str, Any]):
        return _get_schema_context(org_id, current_intent)

    async def get_initial_greeting(self, org_id: str, current_intent: Optional[Dict] = None) -> Dict[str, Any]:
        current_intent = current_intent or {}
        schema_text, missing_r, missing_rec, _, _ = await _get_schema_context(org_id, current_intent)
        system = _SYSTEM_TEMPLATE.format(
            current_intent=repr(current_intent),
            required_fields=schema_text,
            recommended_fields="",
            missing_required=missing_r,
            missing_recommended=missing_rec,
        )
        messages = [{"role": "user", "content": "Hello! I want to define my architecture requirements."}]
        content = await call_llm(system, messages)
        parsed = parse_llm_json(content)
        if parsed and "bot_message" in parsed:
            return {
                "bot_message": parsed["bot_message"],
                "intent_updates": parsed.get("intent_updates", {}),
                "is_complete": parsed.get("is_complete", False),
                "suggested_options": parsed.get("suggested_options", []),
            }
        return {"bot_message": content or "Hello! I'll ask a few questions to capture your architecture needs. What industry is this for? (e.g. BFSI, Healthcare, E-commerce)", "intent_updates": {}, "is_complete": False, "suggested_options": ["BFSI", "Healthcare", "E-commerce"]}

    async def process_message(
        self,
        org_id: str,
        user_message: str,
        current_intent: Dict[str, Any],
        conversation_history: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        schema_text, missing_r, missing_rec, _, _ = await _get_schema_context(org_id, current_intent)
        system = _SYSTEM_TEMPLATE.format(
            current_intent=repr(current_intent),
            required_fields=schema_text,
            recommended_fields="",
            missing_required=missing_r,
            missing_recommended=missing_rec,
        )
        messages = list(conversation_history) + [{"role": "user", "content": user_message}]
        content = await call_llm(system, messages)
        parsed = parse_llm_json(content)
        if parsed and "bot_message" in parsed:
            return {
                "bot_message": parsed["bot_message"],
                "intent_updates": parsed.get("intent_updates", {}),
                "is_complete": parsed.get("is_complete", False),
                "suggested_options": parsed.get("suggested_options", []),
            }
        return {"bot_message": content or "Thanks. What else can you tell me about your requirements?", "intent_updates": {}, "is_complete": False, "suggested_options": []}

    async def re_extract_intent(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Single LLM call to extract full intent from conversation text."""
        text = "\n".join(f"{m.get('role','')}: {m.get('content','')}" for m in conversation_history)
        system = "Extract ALL architecture intent fields from this conversation. Return a single JSON object with dot-path keys (e.g. request_metadata.sector, functional_requirements.application_type). No other text."
        content = await call_llm(system, [{"role": "user", "content": text}])
        parsed = parse_llm_json(content)
        return parsed if isinstance(parsed, dict) else {}
