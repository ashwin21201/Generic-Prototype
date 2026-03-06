"""
Topology Expander — creates a more detailed "topology" view (more nodes/edges).

Goal: Make topology *meaningfully more detailed* than logical.

Current behavior:
- Expand compute tiers into instance nodes (based on min_instances) and fan-out edges.

Added behavior:
- For microservice compute tiers, render as **A, B, B** (3 microservices) in topology only,
  and fan-out edges from/to the original compute tier.
"""

import copy
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def expand_for_topology(graph: Dict[str, Any], *, max_instances_per_compute: int = 6) -> Dict[str, Any]:
    """
    Expand graph in-place for topology view.

    - For each compute node with config.min_instances > 1, replace it with N instance nodes.
    - Duplicate any edges that referenced the original compute node to each instance node.
    - Leaves other nodes unchanged.
    """
    nodes: List[Dict[str, Any]] = graph.get("nodes") or []
    edges: List[Dict[str, Any]] = graph.get("edges") or []
    if not nodes:
        return graph

    compute_nodes = [n for n in nodes if (n.get("category") or "").lower() == "compute"]
    if not compute_nodes:
        return graph

    # Special-case: microservices_compute tier should become A, B, B (topology only)
    microservice_compute_ids = [
        n.get("id")
        for n in compute_nodes
        if (
            ((n.get("capability_ref") or "").lower() == "microservices_compute")
            or (str(n.get("id") or "").lower().startswith("microservices_compute"))
        )
        # If compute was already expanded into named services (services_expander),
        # do NOT override it with A/B/B.
        and (not n.get("service_name"))
        and ("__svc_" not in str(n.get("id") or ""))
    ]
    microservice_compute_ids = [i for i in microservice_compute_ids if i]

    new_nodes: List[Dict[str, Any]] = []
    removed_ids = set()
    replacement_map: Dict[str, List[str]] = {}

    # Replace the entire microservice tier with A, B, B
    if microservice_compute_ids:
        template = next((n for n in nodes if n.get("id") == microservice_compute_ids[0]), None)
        if template:
            removed_ids.update(microservice_compute_ids)
            ms_ids = ["microservices_compute__A", "microservices_compute__B1", "microservices_compute__B2"]
            ms_labels = ["Microservice A", "Microservice B", "Microservice B"]

            ms_nodes: List[Dict[str, Any]] = []
            for mid, mlbl in zip(ms_ids, ms_labels):
                inst = copy.deepcopy(template)
                inst["id"] = mid
                data = inst.get("data") or {}
                if isinstance(data, dict):
                    data["label"] = mlbl
                    inst["data"] = data
                if isinstance(inst.get("config"), dict):
                    inst["config"] = dict(inst["config"])
                    inst["config"]["min_instances"] = None
                    inst["config"]["max_instances"] = None
                ms_nodes.append(inst)
                new_nodes.append(inst)

            for old_id in microservice_compute_ids:
                replacement_map[old_id] = ms_ids

    for n in nodes:
        # Already replaced with A/B/B above
        if n.get("id") in removed_ids:
            continue
        if (n.get("category") or "").lower() != "compute":
            new_nodes.append(n)
            continue

        cfg = n.get("config") if isinstance(n.get("config"), dict) else {}
        min_instances = 1
        try:
            mi = cfg.get("min_instances")
            if isinstance(mi, int) and mi > 0:
                min_instances = mi
        except Exception:
            pass

        # Cap and keep at least 1
        inst_count = max(1, min(int(min_instances), int(max_instances_per_compute)))
        if inst_count == 1:
            new_nodes.append(n)
            continue

        base_id = n.get("id")
        removed_ids.add(base_id)
        instance_ids: List[str] = []

        for i in range(inst_count):
            inst = copy.deepcopy(n)
            inst_id = f"{base_id}__inst_{i+1}"
            inst["id"] = inst_id

            # Label each instance; keep original label if present
            data = inst.get("data") or {}
            if isinstance(data, dict):
                lbl = data.get("label") or base_id
                data["label"] = f"{lbl} ({i+1})"
                inst["data"] = data

            # Instance nodes represent a single replica; strip autoscaling counts
            if isinstance(inst.get("config"), dict):
                inst["config"] = dict(inst["config"])
                inst["config"]["min_instances"] = None
                inst["config"]["max_instances"] = None

            instance_ids.append(inst_id)
            new_nodes.append(inst)

        replacement_map[base_id] = instance_ids

    # Rebuild edges: fan-out any edge touching a replaced compute node
    new_edges: List[Dict[str, Any]] = []
    for e in edges:
        src = e.get("from_node") or e.get("from") or e.get("source")
        tgt = e.get("to") or e.get("target")
        src_repl = replacement_map.get(src) if src in replacement_map else None
        tgt_repl = replacement_map.get(tgt) if tgt in replacement_map else None

        # Expand src
        if src_repl and not tgt_repl:
            for i, sid in enumerate(src_repl):
                ne = dict(e)
                ne["id"] = f"{e.get('id','e')}__src_{i+1}"
                ne["from_node"] = sid
                ne["to"] = tgt
                new_edges.append(ne)
            continue

        # Expand tgt
        if tgt_repl and not src_repl:
            for i, tid in enumerate(tgt_repl):
                ne = dict(e)
                ne["id"] = f"{e.get('id','e')}__tgt_{i+1}"
                ne["from_node"] = src
                ne["to"] = tid
                new_edges.append(ne)
            continue

        # Expand both (rare)
        if src_repl and tgt_repl:
            for i, sid in enumerate(src_repl):
                for j, tid in enumerate(tgt_repl):
                    ne = dict(e)
                    ne["id"] = f"{e.get('id','e')}__src_{i+1}__tgt_{j+1}"
                    ne["from_node"] = sid
                    ne["to"] = tid
                    new_edges.append(ne)
            continue

        # Unchanged edge
        new_edges.append(e)

    graph["nodes"] = new_nodes
    graph["edges"] = new_edges

    logger.info(
        "Topology expand: compute_nodes=%s replaced=%s nodes=%s edges=%s",
        len(compute_nodes),
        len(replacement_map),
        len(new_nodes),
        len(new_edges),
    )
    return graph

