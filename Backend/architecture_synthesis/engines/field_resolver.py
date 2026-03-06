"""
Field Resolver — Configurator §6 Step 1.
Resolves intent JSON paths (via block's intent_field_mappings) and block benchmarks
into a single variable context for formula evaluation.
"""
import logging
from typing import Any, Dict

from ..blocks.block_schemas import BlockDefinition, IntentFieldMapping

logger = logging.getLogger(__name__)


def _get_value_by_path(obj: Dict[str, Any], path: str) -> Any:
    """Get a nested value by dot-separated path, e.g. 'non_functional_requirements.expected_rps_peak'."""
    keys = path.strip().split(".")
    current = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def resolve_variable_context(
    intent: Dict[str, Any],
    block: BlockDefinition,
) -> Dict[str, Any]:
    """
    Build variable context from intent (via block's field mappings) and block benchmarks.
    Used by Formula Engine for expression evaluation (§6).
    """
    ctx: Dict[str, Any] = {}

    # 1) From intent field mappings
    for mapping in block.intent_field_mappings:
        if isinstance(mapping, dict):
            mapping = IntentFieldMapping(**mapping)
        elif not isinstance(mapping, IntentFieldMapping):
            continue
        value = _get_value_by_path(intent, mapping.intent_path)
        if value is None and mapping.default_value is not None:
            value = mapping.default_value
        if value is not None:
            ctx[mapping.maps_to] = value
        elif mapping.required:
            logger.warning(
                "Block %s requires intent path %s (maps_to=%s) but value missing",
                block.block_id,
                mapping.intent_path,
                mapping.maps_to,
            )

    # 2) From resource_benchmarks (snake_case keys as variables)
    if block.resource_benchmarks:
        rb = block.resource_benchmarks
        if rb.rps_per_cpu is not None:
            ctx["rps_per_cpu"] = rb.rps_per_cpu
        if rb.ram_per_cpu_gb is not None:
            ctx["ram_per_cpu_gb"] = rb.ram_per_cpu_gb
        ctx["min_cpu"] = rb.min_cpu
        ctx["min_ram_gb"] = rb.min_ram_gb
        if rb.disk_gb_default is not None:
            ctx["disk_gb_default"] = rb.disk_gb_default
        if rb.data_per_cpu_gb is not None:
            ctx["data_per_cpu_gb"] = rb.data_per_cpu_gb
        if rb.disk_multiplier is not None:
            ctx["disk_multiplier"] = rb.disk_multiplier
        if rb.ram_multiplier is not None:
            ctx["ram_multiplier"] = rb.ram_multiplier
        if rb.events_per_cpu is not None:
            ctx["events_per_cpu"] = rb.events_per_cpu
        if rb.metrics_per_cpu is not None:
            ctx["metrics_per_cpu"] = rb.metrics_per_cpu

    return ctx
