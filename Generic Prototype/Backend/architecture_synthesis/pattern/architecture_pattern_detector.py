"""
Architecture Pattern Detection — Brainboard-style step.
Runs after Block Selection, before Compatibility Resolution.
Detects architecture pattern from selected block IDs and returns layout strategy.
"""
import logging
from dataclasses import dataclass
from typing import List

from ..blocks.block_registry import BlockRegistryStore

logger = logging.getLogger(__name__)


@dataclass
class ArchitecturePattern:
    """Detected architecture pattern and recommended layout strategy."""
    type: str  # web_service | event_driven | data_pipeline | serverless | mesh
    layout_strategy: str  # layered_vertical | radial | horizontal | force


def detect_architecture_pattern(
    selected_block_ids: List[str],
    block_registry: BlockRegistryStore,
) -> ArchitecturePattern:
    """
    Detect architecture pattern from selected blocks.
    Different patterns get different layout strategies (vertical layers, hub/spoke, etc.).
    """
    categories = set()
    block_ids_lower = {bid.lower() for bid in selected_block_ids}

    for block_id in selected_block_ids:
        block = block_registry.get_block(block_id)
        if block:
            categories.add((block.category or "").lower())

    # Event-driven: messaging is central
    if "messaging" in categories and any("event_streaming" in bid for bid in block_ids_lower):
        logger.info("Pattern detected: event_driven (messaging present)")
        return ArchitecturePattern(type="event_driven", layout_strategy="radial")

    # Data pipeline: batch + storage, no strong compute/gateway
    batch_like = any(
        b in block_ids_lower for b in ("batch_processing", "etl_pipeline", "stream_processing")
    )
    storage_like = "storage" in categories or "data" in categories
    if batch_like and storage_like and "network" not in categories:
        logger.info("Pattern detected: data_pipeline")
        return ArchitecturePattern(type="data_pipeline", layout_strategy="horizontal")

    # Serverless: serverless compute present
    if any("serverless" in bid for bid in block_ids_lower):
        logger.info("Pattern detected: serverless")
        return ArchitecturePattern(type="serverless", layout_strategy="radial")

    # Mesh: many compute/services + service_mesh
    if "service_mesh" in block_ids_lower and "compute" in categories:
        logger.info("Pattern detected: mesh")
        return ArchitecturePattern(type="mesh", layout_strategy="force")

    # Default: web service (compute + gateway + db or similar)
    if "compute" in categories and ("network" in categories or "security" in categories):
        logger.info("Pattern detected: web_service (default layered)")
        return ArchitecturePattern(type="web_service", layout_strategy="layered_vertical")

    # Fallback
    logger.info("Pattern detected: web_service (fallback)")
    return ArchitecturePattern(type="web_service", layout_strategy="layered_vertical")
