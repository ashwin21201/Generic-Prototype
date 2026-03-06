"""
Test script to verify block selection fixes
Run this to test if database blocks are now being selected correctly
"""

import logging
import json
import sys
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

from architecture_synthesis.blocks.block_registry import BlockRegistryStore
from architecture_synthesis.blocks.block_selector import BlockSelector
from architecture_synthesis.policy.policy_loader import PolicyLoader
from architecture_synthesis.policy.policy_merger import PolicyMerger

def test_block_selection():
    # Change to Backend directory to ensure relative paths work
    import os
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    """Test if database blocks are selected correctly"""
    
    print("\n" + "="*80)
    print("TESTING BLOCK SELECTION WITH STRICT SELECTION FIXES")
    print("="*80 + "\n")
    
    # Load the master request JSON
    intent_file = Path(__file__).parent / "outputs" / "architecture_intent_20260302_135616.json"
    if not intent_file.exists():
        print(f"❌ Master request file not found: {intent_file}")
        print(f"   Current directory: {Path.cwd()}")
        return
    
    with open(intent_file, 'r') as f:
        master_request = json.load(f)
    
    print("✅ Loaded Master Request JSON")
    print(f"   - Data types: {master_request.get('data_requirements', {}).get('data_types')}")
    print(f"   - Consistency: {master_request.get('data_requirements', {}).get('consistency_model')}")
    print(f"   - Availability: {master_request.get('non_functional_requirements', {}).get('availability_target_percent')}%")
    
    # Load policies
    sector = master_request.get("request_metadata", {}).get("sector", "BFSI")
    policy_loader = PolicyLoader()
    policies = policy_loader.load_policies(sector=sector)
    
    policy_merger = PolicyMerger()
    merged_policy = policy_merger.merge(policies)
    
    print(f"\n✅ Loaded and merged {len(policies)} policies for sector: {sector}")
    
    # Load block registry
    block_registry = BlockRegistryStore()
    block_registry.load()
    
    print(f"✅ Loaded block registry with {len(block_registry.get_all_blocks())} blocks")
    
    # Test block selection
    block_selector = BlockSelector(block_registry)
    
    print("\n" + "-"*80)
    print("RUNNING BLOCK SELECTION...")
    print("-"*80 + "\n")
    
    selected_architecture = block_selector.select_blocks(master_request, merged_policy)
    
    print("\n" + "-"*80)
    print("RESULTS:")
    print("-"*80 + "\n")
    
    print(f"Architecture ID: {selected_architecture.architecture_id}")
    print(f"\nSelected Blocks ({len(selected_architecture.selected_blocks)}):")
    for i, block_id in enumerate(selected_architecture.selected_blocks, 1):
        block = block_registry.get_block(block_id)
        if block:
            print(f"  {i}. {block_id} ({block.category})")
    
    print(f"\nDeployment Topology:")
    print(f"  - Regions: {selected_architecture.deployment_topology.regions}")
    print(f"  - Multi-AZ: {selected_architecture.deployment_topology.multi_az}")
    print(f"  - Active-Active: {selected_architecture.deployment_topology.active_active}")
    
    print(f"\nEstimated Cost: ${selected_architecture.estimated_monthly_cost_usd}/month")
    
    # Check if database block was selected
    has_database = any(
        block_registry.get_block(bid).category == "data"
        for bid in selected_architecture.selected_blocks
        if block_registry.get_block(bid)
    )
    
    print("\n" + "="*80)
    if has_database:
        print("✅ SUCCESS: Database block was selected!")
        db_blocks = [
            bid for bid in selected_architecture.selected_blocks
            if block_registry.get_block(bid) and block_registry.get_block(bid).category == "data"
        ]
        print(f"   Database blocks: {db_blocks}")
    else:
        print("❌ FAILURE: No database block was selected")
        print("   This indicates the fixes did not work as expected")
    
    if selected_architecture.deployment_topology.multi_az:
        print("✅ SUCCESS: Multi-AZ is enabled")
    else:
        print("⚠️  WARNING: Multi-AZ is not enabled (expected for 99.999% availability)")
    
    print("="*80 + "\n")
    
    return selected_architecture

if __name__ == "__main__":
    try:
        result = test_block_selection()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
