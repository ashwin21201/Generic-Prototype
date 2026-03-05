"""
Graph Normalizer — Ensures layout engine receives a clean graph.
Normalizes edge keys (from_node, to), optional cycle handling for DAG.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def normalize_graph(graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize graph for layout: consistent edge format (from_node, to).
    Mutates graph in place and returns it.
    """
    edges: List[Dict[str, Any]] = graph.get("edges") or []
    for e in edges:
        if "from_node" not in e and "from" in e:
            e["from_node"] = e["from"]
        if "from_node" not in e and "source" in e:
            e["from_node"] = e["source"]
        if "to" not in e and "target" in e:
            e["to"] = e["target"]
    logger.debug(f"Normalized {len(edges)} edges")
    return graph
