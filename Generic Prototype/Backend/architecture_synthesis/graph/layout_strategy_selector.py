"""
Layout Strategy Selector — Maps architecture pattern to layout algorithm.
"""
import logging
from typing import Optional

from ..pattern import ArchitecturePattern

logger = logging.getLogger(__name__)

# Pattern type -> layout strategy name (consumed by layout engine)
PATTERN_TO_STRATEGY = {
    "web_service": "layered_vertical",
    "event_driven": "radial",
    "data_pipeline": "horizontal",
    "serverless": "radial",
    "mesh": "force",
}


def get_layout_strategy(pattern: Optional[ArchitecturePattern]) -> str:
    """Return layout strategy name for the given pattern. Default: layered_vertical."""
    if not pattern:
        return "layered_vertical"
    strategy = PATTERN_TO_STRATEGY.get(pattern.type, "layered_vertical")
    logger.info(f"Layout strategy: {strategy} (pattern={pattern.type})")
    return strategy
