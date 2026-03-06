"""
Layer-based layout engine for architecture graphs.

Requirement:
- Regardless of view, render the full solution layers:
  external → edge → application → integration → data → operations

Orientation:
- orientation="horizontal": layers are columns left→right (Logical view)
- orientation="vertical": layers are rows top→bottom (Topology view)
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

VPC_CONTAINER_ID = "vpc_container"
VPC_PADDING = 48
LAYER_PADDING = 24
LAYER_VERTICAL_GAP = 32
LAYER_HORIZONTAL_GAP = 32

NODE_WIDTH = 180
NODE_HEIGHT = 44
NODE_GAP_X = 24
NODE_GAP_Y = 20

EXTERNAL_CATEGORY = "external"
PLACEMENT_SIDE = "side"

# All layers must render, even if empty.
LAYER_ORDER = ["edge", "application", "integration", "data", "operations"]
LAYER_LABELS = {
    "edge": "Edge",
    "application": "Application",
    "integration": "Integration",
    "data": "Data",
    "operations": "Operations",
}


def _solution_layer_for_node(node: Dict[str, Any]) -> str:
    """Resolve solution layer from semantic annotation; fallback to category mapping."""
    sl = (node.get("solution_layer") or "").strip().lower()
    if sl:
        return sl
    cat = (node.get("category") or "").lower()
    if cat in ("security", "network"):
        return "edge"
    if cat == "compute":
        return "application"
    if cat in ("messaging", "cache"):
        return "integration"
    if cat in ("data", "storage", "data_processing"):
        return "data"
    if cat == "observability":
        return "operations"
    return "application"


def _order_key(node: Dict[str, Any]) -> Tuple[int, int, int, str]:
    """Sort by flow_stage, then priority, then main-before-side."""
    stage = node.get("flow_stage")
    if stage is None:
        stage = 100
    priority = int(node.get("priority") or 50)
    placement = (node.get("placement_type") or "").lower()
    side_last = 1 if placement == PLACEMENT_SIDE else 0
    return (int(stage), -priority, side_last, str(node.get("id") or ""))


def _place_nodes_vertical(nodes: List[Dict[str, Any]], start_x: float, start_y: float) -> Tuple[float, float]:
    """Place nodes in a vertical column. Returns (width, height) of bounding box."""
    for i, n in enumerate(nodes):
        n["position"] = {"x": start_x, "y": start_y + i * (NODE_HEIGHT + NODE_GAP_Y)}
    w = NODE_WIDTH + NODE_GAP_X
    h = len(nodes) * (NODE_HEIGHT + NODE_GAP_Y) - NODE_GAP_Y
    return (w, h)


def _place_nodes_horizontal(nodes: List[Dict[str, Any]], start_x: float, start_y: float) -> Tuple[float, float]:
    """Place nodes in a horizontal row (e.g. Primary ↔ Replica). Returns (width, height)."""
    for i, n in enumerate(nodes):
        n["position"] = {"x": start_x + i * (NODE_WIDTH + NODE_GAP_X), "y": start_y}
    w = len(nodes) * (NODE_WIDTH + NODE_GAP_X) - NODE_GAP_X
    h = NODE_HEIGHT
    return (w, h)


def _bbox_nodes(nodes: List[Dict[str, Any]]) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, content_width, content_height) for placed nodes."""
    if not nodes:
        return (0.0, 0.0, 0.0, 0.0)
    min_x = min(n.get("position", {}).get("x", 0) for n in nodes)
    min_y = min(n.get("position", {}).get("y", 0) for n in nodes)
    max_x = max(n.get("position", {}).get("x", 0) + NODE_WIDTH for n in nodes)
    max_y = max(n.get("position", {}).get("y", 0) + NODE_HEIGHT for n in nodes)
    return (min_x, min_y, max_x - min_x, max_y - min_y)


def _center_nodes_in_container(
    nodes: List[Dict[str, Any]],
    sub_w: float,
    sub_h: float,
    min_x: float,
    min_y: float,
    content_w: float,
    content_h: float,
) -> None:
    """Shift node positions so the content bbox is centered inside the container."""
    offset_x = (sub_w - content_w) / 2 - min_x
    offset_y = (sub_h - content_h) / 2 - min_y
    for n in nodes:
        pos = n.get("position") or {"x": 0, "y": 0}
        n["position"] = {
            "x": pos.get("x", 0) + offset_x,
            "y": pos.get("y", 0) + offset_y,
        }


def _add_vpc_and_layers(nodes: List[Dict[str, Any]], horizontal: bool) -> None:
    internal = [
        n for n in nodes
        if (n.get("type") != "group")
        and (n.get("category") or "").lower() != EXTERNAL_CATEGORY
        and n.get("id") != "client"
    ]
    external = [
        n for n in nodes
        if n.get("id") == "client" or (n.get("category") or "").lower() == EXTERNAL_CATEGORY
    ]

    if not internal:
        for n in nodes:
            n["position"] = n.get("position") or {"x": 0.0, "y": 0.0}
        return

    # Group by solution layer (ensure all layers exist)
    by_layer: Dict[str, List[Dict[str, Any]]] = {k: [] for k in LAYER_ORDER}
    for n in internal:
        sl = _solution_layer_for_node(n)
        if sl not in by_layer:
            by_layer[sl] = []
        by_layer[sl].append(n)

    layer_nodes_list: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    x_cursor = 0.0
    y_cursor = 0.0
    max_layer_w = 0.0
    max_layer_h = 0.0

    for sl in LAYER_ORDER:
        ln = by_layer.get(sl) or []
        ln.sort(key=_order_key)
        layer_id = f"layer_{sl}"

        main = [n for n in ln if (n.get("placement_type") or "").lower() != PLACEMENT_SIDE]
        side = [n for n in ln if (n.get("placement_type") or "").lower() == PLACEMENT_SIDE]

        if main:
            _place_nodes_vertical(main, 0.0, 0.0)
        if side:
            sx = NODE_WIDTH + NODE_GAP_X * 2
            _place_nodes_vertical(side, sx, 0.0)

        all_nodes = main + side
        if not all_nodes:
            layer_w = NODE_WIDTH + 2 * LAYER_PADDING
            layer_h = NODE_HEIGHT + 2 * LAYER_PADDING
        else:
            min_x, min_y, content_w, content_h = _bbox_nodes(all_nodes)
            layer_w = content_w + 2 * LAYER_PADDING
            layer_h = content_h + 2 * LAYER_PADDING
            _center_nodes_in_container(all_nodes, layer_w, layer_h, min_x, min_y, content_w, content_h)

        for n in all_nodes:
            n["parent_node"] = layer_id
            n["extent"] = "parent"

        if horizontal:
            pos = {"x": float(VPC_PADDING + x_cursor), "y": float(VPC_PADDING)}
            x_cursor += layer_w + LAYER_HORIZONTAL_GAP
            max_layer_h = max(max_layer_h, layer_h)
        else:
            pos = {"x": float(VPC_PADDING), "y": float(VPC_PADDING + y_cursor)}
            y_cursor += layer_h + LAYER_VERTICAL_GAP
            max_layer_w = max(max_layer_w, layer_w)

        layer_nodes_list.append(({
            "id": layer_id,
            "type": "group",
            "category": "container",
            "data": {"label": LAYER_LABELS.get(sl, sl)},
            "position": pos,
            "style": {"width": layer_w, "height": layer_h},
            "parent_node": VPC_CONTAINER_ID,
            "extent": "parent",
            "solution_layer": sl,
        }, ln))

    # VPC size
    if horizontal:
        total_w = max(0.0, x_cursor - LAYER_HORIZONTAL_GAP)
        vpc_w = total_w + 2 * VPC_PADDING
        vpc_h = max(max_layer_h, 1.0) + 2 * VPC_PADDING
    else:
        total_h = max(0.0, y_cursor - LAYER_VERTICAL_GAP)
        vpc_w = max(max_layer_w, 1.0) + 2 * VPC_PADDING
        vpc_h = total_h + 2 * VPC_PADDING

    # External nodes outside VPC
    if external:
        if horizontal:
            for i, ext in enumerate(external):
                ext["position"] = {"x": 0.0, "y": (vpc_h / 2) - (NODE_HEIGHT / 2) + i * (NODE_HEIGHT + NODE_GAP_Y)}
                ext["layer"] = -1
                ext["zone"] = "external"
        else:
            for i, ext in enumerate(external):
                ext["position"] = {"x": (vpc_w / 2) - (NODE_WIDTH / 2), "y": float(i * (NODE_HEIGHT + NODE_GAP_Y))}
                ext["layer"] = -1
                ext["zone"] = "external"

    # VPC position
    if horizontal:
        vpc_x = NODE_WIDTH + 24
        vpc_y = 0.0
    else:
        vpc_x = 0.0
        vpc_y = (len(external) * (NODE_HEIGHT + NODE_GAP_Y) + 24) if external else 0.0

    vpc_node: Dict[str, Any] = {
        "id": VPC_CONTAINER_ID,
        "type": "group",
        "category": "container",
        "data": {"label": "VPC", "description": "Virtual Private Cloud"},
        "position": {"x": vpc_x, "y": vpc_y},
        "style": {"width": vpc_w, "height": vpc_h},
    }

    nodes.clear()
    nodes.append(vpc_node)
    for layer_node, _ in layer_nodes_list:
        nodes.append(layer_node)
    nodes.extend(internal)
    nodes.extend(external)

    logger.info(f"Layer layout: VPC + {len(layer_nodes_list)} layers; internal={len(internal)} external={len(external)}")


def apply_layout(
    graph: Dict[str, Any],
    layout_strategy: str = "layered_vertical",
    orientation: str = "horizontal",  # horizontal | vertical
) -> Dict[str, Any]:
    """
    Apply layout: layer-based containers with semantic placement.
    Mutates graph["nodes"] in place (adds VPC + layer containers + positions + parent_node/extent).
    """
    from .graph_normalizer import normalize_graph

    normalize_graph(graph)
    nodes = graph.get("nodes") or []
    if not nodes:
        return graph

    horizontal = (orientation or "horizontal").lower() != "vertical"
    _add_vpc_and_layers(nodes, horizontal=horizontal)

    logger.info(f"Applied layout ({layout_strategy}, {orientation}) to {len(nodes)} nodes")
    return graph
