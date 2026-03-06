"""
Graph Semantic Annotator — Brainboard-style step.
Runs after Graph Composer / Product Resolution, before Layout.
Enriches each node with render-ready semantic fields: semantic_role, solution_layer,
flow_stage, placement_type, shape, priority. Layout engine consumes these.
"""
import logging
from typing import Any, Dict, List

from .constants import (
    CATEGORY_TO_LAYER,
    CATEGORY_TO_ZONE,
    CAPABILITY_ROLE_MAP,
    ROLE_PLACEMENT,
    FLOW_STAGE,
    CATEGORY_SHAPES,
    ROLE_PRIORITY,
)

logger = logging.getLogger(__name__)


def _semantic_role_from_node(node: Dict[str, Any]) -> str:
    """Resolve semantic_role from capability_ref or category."""
    category = (node.get("category") or "").lower()
    if category == "external" or (node.get("id") or "").lower() == "client":
        return "external"
    cap = (node.get("capability_ref") or node.get("id") or "").strip().lower()
    if not cap:
        return "application_service" if category == "compute" else "primary_data"
    return CAPABILITY_ROLE_MAP.get(cap) or CAPABILITY_ROLE_MAP.get(cap.replace("-", "_")) or "application_service"


def _solution_layer_from_category(category: str) -> str:
    return CATEGORY_TO_LAYER.get((category or "").lower(), "application")


def _network_zone_from_category(category: str) -> str:
    return CATEGORY_TO_ZONE.get((category or "").lower(), "compute")


def _placement_type_from_role(semantic_role: str) -> str:
    return ROLE_PLACEMENT.get(semantic_role, "traffic_path")


def _flow_stage_from_role(semantic_role: str) -> int:
    return FLOW_STAGE.get(semantic_role, 3)


def _shape_from_category(category: str) -> str:
    return CATEGORY_SHAPES.get((category or "").lower(), "rectangle")


def _priority_from_role(semantic_role: str) -> int:
    return ROLE_PRIORITY.get(semantic_role, 50)


def annotate_graph_semantics(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Annotate every node in graph with semantic fields for layout and rendering.
    Mutates graph["nodes"] in place and returns graph.
    """
    nodes: List[Dict[str, Any]] = graph.get("nodes") or []
    for node in nodes:
        if (node.get("type") or node.get("category")) == "group" or node.get("id") == "vpc_container":
            continue
        category = (node.get("category") or "").lower()
        if category == "container":
            continue

        semantic_role = _semantic_role_from_node(node)
        solution_layer = _solution_layer_from_category(category)
        network_zone = _network_zone_from_category(category)
        placement_type = _placement_type_from_role(semantic_role)
        flow_stage = _flow_stage_from_role(semantic_role)
        shape = _shape_from_category(category)
        priority = _priority_from_role(semantic_role)

        node["semantic_role"] = semantic_role
        node["solution_layer"] = solution_layer
        node["network_zone"] = network_zone
        node["flow_stage"] = flow_stage
        node["placement_type"] = placement_type
        node["shape"] = shape
        node["priority"] = priority

        if not node.get("zone"):
            node["zone"] = network_zone
        if node.get("layer") is None:
            node["layer"] = flow_stage

    logger.info(f"Annotated {len(nodes)} nodes with semantic roles and placement")
    return graph
