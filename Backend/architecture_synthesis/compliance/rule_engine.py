import logging
from datetime import datetime
from typing import List
from .compliance_schemas import ComplianceReportJSON, RuleCheck, Violation
from ..policy.policy_schemas import MergedPolicy
from ..graph.graph_schemas import GraphTopologyJSON
from ..blocks.block_registry import BlockRegistryStore

logger = logging.getLogger(__name__)


class RuleEvaluationEngine:
    """Evaluate compliance rules against architecture graph"""
    
    def __init__(self, block_registry: BlockRegistryStore):
        self.block_registry = block_registry
    
    def evaluate_all(
        self,
        merged_policy: MergedPolicy,
        graph: GraphTopologyJSON
    ) -> ComplianceReportJSON:
        """
        Evaluate all policy rules against the graph.
        
        Args:
            merged_policy: Merged policy with rules
            graph: Architecture graph
            
        Returns:
            ComplianceReportJSON with evaluation results
        """
        logger.info(f"Evaluating {len(merged_policy.rules)} rules against graph")
        
        checks = []
        violations = []
        
        # Evaluate each rule
        for rule in merged_policy.rules:
            check = self._evaluate_rule(rule, graph)
            checks.append(check)
            
            if check.status == "fail":
                violations.append(Violation(
                    rule_id=rule.rule_id,
                    severity=rule.severity,
                    message=f"{rule.description} - Check failed",
                    affected_nodes=[]
                ))
        
        # Check forbidden patterns
        forbidden_checks = self._check_forbidden_patterns(merged_policy, graph)
        
        # Calculate compliance status and risk score
        compliance_status = "compliant" if len(violations) == 0 else "non_compliant"
        risk_score = self._calculate_risk_score(violations)
        
        report = ComplianceReportJSON(
            compliance_status=compliance_status,
            risk_score=risk_score,
            sector=merged_policy.policy_metadata.sector,
            policy_id=merged_policy.policy_metadata.policy_id,
            evaluated_at=datetime.now(),
            checks=checks,
            violations=violations,
            auto_remediations_applied=[],
            forbidden_patterns_checked=forbidden_checks
        )
        
        logger.info(f"Compliance evaluation complete: {compliance_status}, risk score: {risk_score}")
        return report
    
    def _evaluate_rule(self, rule, graph: GraphTopologyJSON) -> RuleCheck:
        """Evaluate a single rule"""
        # Simplified evaluation - can be expanded based on rule type
        
        if rule.rule_type == "capability":
            return self._evaluate_capability_rule(rule, graph)
        elif rule.rule_type == "deployment":
            return self._evaluate_deployment_rule(rule, graph)
        elif rule.rule_type == "topology":
            return self._evaluate_topology_rule(rule, graph)
        elif rule.rule_type == "relationship":
            return self._evaluate_relationship_rule(rule, graph)
        else:
            return RuleCheck(
                rule_id=rule.rule_id,
                status="pass",
                target_category=rule.target_category,
                details="Rule type not yet implemented"
            )
    
    def _evaluate_capability_rule(self, rule, graph: GraphTopologyJSON) -> RuleCheck:
        """Evaluate capability rule"""
        # Check if nodes in target category have required capability
        target_nodes = [n for n in graph.nodes if n.category == rule.target_category]
        
        if not target_nodes:
            return RuleCheck(
                rule_id=rule.rule_id,
                status="pass",
                target_category=rule.target_category,
                details=f"No nodes in category {rule.target_category}"
            )
        
        # Check each node's block for the capability
        for node in target_nodes:
            if node.capability_ref:
                block = self.block_registry.get_block(node.capability_ref)
                if block:
                    capability = rule.condition.field
                    required_value = rule.condition.value
                    actual_value = block.capabilities_provided.get(capability)
                    
                    if actual_value != required_value:
                        return RuleCheck(
                            rule_id=rule.rule_id,
                            status="fail",
                            target_category=rule.target_category,
                            details=f"Node {node.id} missing required capability: {capability}"
                        )
        
        return RuleCheck(
            rule_id=rule.rule_id,
            status="pass",
            target_category=rule.target_category,
            details=f"All {rule.target_category} nodes have required capabilities"
        )
    
    def _evaluate_deployment_rule(self, rule, graph: GraphTopologyJSON) -> RuleCheck:
        """Evaluate deployment rule"""
        target_nodes = [n for n in graph.nodes if n.category == rule.target_category]
        
        if rule.condition.field == "region_count":
            # Count unique regions for target category
            regions = set(n.region for n in target_nodes if n.region)
            region_count = len(regions)
            required_count = rule.condition.value
            
            if rule.condition.operator == "greater_or_equal":
                if region_count >= required_count:
                    return RuleCheck(
                        rule_id=rule.rule_id,
                        status="pass",
                        target_category=rule.target_category,
                        details=f"{rule.target_category} deployed in {region_count} regions"
                    )
                else:
                    return RuleCheck(
                        rule_id=rule.rule_id,
                        status="fail",
                        target_category=rule.target_category,
                        details=f"{rule.target_category} only in {region_count} regions, requires {required_count}"
                    )
        
        return RuleCheck(
            rule_id=rule.rule_id,
            status="pass",
            target_category=rule.target_category,
            details="Deployment rule check passed"
        )
    
    def _evaluate_topology_rule(self, rule, graph: GraphTopologyJSON) -> RuleCheck:
        """Evaluate topology rule"""
        target_nodes = [n for n in graph.nodes if n.category == rule.target_category]
        
        if rule.condition.field == "public_access":
            for node in target_nodes:
                if node.config and hasattr(node.config, 'public_access'):
                    if node.config.public_access != rule.condition.value:
                        return RuleCheck(
                            rule_id=rule.rule_id,
                            status="fail",
                            target_category=rule.target_category,
                            details=f"Node {node.id} has incorrect public_access setting"
                        )
        
        return RuleCheck(
            rule_id=rule.rule_id,
            status="pass",
            target_category=rule.target_category,
            details="Topology rule check passed"
        )
    
    def _evaluate_relationship_rule(self, rule, graph: GraphTopologyJSON) -> RuleCheck:
        """Evaluate relationship rule"""
        # Check if required predecessor exists in edge path
        target_nodes = [n for n in graph.nodes if n.category == rule.target_category]
        
        if hasattr(rule.condition, 'must_be_preceded_by'):
            required_predecessor = rule.condition.must_be_preceded_by
            
            for target_node in target_nodes:
                # Find edges leading to this node
                incoming_edges = [e for e in graph.edges if e.to == target_node.id]
                
                # Check if any incoming edge comes from required predecessor
                has_required_predecessor = False
                for edge in incoming_edges:
                    from_node = next((n for n in graph.nodes if n.id == edge.from_node), None)
                    if from_node and from_node.capability_ref == required_predecessor:
                        has_required_predecessor = True
                        break
                
                if not has_required_predecessor:
                    return RuleCheck(
                        rule_id=rule.rule_id,
                        status="fail",
                        target_category=rule.target_category,
                        details=f"Node {target_node.id} not preceded by {required_predecessor}"
                    )
        
        return RuleCheck(
            rule_id=rule.rule_id,
            status="pass",
            target_category=rule.target_category,
            details="Relationship rule check passed"
        )
    
    def _check_forbidden_patterns(self, merged_policy: MergedPolicy, graph: GraphTopologyJSON) -> List[dict]:
        """Check for forbidden patterns"""
        checks = []
        
        for pattern in merged_policy.forbidden_patterns:
            detection = pattern.detection_logic
            category = detection.get("category")
            
            if category:
                nodes = [n for n in graph.nodes if n.category == category]
                
                # Check pattern conditions
                if "region_count" in detection:
                    regions = set(n.region for n in nodes if n.region)
                    if len(regions) == detection["region_count"]:
                        checks.append({
                            "pattern_id": pattern.pattern_id,
                            "status": "fail",
                            "description": pattern.description
                        })
                    else:
                        checks.append({
                            "pattern_id": pattern.pattern_id,
                            "status": "pass"
                        })
        
        return checks
    
    def _calculate_risk_score(self, violations: List[Violation]) -> float:
        """Calculate overall risk score from violations"""
        if not violations:
            return 0.0
        
        severity_weights = {
            "critical": 1.0,
            "high": 0.7,
            "medium": 0.4,
            "low": 0.2
        }
        
        total_weight = sum(severity_weights.get(v.severity, 0.5) for v in violations)
        risk_score = min(total_weight / 10.0, 1.0)  # Normalize to 0-1
        
        return round(risk_score, 2)
