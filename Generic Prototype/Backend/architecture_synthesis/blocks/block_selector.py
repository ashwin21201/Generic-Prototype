import logging
import uuid
from typing import Dict, List, Set
from .block_schemas import (
    BlockDefinition, SelectedArchitectureJSON, 
    DeploymentTopology, ScoringDetail
)
from .block_registry import BlockRegistryStore
from ..policy.policy_schemas import MergedPolicy

logger = logging.getLogger(__name__)


class BlockSelector:
    """Map intent + policy to architecture blocks"""
    
    def __init__(self, block_registry: BlockRegistryStore):
        self.block_registry = block_registry
    
    def select_blocks(
        self,
        master_request: Dict,
        merged_policy: MergedPolicy
    ) -> SelectedArchitectureJSON:
        """
        Select architecture blocks based on intent and policy.
        
        Args:
            master_request: Master Request JSON (intent)
            merged_policy: Merged policy with rules and constraints
            
        Returns:
            SelectedArchitectureJSON with selected blocks and topology
        """
        logger.info("Starting block selection")
        
        # Step 1: Determine categories needed
        categories_needed = self._determine_categories(master_request)
        logger.info(f"Categories needed: {categories_needed}")
        
        # Step 2: Determine required capabilities per category
        required_capabilities = self._determine_required_capabilities(
            master_request, merged_policy, categories_needed
        )
        logger.info(f"Required capabilities: {required_capabilities}")
        
        # Step 3: Add mandatory blocks from policy
        mandatory_block_ids = [mb.block_id for mb in merged_policy.mandatory_blocks]
        logger.info(f"Mandatory blocks from policy: {mandatory_block_ids}")
        
        # Step 4: Select blocks per category
        selected_blocks = []
        for category in categories_needed:
            required_caps = required_capabilities.get(category, {})
            
            # DEBUG: Log detailed information
            logger.info(f"=== Processing category: {category} ===")
            logger.info(f"Required capabilities: {required_caps}")
            
            # Get all blocks in this category
            all_blocks_in_category = self.block_registry.get_blocks_by_category(category)
            logger.info(f"All blocks in '{category}': {[b.block_id for b in all_blocks_in_category]}")
            
            # Find candidates
            candidates = self._find_candidate_blocks(category, required_caps)
            logger.info(f"Found {len(candidates)} candidates: {[c.block_id for c in candidates]}")
            
            if candidates:
                # Score and pick best
                best_block = self._score_and_select(
                    candidates,
                    master_request.get("optimization_priorities", {})
                )
                selected_blocks.append(best_block.block_id)
                logger.info(f"✅ Selected {best_block.block_id} for category {category}")
            else:
                logger.warning(f"❌ No suitable block found for category {category} with required capabilities: {required_caps}")
        
        # Add mandatory blocks
        for block_id in mandatory_block_ids:
            if block_id not in selected_blocks:
                selected_blocks.append(block_id)
                logger.info(f"Added mandatory block: {block_id}")
        
        # Step 5: Determine deployment topology
        deployment_topology = self._determine_deployment_topology(master_request, merged_policy)
        
        # Step 6: Calculate estimated cost
        estimated_cost = self._estimate_cost(selected_blocks)
        
        # Step 7: Calculate scoring summary
        scoring_summary = self._calculate_scoring_summary(
            selected_blocks,
            master_request.get("optimization_priorities", {})
        )
        
        # Step 8: Determine compliance alignment
        compliance_alignment = self._determine_compliance_alignment(selected_blocks, merged_policy)
        
        architecture_id = f"arch_{uuid.uuid4().hex[:8]}"
        
        return SelectedArchitectureJSON(
            architecture_id=architecture_id,
            selected_blocks=selected_blocks,
            deployment_topology=deployment_topology,
            scoring_summary=scoring_summary,
            estimated_monthly_cost_usd=estimated_cost,
            compliance_alignment=compliance_alignment
        )
    
    def _determine_categories(self, master_request: Dict) -> Set[str]:
        """Determine which categories are needed based on intent"""
        categories = set()
        
        func_req = master_request.get("functional_requirements", {})
        non_func_req = master_request.get("non_functional_requirements", {})
        data_req = master_request.get("data_requirements", {})
        security_req = master_request.get("security_requirements", {})
        observability_req = master_request.get("observability_requirements", {})
        
        # Web app, API, public access → network + security + compute
        if (func_req.get("application_type") in ["Web application", "web_application", "api"] or
            func_req.get("public_access_required") or
            func_req.get("api_required")):
            categories.update(["network", "security", "compute"])
        
        # Data storage needs
        data_types = data_req.get("data_types", [])
        logger.info(f"Data types from request: {data_types}")
        if "structured" in data_types or "relational" in data_types:
            categories.add("data")
            logger.info("Added 'data' category due to data_types requirement")
        
        if "unstructured" in data_req.get("data_types", []):
            categories.add("storage")
        
        # Real-time or async processing → messaging
        if func_req.get("real_time_processing") or func_req.get("interaction_model") == "asynchronous":
            categories.add("messaging")
        
        # Caching for performance
        if non_func_req.get("expected_rps_peak", 0) > 1000:
            categories.add("cache")
        
        # Observability
        if (observability_req.get("logging_required") or 
            security_req.get("audit_logging_required")):
            categories.add("observability")
        
        return categories
    
    def _determine_required_capabilities(
        self,
        master_request: Dict,
        merged_policy: MergedPolicy,
        categories: Set[str]
    ) -> Dict[str, Dict[str, bool]]:
        """Determine required capabilities per category"""
        required_caps = {}
        
        security_req = master_request.get("security_requirements", {})
        data_req = master_request.get("data_requirements", {})
        deployment_pref = master_request.get("deployment_preferences", {})
        non_func_req = master_request.get("non_functional_requirements", {})
        
        for category in categories:
            caps = {}
            
            # Security requirements
            if category in ["data", "storage", "cache"]:
                if security_req.get("data_encryption_at_rest"):
                    caps["data_encryption_at_rest"] = True
                if security_req.get("data_encryption_in_transit"):
                    caps["data_encryption_in_transit"] = True
                if security_req.get("audit_logging_required"):
                    caps["audit_logging"] = True
            
            # Compute requirements
            if category == "compute":
                if non_func_req.get("horizontal_scaling_required"):
                    caps["horizontal_scaling"] = True
                    caps["stateless_compute"] = True
                if deployment_pref.get("containerization_preferred"):
                    caps["container_support"] = True
            
            # Data requirements
            if category == "data":
                if data_req.get("consistency_model") == "strong":
                    caps["strong_consistency"] = True
                    caps["relational_storage"] = True
                    caps["acid_transactions"] = True
                elif data_req.get("consistency_model") == "eventual":
                    caps["eventual_consistency"] = True
                
                # Check for structured or relational data types
                if "structured" in data_req.get("data_types", []) or "relational" in data_req.get("data_types", []):
                    caps["structured_storage"] = True
                
                if non_func_req.get("availability_target_percent", 0) >= 99.9:
                    caps["multi_az_deployment"] = True
            
            # Network requirements
            if category == "network":
                caps["api_management"] = True
                caps["routing"] = True
            
            # Security category
            if category == "security":
                caps["web_application_firewall"] = True
                caps["audit_logging"] = True
            
            # Messaging requirements
            if category == "messaging":
                caps["asynchronous_processing"] = True
                caps["event_driven_architecture"] = True
            
            # Cache requirements
            if category == "cache":
                caps["in_memory_cache"] = True
                caps["low_latency"] = True
            
            # Observability requirements
            if category == "observability":
                caps["audit_logging"] = True
                caps["log_aggregation"] = True
            
            # Apply policy capability rules
            for rule in merged_policy.rules:
                if rule.rule_type == "capability" and rule.target_category == category:
                    if rule.condition and rule.condition.operator == "equals":
                        caps[rule.condition.field] = rule.condition.value
            
            required_caps[category] = caps
        
        return required_caps
    
    def _find_candidate_blocks(
        self,
        category: str,
        required_capabilities: Dict[str, bool]
    ) -> List[BlockDefinition]:
        """Find blocks in category that match required capabilities"""
        category_blocks = self.block_registry.get_blocks_by_category(category)
        
        candidates = []
        for block in category_blocks:
            matches_all = True
            mismatches = []
            
            for cap, required_value in required_capabilities.items():
                block_cap_value = block.capabilities_provided.get(cap)
                
                # Only check if capability is required (True)
                if required_value:
                    # Block must have this capability set to True
                    if not block_cap_value:
                        matches_all = False
                        mismatches.append(f"{cap}: required=True, provided={block_cap_value}")
                # If required_value is False, we don't care if block has it or not
            
            if matches_all:
                candidates.append(block)
                logger.debug(f"  ✅ Block '{block.block_id}' matches all requirements")
            else:
                logger.debug(f"  ❌ Block '{block.block_id}' mismatches: {mismatches}")
        
        return candidates
    
    def _score_and_select(
        self,
        candidates: List[BlockDefinition],
        optimization_priorities: Dict
    ) -> BlockDefinition:
        """Score candidates and select the best one"""
        if len(candidates) == 1:
            return candidates[0]
        
        perf_weight = optimization_priorities.get("performance_weight", 0.25)
        cost_weight = optimization_priorities.get("cost_weight", 0.25)
        compliance_weight = optimization_priorities.get("compliance_weight", 0.25)
        simplicity_weight = optimization_priorities.get("operational_simplicity_weight", 0.25)
        
        best_block = None
        best_score = -1
        
        for block in candidates:
            # Normalize scores (0-1 range)
            perf_score = min(block.performance_profile.max_rps_supported or 1000, 100000) / 100000
            cost_score = 1.0 - min(block.cost_profile.base_monthly_cost_usd, 5000) / 5000
            compliance_score = len(block.compliance_tags) / 5.0
            simplicity_score = 1.0 - (block.complexity_score / 10.0)
            
            weighted_score = (
                perf_score * perf_weight +
                cost_score * cost_weight +
                compliance_score * compliance_weight +
                simplicity_score * simplicity_weight
            )
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_block = block
        
        return best_block or candidates[0]
    
    def _determine_deployment_topology(
        self,
        master_request: Dict,
        merged_policy: MergedPolicy
    ) -> DeploymentTopology:
        """Determine deployment topology from intent and policy"""
        non_func_req = master_request.get("non_functional_requirements", {})
        deployment_pref = master_request.get("deployment_preferences", {})
        
        multi_region = (
            non_func_req.get("multi_region_required", False) or
            deployment_pref.get("multi_region_required", False)
        )
        
        # Check policy for multi-region requirement
        for rule in merged_policy.rules:
            if rule.rule_type == "deployment" and rule.target_category == "data":
                if rule.condition and rule.condition.field == "region_count":
                    if rule.condition.value >= 2:
                        multi_region = True
        
        regions = ["ap-south-1"]
        if multi_region:
            regions.append("ap-southeast-1")
        
        # Multi-AZ should be enabled for high availability targets
        availability_target = non_func_req.get("availability_target_percent", 0)
        multi_az = availability_target >= 99.9
        
        # If multi-region, also enable multi-AZ
        if multi_region:
            multi_az = True
        
        logger.info(f"Deployment topology: regions={regions}, multi_az={multi_az}, active_active={multi_region}, availability_target={availability_target}")
        
        return DeploymentTopology(
            regions=regions,
            active_active=multi_region,
            multi_az=multi_az,
            replication_required=multi_region
        )
    
    def _estimate_cost(self, selected_block_ids: List[str]) -> float:
        """Estimate total monthly cost"""
        total_cost = 0.0
        
        for block_id in selected_block_ids:
            block = self.block_registry.get_block(block_id)
            if block:
                total_cost += block.cost_profile.base_monthly_cost_usd
        
        return total_cost
    
    def _calculate_scoring_summary(
        self,
        selected_block_ids: List[str],
        optimization_priorities: Dict
    ) -> ScoringDetail:
        """Calculate overall scoring summary"""
        blocks = [self.block_registry.get_block(bid) for bid in selected_block_ids if self.block_registry.get_block(bid)]
        
        if not blocks:
            return ScoringDetail()
        
        # Average performance score
        perf_scores = [min(b.performance_profile.max_rps_supported or 1000, 100000) / 100000 for b in blocks]
        avg_perf = sum(perf_scores) / len(perf_scores) if perf_scores else 0.0
        
        # Average cost score (inverted - lower cost = higher score)
        cost_scores = [1.0 - min(b.cost_profile.base_monthly_cost_usd, 5000) / 5000 for b in blocks]
        avg_cost = sum(cost_scores) / len(cost_scores) if cost_scores else 0.0
        
        # Compliance score
        all_tags = set()
        for b in blocks:
            all_tags.update(b.compliance_tags)
        compliance_score = min(len(all_tags) / 5.0, 1.0)
        
        # Simplicity score
        simplicity_scores = [1.0 - (b.complexity_score / 10.0) for b in blocks]
        avg_simplicity = sum(simplicity_scores) / len(simplicity_scores) if simplicity_scores else 0.0
        
        # Weighted final score
        perf_weight = optimization_priorities.get("performance_weight", 0.25)
        cost_weight = optimization_priorities.get("cost_weight", 0.25)
        compliance_weight = optimization_priorities.get("compliance_weight", 0.25)
        simplicity_weight = optimization_priorities.get("operational_simplicity_weight", 0.25)
        
        final_score = (
            avg_perf * perf_weight +
            avg_cost * cost_weight +
            compliance_score * compliance_weight +
            avg_simplicity * simplicity_weight
        )
        
        return ScoringDetail(
            performance_score=round(avg_perf, 2),
            cost_score=round(avg_cost, 2),
            compliance_score=round(compliance_score, 2),
            simplicity_score=round(avg_simplicity, 2),
            final_weighted_score=round(final_score, 2)
        )
    
    def _determine_compliance_alignment(
        self,
        selected_block_ids: List[str],
        merged_policy: MergedPolicy
    ) -> List[str]:
        """Determine which compliance standards are met"""
        all_tags = set()
        
        for block_id in selected_block_ids:
            block = self.block_registry.get_block(block_id)
            if block:
                all_tags.update(block.compliance_tags)
        
        return list(all_tags)
