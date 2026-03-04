"""
Layout engine for architecture graphs.

Semantic layout rules so the diagram communicates:
  - Traffic path: Client → WAF → API Gateway → Compute → Data
  - Support services (KMS, etc.) separate from ingress, not inline
  - Data tier: Primary ↔ Replica shown as a pair; observability as side-channel

  CLIENT
     │
  ┌── EDGE SUBNET ──────────────┐
  │  WAF → API Gateway  (traffic)│
  │  Key Management    (support) │
  └──────────────────────────────┘
     │
  ┌── COMPUTE SUBNET ────────────┐
  │  App Servers 1, App Servers 2│
  └──────────────────────────────┘
     │
  ┌── DATA & OPS ────────────────────────┐
  │  Primary DB ↔ Replica DB  │ Logging  │  (data pair + observability side)
  └─────────────────────────────────────┘
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

VPC_CONTAINER_ID = "vpc_container"
VPC_PADDING = 48
SUBNET_PADDING = 24
SUBNET_VERTICAL_GAP = 32

NODE_WIDTH = 180
NODE_HEIGHT = 44
NODE_GAP_X = 24
NODE_GAP_Y = 20

ZONE_ORDER = ["edge", "compute", "data_ops"]
ZONE_LABELS = {"edge": "Edge", "compute": "Compute", "data_ops": "Data & Ops"}

ZONE_BY_CATEGORY = {
    "security": "edge",
    "network": "edge",
    "compute": "compute",
    "messaging": "compute",
    "cache": "compute",
    "data": "data_ops",
    "storage": "data_ops",
    "observability": "data_ops",
    "data_processing": "data_ops",
}
DEFAULT_ZONE = "compute"

# Semantic roles: traffic_path (ingress flow), support (KMS, etc.), data, observability
ROLE_TRAFFIC_PATH = "traffic_path"
ROLE_SUPPORT = "support"
ROLE_DATA = "data"
ROLE_OBSERVABILITY = "observability"

# In edge zone: block_ids that are ingress (order = flow). Others = support.
EDGE_TRAFFIC_ORDER = ["waf_layer", "api_gateway", "api_gateway_"]
EXTERNAL_CATEGORY = "external"


def _zone_for_node(node: Dict[str, Any]) -> str:
    """Assign node to a zone by category."""
    cat = (node.get("category") or "").lower()
    return ZONE_BY_CATEGORY.get(cat, DEFAULT_ZONE)


def _layer_index_for_zone(zone: str) -> int:
    try:
        return ZONE_ORDER.index(zone)
    except ValueError:
        return 1


def _semantic_role(node: Dict[str, Any], zone: str) -> str:
    """Traffic path vs support (edge); data vs observability (data_ops)."""
    cat = (node.get("category") or "").lower()
    bid = (node.get("capability_ref") or node.get("id") or "").lower()
    if zone == "edge":
        if "waf" in bid or "api" in bid or "gateway" in bid:
            return ROLE_TRAFFIC_PATH
        return ROLE_SUPPORT
    if zone == "data_ops":
        if cat == "observability":
            return ROLE_OBSERVABILITY
        return ROLE_DATA
    return "default"


def _edge_traffic_order_key(node: Dict[str, Any]) -> int:
    """Order for traffic-path nodes: WAF first, then API Gateway."""
    bid = (node.get("capability_ref") or node.get("id") or "").lower()
    if "waf" in bid:
        return 0
    if "api" in bid or "gateway" in bid:
        return 1
    return 2


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


def _add_vpc_and_subnets(nodes: List[Dict[str, Any]]) -> None:
    """
    Semantic layout: traffic path vs support in Edge; data pair + observability side in Data & Ops.
    """
    internal = [n for n in nodes if n.get("id") != "client" and (n.get("category") or "").lower() != EXTERNAL_CATEGORY]
    external = [n for n in nodes if n.get("id") == "client" or (n.get("category") or "").lower() == EXTERNAL_CATEGORY]

    if not internal:
        for n in nodes:
            n["position"] = n.get("position") or {"x": 0.0, "y": 0.0}
        return

    by_zone: Dict[str, List[Dict[str, Any]]] = {}
    for n in internal:
        z = _zone_for_node(n)
        n["zone"] = z
        n["layer"] = _layer_index_for_zone(z)
        n["role"] = _semantic_role(n, z)
        if z not in by_zone:
            by_zone[z] = []
        by_zone[z].append(n)

    zones = [z for z in ZONE_ORDER if z in by_zone]
    if not zones:
        zones = list(by_zone.keys())

    subnet_nodes_list: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    y_cursor = 0.0

    for z in zones:
        zone_nodes = by_zone[z]
        sub_id = f"subnet_{z}"

        if z == "edge":
            traffic = [n for n in zone_nodes if n.get("role") == ROLE_TRAFFIC_PATH]
            support = [n for n in zone_nodes if n.get("role") == ROLE_SUPPORT]
            traffic.sort(key=_edge_traffic_order_key)
            support.sort(key=lambda n: (n.get("category") or "", n.get("id") or ""))
            # Row 0: WAF → API Gateway (horizontal). Row 1: support (horizontal or single).
            sub_x, sub_y = SUBNET_PADDING, SUBNET_PADDING
            max_w, total_h = 0.0, 0.0
            if traffic:
                tw, th = _place_nodes_horizontal(traffic, sub_x, sub_y)
                total_h += th + (NODE_GAP_Y if support else 0)
                max_w = max(max_w, tw)
            if support:
                sy = sub_y + (len(traffic) * (NODE_HEIGHT + NODE_GAP_Y) if traffic else 0) + (NODE_GAP_Y if traffic else 0)
                sw, sh = _place_nodes_horizontal(support, sub_x, sy)
                total_h = (sy - sub_y) + sh
                max_w = max(max_w, sw)
            sub_w = max(max_w + 2 * SUBNET_PADDING, NODE_WIDTH + 2 * SUBNET_PADDING)
            sub_h = total_h + 2 * SUBNET_PADDING

        elif z == "data_ops":
            data_nodes = [n for n in zone_nodes if n.get("role") == ROLE_DATA]
            obs_nodes = [n for n in zone_nodes if n.get("role") == ROLE_OBSERVABILITY]

            def _repl_role(n: Dict[str, Any]) -> str:
                c = n.get("config")
                if c is None:
                    return ""
                return c.get("replication_role", "") if isinstance(c, dict) else getattr(c, "replication_role", "") or ""

            primary = [n for n in data_nodes if _repl_role(n) == "primary"]
            replica = [n for n in data_nodes if _repl_role(n) == "replica"]
            other_data = [n for n in data_nodes if n not in primary and n not in replica]
            pair = primary + replica
            pair.sort(key=lambda n: (0 if _repl_role(n) == "primary" else 1, n.get("id") or ""))
            sub_x, sub_y = SUBNET_PADDING, SUBNET_PADDING
            col_left_w, col_left_h = 0.0, 0.0
            if pair:
                pw, ph = _place_nodes_horizontal(pair, sub_x, sub_y)
                col_left_w = pw
                col_left_h = ph + (NODE_GAP_Y if other_data else 0)
            for i, n in enumerate(other_data):
                n["position"] = {"x": sub_x, "y": sub_y + col_left_h + i * (NODE_HEIGHT + NODE_GAP_Y)}
                col_left_h += NODE_HEIGHT + NODE_GAP_Y
            if other_data:
                col_left_w = max(col_left_w, NODE_WIDTH)
            data_height = col_left_h
            obs_x = sub_x + col_left_w + NODE_GAP_X * 2
            obs_y = sub_y
            for i, n in enumerate(obs_nodes):
                n["parent_node"] = sub_id
                n["extent"] = "parent"
                n["position"] = {"x": obs_x, "y": obs_y + i * (NODE_HEIGHT + NODE_GAP_Y)}
            obs_height = len(obs_nodes) * (NODE_HEIGHT + NODE_GAP_Y) - NODE_GAP_Y if obs_nodes else 0
            sub_w = col_left_w + (NODE_WIDTH + NODE_GAP_X) * (1 if obs_nodes else 0) + NODE_GAP_X * 2 + 2 * SUBNET_PADDING
            sub_h = max(data_height, obs_height) + 2 * SUBNET_PADDING
            for n in data_nodes:
                n["parent_node"] = sub_id
                n["extent"] = "parent"
            subnet_nodes_list.append(({
                "id": sub_id,
                "type": "group",
                "category": "container",
                "data": {"label": ZONE_LABELS.get(z, z)},
                "position": {"x": float(VPC_PADDING), "y": VPC_PADDING + y_cursor},
                "style": {"width": sub_w, "height": sub_h},
                "parent_node": VPC_CONTAINER_ID,
                "extent": "parent",
                "layer": _layer_index_for_zone(z),
                "zone": z,
            }, zone_nodes))
            y_cursor += sub_h + SUBNET_VERTICAL_GAP
            continue

        else:
            # Compute (and any other zone): single vertical column
            zone_nodes.sort(key=lambda n: (n.get("category") or "", n.get("id") or ""))
            sub_w = NODE_WIDTH + 2 * SUBNET_PADDING
            sub_h = len(zone_nodes) * (NODE_HEIGHT + NODE_GAP_Y) - NODE_GAP_Y + 2 * SUBNET_PADDING
            for i, n in enumerate(zone_nodes):
                n["parent_node"] = sub_id
                n["extent"] = "parent"
                n["position"] = {"x": SUBNET_PADDING, "y": SUBNET_PADDING + i * (NODE_HEIGHT + NODE_GAP_Y)}
            subnet_nodes_list.append(({
                "id": sub_id,
                "type": "group",
                "category": "container",
                "data": {"label": ZONE_LABELS.get(z, z)},
                "position": {"x": float(VPC_PADDING), "y": VPC_PADDING + y_cursor},
                "style": {"width": sub_w, "height": sub_h},
                "parent_node": VPC_CONTAINER_ID,
                "extent": "parent",
                "layer": _layer_index_for_zone(z),
                "zone": z,
            }, zone_nodes))
            y_cursor += sub_h + SUBNET_VERTICAL_GAP
            continue

        # Edge: set parent and extent
        for n in zone_nodes:
            n["parent_node"] = sub_id
            n["extent"] = "parent"
        subnet_nodes_list.append(({
            "id": sub_id,
            "type": "group",
            "category": "container",
            "data": {"label": ZONE_LABELS.get(z, z)},
            "position": {"x": float(VPC_PADDING), "y": VPC_PADDING + y_cursor},
            "style": {"width": sub_w, "height": sub_h},
            "parent_node": VPC_CONTAINER_ID,
            "extent": "parent",
            "layer": _layer_index_for_zone(z),
            "zone": z,
        }, zone_nodes))
        y_cursor += sub_h + SUBNET_VERTICAL_GAP

    vpc_w = NODE_WIDTH * 2 + VPC_PADDING * 2 + SUBNET_PADDING * 4
    vpc_h = y_cursor - SUBNET_VERTICAL_GAP + 2 * VPC_PADDING

    client_y_offset = 0.0
    if external:
        for ext in external:
            ext["position"] = {"x": (vpc_w / 2) - (NODE_WIDTH / 2), "y": 0.0}
            ext["layer"] = -1
            ext["zone"] = "external"
        client_y_offset = NODE_HEIGHT + 24

    vpc_node: Dict[str, Any] = {
        "id": VPC_CONTAINER_ID,
        "type": "group",
        "category": "container",
        "data": {"label": "VPC", "description": "Virtual Private Cloud"},
        "position": {"x": 0.0, "y": client_y_offset},
        "style": {"width": vpc_w, "height": vpc_h},
    }

    nodes.clear()
    nodes.append(vpc_node)
    for sub_node, _ in subnet_nodes_list:
        nodes.append(sub_node)
    nodes.extend(internal)
    nodes.extend(external)

    logger.info(f"Semantic layout: VPC + {len(subnet_nodes_list)} subnets (traffic/support/data+observability); {len(internal)} nodes")


def apply_layout(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply layer/zone layout: subnets stacked vertically (Edge → Compute → Data & Ops).
    Positions are computed from (layer, zone); no arbitrary coordinates.
    Mutates graph["nodes"] in place (adds VPC, subnets, and sets position/parent_node/layer/zone).
    """
    nodes = graph.get("nodes") or []
    if not nodes:
        return graph

    _add_vpc_and_subnets(nodes)
    logger.info(f"Applied layer/zone layout to {len(nodes)} nodes")
    return graph
