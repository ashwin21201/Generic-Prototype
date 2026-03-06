"""Call LLM (Claude or OpenAI) and parse JSON response."""
import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


async def call_llm(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    """Call configured LLM; return assistant content as string."""
    try:
        from core.config import settings
        provider = (settings.LLM_PROVIDER or "claude").lower()
    except Exception:
        provider = "claude"

    if provider == "openai":
        return await _call_openai(system_prompt, messages)
    return await _call_claude(system_prompt, messages)


async def _call_claude(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    try:
        from anthropic import AsyncAnthropic
        from core.config import settings
        client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY or "")
        formatted = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = await client.messages.create(
            model=settings.CLAUDE_MODEL or "claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=formatted,
        )
        text = ""
        for block in getattr(resp, "content", []):
            if getattr(block, "type", None) == "text":
                text += getattr(block, "text", "")
        return text.strip()
    except Exception as e:
        logger.error("Claude call failed: %s", e)
        raise


async def _call_openai(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    try:
        from openai import AsyncOpenAI
        from core.config import settings
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY or "")
        formatted = [{"role": "system", "content": system_prompt}]
        for m in messages:
            formatted.append({"role": m["role"], "content": m["content"]})
        resp = await client.chat.completions.create(
            model=settings.OPENAI_MODEL or "gpt-4o-mini",
            messages=formatted,
            response_format={"type": "json_object"},
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error("OpenAI call failed: %s", e)
        raise


def parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """Strip markdown code fences and parse JSON."""
    if not text:
        return None
    cleaned = text.strip()
    for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            cleaned = m.group(1).strip()
            break
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
