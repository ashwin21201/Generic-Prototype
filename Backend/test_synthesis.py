"""
Test script for architecture synthesis pipeline
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from architecture_synthesis.policy import PolicyLoader, PolicyMerger
from architecture_synthesis.blocks import (
    BlockRegistryStore, BlockSelector, CompatibilityResolver
)
from architecture_synthesis.graph import GraphComposer
from architecture_synthesis.compliance import RuleEvaluationEngine
from architecture_synthesis.resolution import ProductCatalogStore, ProductResolutionEngine


def test_synthesis():
    """Test the full synthesis pipeline"""
    
    print("=" * 60)
    print("Testing Architecture Synthesis Pipeline")
    print("=" * 60)
    
    # Load Master Request JSON
    print("\n1. Loading Master Request JSON...")
    with open("outputs/architecture_intent_20260302_135616.json", "r") as f:
        master_request = json.load(f)
    print(f"   ✓ Loaded intent for sector: {master_request['request_metadata']['sector']}")
    
    # Load and merge policies
    print("\n2. Loading policies...")
    sector = master_request.get("request_metadata", {}).get("sector", "BFSI")
    policy_loader = PolicyLoader()
    policies = policy_loader.load_policies(sector=sector)
    print(f"   ✓ Loaded {len(policies)} policy files")
    
    policy_merger = PolicyMerger()
    merged_policy = policy_merger.merge(policies)
    print(f"   ✓ Merged into {len(merged_policy.rules)} rules")
    
    # Load block registry and select blocks
    print("\n3. Selecting architecture blocks...")
    block_registry = BlockRegistryStore()
    block_registry.load()
    print(f"   ✓ Loaded {len(block_registry.get_all_blocks())} blocks from registry")
    
    block_selector = BlockSelector(block_registry)
    selected_architecture = block_selector.select_blocks(master_request, merged_policy)
    print(f"   ✓ Selected {len(selected_architecture.selected_blocks)} blocks:")
    for block_id in selected_architecture.selected_blocks:
        print(f"      - {block_id}")
    
    # Resolve compatibility
    print("\n4. Resolving compatibility...")
    compatibility_resolver = CompatibilityResolver(block_registry)
    resolved_blocks, warnings = compatibility_resolver.resolve(
        selected_architecture.selected_blocks
    )
    print(f"   ✓ Resolved to {len(resolved_blocks)} blocks")
    if warnings:
        print(f"   ⚠ {len(warnings)} warnings:")
        for w in warnings[:3]:
            print(f"      - {w.message}")
    
    # Compose graph
    print("\n5. Composing graph...")
    graph_composer = GraphComposer()
    graph = graph_composer.compose(
        resolved_blocks,
        selected_architecture.deployment_topology
    )
    print(f"   ✓ Created graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
    print(f"   Nodes:")
    for node in graph.nodes[:5]:
        print(f"      - {node.id} ({node.category})")
    
    # Evaluate compliance
    print("\n6. Evaluating compliance...")
    rule_engine = RuleEvaluationEngine(block_registry)
    compliance_report = rule_engine.evaluate_all(merged_policy, graph)
    print(f"   ✓ Compliance status: {compliance_report.compliance_status}")
    print(f"   ✓ Risk score: {compliance_report.risk_score}")
    print(f"   ✓ Checks performed: {len(compliance_report.checks)}")
    if compliance_report.violations:
        print(f"   ⚠ Violations: {len(compliance_report.violations)}")
        for v in compliance_report.violations[:3]:
            print(f"      - {v.rule_id}: {v.message}")
    
    # Resolve products
    print("\n7. Resolving products...")
    product_catalog = ProductCatalogStore()
    product_catalog.load_catalogs(["aws", "your_cloud"])
    print(f"   ✓ Loaded catalogs for: {list(product_catalog.get_all_catalogs().keys())}")
    
    product_resolver = ProductResolutionEngine(product_catalog, block_registry)
    resolved_architecture = product_resolver.resolve(
        graph,
        selected_architecture.architecture_id,
        master_request.get("deployment_preferences")
    )
    print(f"   ✓ Resolved products for {len(resolved_architecture.resolved_products)} nodes")
    print(f"   ✓ Estimated cost: ${resolved_architecture.estimated_monthly_cost_usd}/month")
    
    # Summary
    print("\n" + "=" * 60)
    print("SYNTHESIS COMPLETE!")
    print("=" * 60)
    print(f"Architecture ID: {selected_architecture.architecture_id}")
    print(f"Blocks: {len(resolved_blocks)}")
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")
    print(f"Compliance: {compliance_report.compliance_status}")
    print(f"Estimated Cost: ${resolved_architecture.estimated_monthly_cost_usd}/month")
    print(f"Regions: {', '.join(selected_architecture.deployment_topology.regions)}")
    print("=" * 60)
    
    return {
        "selected_architecture": selected_architecture,
        "graph": graph,
        "compliance_report": compliance_report,
        "resolved_architecture": resolved_architecture
    }


if __name__ == "__main__":
    try:
        result = test_synthesis()
        print("\n✓ All tests passed!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
