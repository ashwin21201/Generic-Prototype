"""Build Topology + TopologyNode + TopologyEdge from resolved blocks and intent (persist to DB)."""
import uuid
import logging
from typing import List, Dict, Any

from architecture_synthesis.blocks.block_schemas import BlockDefinition, DeploymentTopology
from architecture_synthesis.graph import GraphComposer
from architecture_synthesis.graph.graph_schemas import GraphTopologyJSON, Node, Edge

from models import Topology, TopologyNode, TopologyEdge

logger = logging.getLogger(__name__)


def build_topology(
    db_session,
    org_id: str,
    project_id: str,
    resolved_blocks: List[BlockDefinition],
    deployment_topology: DeploymentTopology,
    intent_json: Dict[str, Any],
    schema_version: str = None,
    session_id: str = None,
) -> tuple:
    """
    Compose in-memory graph from blocks, then persist Topology + nodes + edges.
    Returns (topology_id, list of node dicts, list of edge dicts).
    """
    composer = GraphComposer()
    graph = composer.compose(
        resolved_blocks,
        deployment_topology,
        intent=intent_json,
    )
    topology_id = f"top_{uuid.uuid4().hex[:12]}"
    topology = Topology(
        id=topology_id,
        project_id=project_id,
        org_id=org_id,
        status="COMPLETED",
        intent_snapshot=intent_json or {},
        schema_version=schema_version,
        session_id=session_id,
        version=1,
    )
    db_session.add(topology)

    node_id_to_db_id = {}
    for n in graph.nodes:
        spec = {}
        if n.config:
            spec = n.config.model_dump() if hasattr(n.config, "model_dump") else (n.config or {})
        # Store semantic (graph) id for traceability and future diffing
        try:
            spec = dict(spec or {})
            spec["_semantic_id"] = n.id
        except Exception:
            pass
        db_node_id = f"n_{uuid.uuid4().hex[:12]}"
        db_node = TopologyNode(
            id=db_node_id,
            topology_id=topology_id,
            block_id=n.capability_ref or n.id.split("_")[0] if "_" in n.id else n.id,
            instance_name=n.data.label if n.data else n.id,
            layer=_layer_for_category(n.category),
            region=getattr(n, "region", None),
            spec=spec,
            capability_ref=n.capability_ref,
            category=n.category,
            node_type=n.type,
            data_label=n.data.label if n.data else n.id,
        )
        db_session.add(db_node)
        node_id_to_db_id[n.id] = db_node_id

    for e in graph.edges:
        src = getattr(e, "from_node", None)
        if src is None:
            d = e.model_dump() if hasattr(e, "model_dump") else {}
            src = d.get("from_node") or d.get("from")
        to_id = getattr(e, "to", None)
        if not src or not to_id:
            continue
        src_db = node_id_to_db_id.get(src)
        tgt_db = node_id_to_db_id.get(to_id)
        if not src_db or not tgt_db:
            continue
        edge_id = f"e_{uuid.uuid4().hex[:16]}"
        db_edge = TopologyEdge(
            id=edge_id,
            topology_id=topology_id,
            source_node_id=src_db,
            target_node_id=tgt_db,
            protocol=getattr(e, "protocol", None),
            edge_type=getattr(e, "type", "traffic"),
        )
        db_session.add(db_edge)

    logger.info("Persisted topology %s with %s nodes, %s edges", topology_id, len(graph.nodes), len(graph.edges))
    nodes_out = [
        {
            "id": node_id_to_db_id.get(n.id),
            "semantic_id": n.id,
            "block_id": n.capability_ref or (n.id.split("_")[0] if "_" in n.id else n.id),
            "category": n.category,
        }
        for n in graph.nodes
    ]
    edges_out = []
    for e in graph.edges:
        src = getattr(e, "from_node", None) or (e.model_dump() if hasattr(e, "model_dump") else {}).get("from_node")
        edges_out.append(
            {
                "id": "",
                "source": node_id_to_db_id.get(src),
                "target": node_id_to_db_id.get(getattr(e, "to", None)),
            }
        )
    return topology_id, nodes_out, edges_out


def _layer_for_category(category: str) -> int:
    if category in ("network", "security", "external"):
        return 1
    if category == "compute":
        return 2
    if category in ("data", "cache", "storage", "messaging", "observability"):
        return 3
    return 2
