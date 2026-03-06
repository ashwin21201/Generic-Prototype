"""
Services Expander — turns a single compute tier into multiple named services for topology.

Motivation (docs you shared):
- intent.services drives "distributed vs monolithic" and should render as multiple app services
- avoid edge hairball by keeping edges anchored on PRIMARY nodes only
"""

import copy
from typing import Any, Dict, List, Optional


def _get_services_from_intent(intent: Dict[str, Any]) -> List[str]:
    fr = (intent or {}).get("functional_requirements") or {}
    services = fr.get("services")
    if isinstance(services, list):
        names = [str(s).strip() for s in services if str(s).strip()]
        return names
    # Accept comma-separated string
    if isinstance(services, str) and services.strip():
        return [s.strip() for s in services.split(",") if s.strip()]
    return []


def _fallback_service_names() -> List[str]:
    return ["Order Service", "Payment Service", "Inventory Service"]


def _get_storage_types_count(intent: Dict[str, Any]) -> int:
    dr = (intent or {}).get("data_requirements") or {}
    st = dr.get("storage_types")
    if isinstance(st, list):
        return len([x for x in st if str(x).strip()])
    if isinstance(st, str) and st.strip():
        return len([x for x in st.split(",") if x.strip()])
    return 0


def _get_architecture_pattern_text(intent: Dict[str, Any]) -> str:
    fr = (intent or {}).get("functional_requirements") or {}
    ap = fr.get("architecture_pattern") or intent.get("architecture_pattern") or ""
    return str(ap or "").lower()


def _is_distributed(intent: Dict[str, Any]) -> bool:
    fr = (intent or {}).get("functional_requirements") or {}
    app_type = str(fr.get("application_type") or "").lower()
    services = _get_services_from_intent(intent)
    storage_types_count = _get_storage_types_count(intent)
    ap = _get_architecture_pattern_text(intent)

    # Strong signals
    if len(services) >= 2:
        return True
    if storage_types_count >= 2:
        return True
    if any(k in ap for k in ["microservice", "event-driven", "event", "kafka", "stream", "distributed"]):
        return True
    if any(k in app_type for k in ["ecommerce", "e-commerce", "bank", "banking", "fintech", "payment", "saas", "platform"]):
        return True

    return False


def expand_compute_to_services(
    graph: Dict[str, Any],
    *,
    intent: Optional[Dict[str, Any]] = None,
    max_services: int = 3,
    create_replicas: bool = True,
) -> Dict[str, Any]:
    """
    Replace compute nodes with N service nodes, using intent.functional_requirements.services.
    - Each service gets a PRIMARY node (always)
    - If create_replicas and original compute config.min_instances>1, also add a REPLICA node per service
      and connect PRIMARY -> REPLICA with edge_type="replica"
    - All original edges touching compute are rewired to PRIMARY nodes only.
    """
    nodes: List[Dict[str, Any]] = graph.get("nodes") or []
    edges: List[Dict[str, Any]] = graph.get("edges") or []
    if not nodes:
        return graph

    # Idempotency: if services already expanded, do nothing
    for n in nodes:
        nid = str(n.get("id") or "")
        if "__svc_" in nid or n.get("service_name"):
            return graph

    intent = intent or {}
    distributed = _is_distributed(intent)
    effective_max = int(max_services or 3)
    if not distributed:
        effective_max = 1

    services = _get_services_from_intent(intent) or _fallback_service_names()
    services = services[: max(1, effective_max)]

    compute_nodes = [n for n in nodes if (n.get("category") or "").lower() == "compute"]
    if not compute_nodes:
        return graph

    replacement_map: Dict[str, List[str]] = {}
    new_nodes: List[Dict[str, Any]] = []
    removed_ids = set()

    # Group compute nodes by capability_ref (treat multi-AZ instances as one tier)
    by_cap: Dict[str, List[Dict[str, Any]]] = {}
    for cn in compute_nodes:
        cap = (cn.get("capability_ref") or cn.get("id") or "compute").strip()
        by_cap.setdefault(cap, []).append(cn)

    for cap, group in by_cap.items():
        template = group[0]
        base_id = str(template.get("id") or cap)
        group_ids = [g.get("id") for g in group if g.get("id")]
        removed_ids.update(group_ids)

        # If group has >1 (multi-AZ), treat as min_instances>1 for replica modeling
        cfg = template.get("config") if isinstance(template.get("config"), dict) else {}
        min_instances = 1
        try:
            mi = cfg.get("min_instances")
            if isinstance(mi, (int, float)) and int(mi) > 0:
                min_instances = int(mi)
        except Exception:
            min_instances = 1
        if len(group_ids) > 1:
            min_instances = max(min_instances, len(group_ids))

        wants_replica = create_replicas and min_instances > 1

        service_primary_ids: List[str] = []

        for i, svc in enumerate(services, start=1):
            primary = copy.deepcopy(template)
            primary_id = f"{base_id}__svc_{i}__primary"
            primary["id"] = primary_id
            primary["ha_role"] = "PRIMARY"
            primary["service_name"] = svc
            primary_data = primary.get("data") or {}
            if isinstance(primary_data, dict):
                primary_data["label"] = svc
                primary_data["product_name"] = svc
            primary["data"] = primary_data

            # Strip instance counts from expanded service nodes (explicit replica nodes represent HA)
            if isinstance(primary.get("config"), dict):
                primary["config"] = dict(primary["config"])
                primary["config"]["min_instances"] = None
                primary["config"]["max_instances"] = None

            new_nodes.append(primary)
            service_primary_ids.append(primary_id)

            if wants_replica:
                replica = copy.deepcopy(primary)
                replica_id = f"{base_id}__svc_{i}__replica"
                replica["id"] = replica_id
                replica["ha_role"] = "REPLICA"
                rep_data = replica.get("data") or {}
                if isinstance(rep_data, dict):
                    rep_data["label"] = f"{svc} (Replica)"
                    rep_data["product_name"] = f"{svc} (Replica)"
                replica["data"] = rep_data
                new_nodes.append(replica)

                # Add explicit HA link (PRIMARY -> REPLICA). Frontend can style/collapse.
                edges.append(
                    {
                        "id": f"ha_{primary_id}_{replica_id}",
                        "from_node": primary_id,
                        "to": replica_id,
                        "protocol": "replica",
                        "type": "replica",
                    }
                )

        # Any compute instance id in this tier maps to the same service primaries
        for gid in group_ids:
            replacement_map[gid] = service_primary_ids

    # Keep non-compute nodes unchanged
    for n in nodes:
        if (n.get("id") in removed_ids) or ((n.get("category") or "").lower() == "compute"):
            continue
        new_nodes.append(n)

    # Rewire edges that touched replaced compute nodes to PRIMARY service nodes
    new_edges: List[Dict[str, Any]] = []
    for e in edges:
        src = e.get("from_node") or e.get("from") or e.get("source")
        tgt = e.get("to") or e.get("target")

        src_repl = replacement_map.get(src)
        tgt_repl = replacement_map.get(tgt)

        # Ignore edges that referenced removed compute nodes directly; will be expanded
        if src in removed_ids or tgt in removed_ids:
            pass

        if src_repl and not tgt_repl:
            for i, sid in enumerate(src_repl):
                ne = dict(e)
                ne["id"] = f"{e.get('id','e')}__srcsvc_{i+1}"
                ne["from_node"] = sid
                ne["to"] = tgt
                new_edges.append(ne)
            continue

        if tgt_repl and not src_repl:
            for i, tid in enumerate(tgt_repl):
                ne = dict(e)
                ne["id"] = f"{e.get('id','e')}__tgtsvc_{i+1}"
                ne["from_node"] = src
                ne["to"] = tid
                new_edges.append(ne)
            continue

        if src_repl and tgt_repl:
            for i, sid in enumerate(src_repl):
                for j, tid in enumerate(tgt_repl):
                    ne = dict(e)
                    ne["id"] = f"{e.get('id','e')}__srcsvc_{i+1}__tgtsvc_{j+1}"
                    ne["from_node"] = sid
                    ne["to"] = tid
                    new_edges.append(ne)
            continue

        # Keep unrelated edges
        if src and tgt:
            # normalize key names
            ne = dict(e)
            ne["from_node"] = e.get("from_node") or src
            ne["to"] = e.get("to") or tgt
            new_edges.append(ne)

    graph["nodes"] = new_nodes
    graph["edges"] = new_edges
    return graph

