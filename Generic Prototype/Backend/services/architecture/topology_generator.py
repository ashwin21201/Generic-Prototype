"""6-dimension topology generation: select blocks, resolve dependencies, build and persist topology."""
import logging
from typing import Dict, Any, List

from architecture_synthesis.policy import PolicyLoader, PolicyMerger
from architecture_synthesis.blocks import BlockRegistryStore, BlockSelector, CompatibilityResolver

from services.architecture.topology_builder import build_topology

logger = logging.getLogger(__name__)


async def generate_topology(
    db_session,
    org_id: str,
    project_id: str,
    intent_json: Dict[str, Any],
    schema_version: str = None,
    session_id: str = None,
) -> tuple:
    """
    Run block selection, compatibility resolution, then persist topology.
    Returns (topology_id, selected_blocks: list of block_ids, warnings: list of dicts).
    """
    if not intent_json:
        raise ValueError("intent_json is required")

    intent = dict(intent_json)
    intent.setdefault("request_metadata", {})["org_id"] = org_id
    sector = (intent.get("request_metadata") or {}).get("sector", "BFSI")

    policy_loader = PolicyLoader()
    policies = policy_loader.load_policies(sector=sector)
    if not policies:
        policies = policy_loader.load_policies(sector="BFSI")
    policy_merger = PolicyMerger()
    merged_policy = policy_merger.merge(policies or [])

    block_registry = BlockRegistryStore()
    block_registry.load()
    block_selector = BlockSelector(block_registry)
    selected_architecture = block_selector.select_blocks(intent, merged_policy)
    selected_blocks = list(selected_architecture.selected_blocks)

    compatibility_resolver = CompatibilityResolver(block_registry)
    resolved_blocks, warnings = compatibility_resolver.resolve(selected_blocks)
    warnings_list = [{"message": w.message, "severity": getattr(w, "severity", "warning")} for w in (warnings or [])]

    topology_id, nodes_out, edges_out = build_topology(
        db_session,
        org_id=org_id,
        project_id=project_id,
        resolved_blocks=resolved_blocks,
        deployment_topology=selected_architecture.deployment_topology,
        intent_json=intent,
        schema_version=schema_version,
        session_id=session_id,
    )
    try:
        await db_session.commit()
    except Exception:
        await db_session.rollback()
        raise
    return topology_id, selected_blocks, warnings_list
