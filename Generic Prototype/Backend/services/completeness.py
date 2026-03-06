"""Completeness scoring for intent: required vs recommended fields."""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _get_nested(data: Dict, path: str):
    keys = path.replace("]", "").split("[")[0].split(".")
    obj = data
    for k in keys:
        if k and isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return None
    return obj


def _is_filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def calculate_score(
    intent: Dict[str, Any],
    required_paths: List[str],
    recommended_paths: List[str],
) -> Dict[str, Any]:
    """
    Return completeness score and gaps.
    required_paths / recommended_paths are dot paths e.g. ["request_metadata.sector", "functional_requirements.data_types"].
    """
    filled_required = sum(1 for p in required_paths if _is_filled(_get_nested(intent, p)))
    filled_recommended = sum(1 for p in recommended_paths if _is_filled(_get_nested(intent, p)))
    total_required = len(required_paths)
    total_recommended = len(recommended_paths)
    score_required = filled_required / total_required if total_required else 1.0
    score_recommended = filled_recommended / total_recommended if total_recommended else 1.0
    # Weight required higher
    score = 0.7 * score_required + 0.3 * score_recommended
    missing_required = [p for p in required_paths if not _is_filled(_get_nested(intent, p))]
    missing_recommended = [p for p in recommended_paths if not _is_filled(_get_nested(intent, p))]
    is_complete = len(missing_required) == 0
    return {
        "score": round(score, 2),
        "is_complete": is_complete,
        "filled_required": filled_required,
        "total_required": total_required,
        "filled_recommended": filled_recommended,
        "total_recommended": total_recommended,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "gaps": missing_required + missing_recommended,
    }
