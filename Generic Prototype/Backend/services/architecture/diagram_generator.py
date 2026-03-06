"""Build diagram-ready JSON from topology DB: views (logical/topology), containers/nodes/edges, legend, request_flows.

Richer JSON contract (layout-friendly):
- Each view includes explicit `containers`, `nodes`, `edges` for deterministic layout engines (ELK / backend layout).
- Logical view collapses replicas via primary-node mapping and edge dedupe (prevents hairball).
- Topology view can expand compute into microservices/instances but still dedupes edges.

Backward compatibility:
- Still includes `views.{view}.graph` with backend-computed positions (existing ReactFlow mapping).
"""

import copy
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

from architecture_synthesis.semantics import annotate_graph_semantics
from architecture_synthesis.graph.topology_expander import expand_for_topology
from architecture_synthesis.graph.layout_engine import apply_layout
from architecture_synthesis.graph.services_expander import expand_compute_to_services


def generate_diagram(
    topology_id: str,
    nodes: List[Any],
    edges: List[Any],
    view: str = "logical",
    mode: str = "default",
    intent_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build diagram JSON from topology nodes/edges (from DB).
    nodes/edges are ORM objects with id, block_id, category, data_label, spec, etc.
    """
    graph = _topology_to_graph(nodes, edges)
    if not graph.get("nodes"):
        return _empty_diagram(topology_id, view, mode)

    # 1) Logical view: collapse replicas, dedupe edges
    logical_graph = copy.deepcopy(graph)
    annotate_graph_semantics(logical_graph)
    logical_graph = _collapse_to_primary(logical_graph)
    logical_graph = _dedupe_edges(logical_graph, by_capability=True)
    # Provide positions as a fallback for non-ELK renderers
    apply_layout(logical_graph, layout_strategy="layered_vertical", orientation="horizontal")
    logical_graph["layout_direction"] = "RIGHT"

    # 2) Topology view: expanded + deduped
    topology_graph = copy.deepcopy(graph)
    annotate_graph_semantics(topology_graph)
    # Expand compute tier into named services, then expand instances for deeper topology
    expand_compute_to_services(topology_graph, intent=intent_snapshot or {}, max_services=3, create_replicas=True)
    expand_for_topology(topology_graph, max_instances_per_compute=6)
    # Keep instance edges; only remove exact duplicates
    topology_graph = _dedupe_edges(topology_graph, by_capability=False)
    apply_layout(topology_graph, layout_strategy="layered_vertical", orientation="vertical")
    topology_graph["layout_direction"] = "DOWN"

    views = {
        "logical": {
            "graph": logical_graph,
            **_graph_to_view_struct(logical_graph),
        },
        "topology": {
            "graph": topology_graph,
            **_graph_to_view_struct(topology_graph),
        },
    }
    default_view = view if view in views else "logical"
    legend = _generate_legend(logical_graph)
    request_flows = _generate_request_flows(logical_graph)
    layout_config = _generate_layout_config()

    return {
        "topology_id": topology_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "views": views,
        "default_view": default_view,
        "rendering_modes": {"default": {}, "compliance": {}, "cost": {}, "diff": {}},
        "default_mode": mode or "default",
        "legend": legend,
        "request_flows": request_flows,
        "layout": layout_config,
    }


def _topology_to_graph(nodes: List[Any], edges: List[Any]) -> Dict[str, Any]:
    """Convert DB topology nodes/edges to graph dict (nodes + edges lists)."""
    node_list = []
    for n in nodes:
        cfg = n.spec or {}
        ha_role = _infer_ha_role(cfg)
        semantic_id = None
        try:
            if isinstance(cfg, dict):
                semantic_id = cfg.get("_semantic_id")
        except Exception:
            semantic_id = None
        node_list.append({
            "id": n.id,
            "type": n.node_type or "default",
            "category": n.category or "compute",
            "region": n.region,
            "capability_ref": n.capability_ref or n.block_id,
            "block_id": getattr(n, "block_id", None) or (n.capability_ref or ""),
            "ha_role": ha_role,
            "semantic_id": semantic_id,
            "data": {
                "label": _resolve_display_label(n.capability_ref or n.block_id, n.data_label or n.id),
                "description": "",
                "product_name": _resolve_display_label(n.capability_ref or n.block_id, n.data_label or n.id),
            },
            "config": cfg,
        })
    edge_list = []
    for e in edges:
        edge_list.append({
            "id": e.id,
            "from_node": e.source_node_id,
            "to": e.target_node_id,
            "protocol": e.protocol or "http",
            "type": e.edge_type or "traffic",
        })
    return {"nodes": node_list, "edges": edge_list}


def _infer_ha_role(config: Dict[str, Any]) -> str:
    """Infer HA role from known config keys."""
    rr = (config or {}).get("replication_role")
    if isinstance(rr, str) and rr.lower() in ("primary", "leader", "writer"):
        return "PRIMARY"
    if isinstance(rr, str) and rr.lower() in ("replica", "secondary", "follower", "reader"):
        return "REPLICA"
    return "PRIMARY"


def _load_product_labels() -> Dict[str, Any]:
    """Load optional product display labels mapping."""
    try:
        import json
        from pathlib import Path
        here = Path(__file__).resolve()
        backend_dir = here.parents[2]  # Backend/
        p = backend_dir / "blocks" / "product_display_names.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


_PRODUCT_LABELS = _load_product_labels()


def _resolve_display_label(capability_ref: Optional[str], fallback: str) -> str:
    cap = (capability_ref or "").strip()
    if not cap:
        return fallback
    try:
        labels = (_PRODUCT_LABELS or {}).get("block_labels") or {}
        return labels.get(cap) or labels.get(cap.replace("-", "_")) or fallback
    except Exception:
        return fallback


def _collapse_to_primary(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collapse replicas by mapping each capability_ref to a single primary node id.
    Produces a smaller, cleaner graph for logical view.
    """
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    primary_by_cap: Dict[str, str] = {}
    nodes_out: List[Dict[str, Any]] = []

    # Pick a primary per capability_ref (or per id if none)
    for n in nodes:
        cap = (n.get("capability_ref") or n.get("block_id") or n.get("id") or "").strip()
        role = (n.get("ha_role") or "PRIMARY").upper()
        if cap not in primary_by_cap:
            primary_by_cap[cap] = n.get("id")
        if role == "PRIMARY":
            primary_by_cap[cap] = n.get("id")

    # Keep only chosen primary nodes
    keep_ids = set(primary_by_cap.values())
    for n in nodes:
        if n.get("id") in keep_ids:
            nodes_out.append(n)

    # Remap edges to primary endpoints
    edges_out: List[Dict[str, Any]] = []
    for e in edges:
        src = e.get("from_node")
        tgt = e.get("to")
        src_cap = _node_capability(nodes, src)
        tgt_cap = _node_capability(nodes, tgt)
        if not src_cap or not tgt_cap:
            continue
        src2 = primary_by_cap.get(src_cap) or src
        tgt2 = primary_by_cap.get(tgt_cap) or tgt
        if not src2 or not tgt2 or src2 == tgt2:
            continue
        ne = dict(e)
        ne["from_node"] = src2
        ne["to"] = tgt2
        edges_out.append(ne)

    graph["nodes"] = nodes_out
    graph["edges"] = edges_out
    return graph


def _node_capability(nodes: List[Dict[str, Any]], node_id: str) -> Optional[str]:
    for n in nodes:
        if n.get("id") == node_id:
            return (n.get("capability_ref") or n.get("block_id") or n.get("id") or "").strip()
    return None


def _dedupe_edges(graph: Dict[str, Any], *, by_capability: bool = True) -> Dict[str, Any]:
    """
    Dedupe edges.
    - by_capability=True: collapse edges across replicas/instances (clean logical view).
    - by_capability=False: only remove exact duplicates (keeps topology connectivity).
    """
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    seen = set()
    out = []
    for e in edges:
        src = e.get("from_node")
        tgt = e.get("to")
        et = (e.get("type") or "traffic").lower()
        if by_capability:
            sc = _node_capability(nodes, src) or src
            tc = _node_capability(nodes, tgt) or tgt
            key = (sc, tc, et)
        else:
            key = (src, tgt, et)
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    graph["edges"] = out
    return graph


def _graph_to_view_struct(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert `graph` into explicit containers + nodes + edges for deterministic layout.
    Containers: VPC + solution layers.
    Nodes: non-container nodes with container_id.
    """
    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []

    # Identify container/group nodes (created by apply_layout)
    containers = []
    node_items = []
    for n in nodes:
        if (n.get("type") == "group") or (n.get("category") == "container"):
            containers.append({
                "id": n.get("id"),
                "label": (n.get("data") or {}).get("label") or n.get("id"),
                "parent_id": n.get("parent_node"),
                "solution_layer": n.get("solution_layer"),
                "style": n.get("style") or {},
            })
        else:
            node_items.append({
                "id": n.get("id"),
                "block_id": n.get("capability_ref") or n.get("block_id"),
                "product_name": ((n.get("data") or {}).get("product_name")) or ((n.get("data") or {}).get("label")),
                "category": n.get("category"),
                "solution_layer": n.get("solution_layer"),
                "network_zone": n.get("network_zone"),
                "semantic_role": n.get("semantic_role"),
                "placement_type": n.get("placement_type"),
                "shape": n.get("shape"),
                "ha_role": n.get("ha_role"),
                "region": n.get("region"),
                "container_id": n.get("parent_node"),
                "style": {"width": 180, "height": 44},
            })

    edge_items = []
    for e in edges:
        edge_items.append({
            "id": e.get("id"),
            "source": e.get("from_node"),
            "target": e.get("to"),
            "type": e.get("type") or "traffic",
            "protocol": e.get("protocol"),
        })

    return {
        "containers": containers,
        "nodes": node_items,
        "edges": edge_items,
        "layout_hints": {
            "engine": "elk",
            "algorithm": "layered",
            "direction": "RIGHT" if (graph.get("layout_direction") or "LR") in ("LR", "RIGHT") else "DOWN",
            "spacing": 40,
        },
    }


def _generate_legend(graph: Dict[str, Any]) -> List[Dict[str, str]]:
    """Derive legend from node categories."""
    cats = set()
    for n in graph.get("nodes") or []:
        c = n.get("category") or "default"
        if c not in ("group", "container"):
            cats.add(c)
    return [{"id": c, "label": c.replace("_", " ").title()} for c in sorted(cats)]


def _generate_request_flows(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive request flows from edges."""
    flows = []
    for e in graph.get("edges") or []:
        flows.append({
            "id": e.get("id", ""),
            "from": e.get("from_node"),
            "to": e.get("to"),
            "protocol": e.get("protocol"),
        })
    return flows[:20]


def _generate_layout_config() -> Dict[str, Any]:
    return {"direction": "LR", "aspect_ratio": 1.5, "max_columns": 8}


def _empty_diagram(topology_id: str, view: str, mode: str) -> Dict[str, Any]:
    return {
        "topology_id": topology_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "views": {
            "logical": {"graph": {"nodes": [], "edges": []}, "containers": [], "nodes": [], "edges": [], "layout_hints": {}},
            "topology": {"graph": {"nodes": [], "edges": []}, "containers": [], "nodes": [], "edges": [], "layout_hints": {}},
        },
        "default_view": view or "logical",
        "rendering_modes": {"default": {}},
        "default_mode": mode or "default",
        "legend": [],
        "request_flows": [],
        "layout": _generate_layout_config(),
    }
