import logging
from typing import List, Literal
from datetime import datetime
from .policy_schemas import (
    PolicyJSON, MergedPolicy, PolicyMetadata, 
    Applicability, Rule, ForbiddenPattern, MandatoryBlock
)

logger = logging.getLogger(__name__)


class PolicyMerger:
    """Merge multiple policies into a single unified policy"""
    
    def merge(
        self,
        policies: List[PolicyJSON],
        strategy: Literal["highest_priority_wins", "most_restrictive"] = "highest_priority_wins"
    ) -> MergedPolicy:
        """
        Merge multiple policies into one.
        
        Args:
            policies: List of PolicyJSON objects to merge
            strategy: Conflict resolution strategy
            
        Returns:
            MergedPolicy with combined rules and constraints
        """
        if not policies:
            raise ValueError("Cannot merge empty policy list")
        
        if len(policies) == 1:
            # Single policy, just convert to MergedPolicy
            return self._convert_to_merged(policies[0])
        
        # Sort policies by priority (highest first)
        sorted_policies = sorted(policies, key=lambda p: p.policy_metadata.priority, reverse=True)
        
        # Use highest priority policy as base
        base_policy = sorted_policies[0]
        
        # Merge metadata
        merged_metadata = self._merge_metadata(sorted_policies)
        
        # Merge applicability
        merged_applicability = self._merge_applicability(sorted_policies)
        
        # Merge rules (deduplicate by rule_id)
        merged_rules = self._merge_rules(sorted_policies, strategy)
        
        # Merge forbidden patterns
        merged_patterns = self._merge_forbidden_patterns(sorted_policies)
        
        # Merge mandatory blocks
        merged_blocks = self._merge_mandatory_blocks(sorted_policies)
        
        # Collect source policy IDs
        source_policies = [p.policy_metadata.policy_id for p in sorted_policies]
        
        merged = MergedPolicy(
            policy_metadata=merged_metadata,
            applicability=merged_applicability,
            rules=merged_rules,
            forbidden_patterns=merged_patterns,
            mandatory_blocks=merged_blocks,
            policy_exceptions=base_policy.policy_exceptions,
            evaluation_strategy=base_policy.evaluation_strategy,
            reporting=base_policy.reporting,
            source_policies=source_policies
        )
        
        logger.info(f"Merged {len(policies)} policies into one with {len(merged_rules)} rules")
        return merged
    
    def _convert_to_merged(self, policy: PolicyJSON) -> MergedPolicy:
        """Convert a single PolicyJSON to MergedPolicy"""
        return MergedPolicy(
            policy_metadata=policy.policy_metadata,
            applicability=policy.applicability,
            rules=policy.rules,
            forbidden_patterns=policy.forbidden_patterns,
            mandatory_blocks=policy.mandatory_blocks,
            policy_exceptions=policy.policy_exceptions,
            evaluation_strategy=policy.evaluation_strategy,
            reporting=policy.reporting,
            source_policies=[policy.policy_metadata.policy_id]
        )
    
    def _merge_metadata(self, policies: List[PolicyJSON]) -> PolicyMetadata:
        """Merge policy metadata, using highest priority as base"""
        base = policies[0].policy_metadata
        
        return PolicyMetadata(
            policy_id=f"merged_{base.policy_id}",
            policy_name=f"Merged Policy: {base.policy_name}",
            sector=base.sector,
            region=base.region,
            version="1.0.0",
            status="active",
            priority=base.priority,
            enforcement_mode=base.enforcement_mode,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description=f"Merged from {len(policies)} policies"
        )
    
    def _merge_applicability(self, policies: List[PolicyJSON]) -> Applicability:
        """Merge applicability - union of all applicable environments/criticality"""
        all_envs = set()
        all_criticality = set()
        all_providers = set()
        
        for policy in policies:
            all_envs.update(policy.applicability.environments)
            all_criticality.update(policy.applicability.business_criticality)
            all_providers.update(policy.applicability.cloud_providers)
        
        return Applicability(
            environments=list(all_envs),
            business_criticality=list(all_criticality),
            cloud_providers=list(all_providers)
        )
    
    def _merge_rules(
        self, 
        policies: List[PolicyJSON], 
        strategy: str
    ) -> List[Rule]:
        """Merge rules, deduplicating by rule_id"""
        rules_dict = {}
        
        for policy in policies:
            for rule in policy.rules:
                if rule.rule_id not in rules_dict:
                    # First occurrence, add it
                    rules_dict[rule.rule_id] = rule
                else:
                    # Duplicate rule_id, apply strategy
                    if strategy == "highest_priority_wins":
                        # Policy with higher priority already added (sorted order)
                        logger.debug(f"Rule {rule.rule_id} already exists, keeping higher priority version")
                    elif strategy == "most_restrictive":
                        # Keep more restrictive rule (higher severity)
                        existing = rules_dict[rule.rule_id]
                        if self._is_more_restrictive(rule, existing):
                            rules_dict[rule.rule_id] = rule
                            logger.debug(f"Replacing rule {rule.rule_id} with more restrictive version")
        
        return list(rules_dict.values())
    
    def _is_more_restrictive(self, rule1: Rule, rule2: Rule) -> bool:
        """Determine if rule1 is more restrictive than rule2"""
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        return severity_order.get(rule1.severity, 0) > severity_order.get(rule2.severity, 0)
    
    def _merge_forbidden_patterns(self, policies: List[PolicyJSON]) -> List[ForbiddenPattern]:
        """Merge forbidden patterns, deduplicating by pattern_id"""
        patterns_dict = {}
        
        for policy in policies:
            for pattern in policy.forbidden_patterns:
                if pattern.pattern_id not in patterns_dict:
                    patterns_dict[pattern.pattern_id] = pattern
        
        return list(patterns_dict.values())
    
    def _merge_mandatory_blocks(self, policies: List[PolicyJSON]) -> List[MandatoryBlock]:
        """Merge mandatory blocks, deduplicating by block_id"""
        blocks_dict = {}
        
        for policy in policies:
            for block in policy.mandatory_blocks:
                if block.block_id not in blocks_dict:
                    blocks_dict[block.block_id] = block
        
        return list(blocks_dict.values())
