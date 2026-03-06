"""
Cost Analysis Module for Architecture Synthesis.

Provides detailed cost breakdown and optimization recommendations.
"""

import logging
from typing import Dict, List, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class CostAnalyzer:
    """Analyze costs of synthesized architecture"""
    
    def __init__(self, block_registry=None):
        self.block_registry = block_registry
    
    def analyze_costs(self, graph: Dict[str, Any], architecture_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze costs from architecture graph and provide detailed breakdown.
        
        Args:
            graph: Graph with nodes and edges
            architecture_data: Full architecture data including selected_architecture
        
        Returns:
            Detailed cost analysis with breakdowns and recommendations
        """
        nodes = graph.get("nodes", [])
        selected_arch = architecture_data.get("selected_architecture", {})
        
        # Calculate costs
        total_cost = selected_arch.get("estimated_monthly_cost_usd", 0.0)
        
        # Breakdown by layer
        by_layer = self._breakdown_by_layer(nodes)
        
        # Breakdown by category
        by_category = self._breakdown_by_category(nodes)
        
        # Breakdown by region
        by_region = self._breakdown_by_region(nodes)
        
        # Identify cost drivers (top 5 most expensive components)
        cost_drivers = self._identify_cost_drivers(nodes)
        
        # Generate optimization suggestions
        optimizations = self._generate_optimizations(nodes, selected_arch)
        
        return {
            "total_monthly_cost_usd": total_cost,
            "breakdown_by_layer": by_layer,
            "breakdown_by_category": by_category,
            "breakdown_by_region": by_region,
            "cost_drivers": cost_drivers,
            "optimization_suggestions": optimizations,
            "cost_trend": "stable",  # Could be calculated based on scaling configs
            "estimated_annual_cost_usd": total_cost * 12,
        }
    
    def _breakdown_by_layer(self, nodes: List[Dict]) -> Dict[str, float]:
        """Calculate cost breakdown by solution layer"""
        breakdown = defaultdict(float)
        
        for node in nodes:
            if node.get("type") == "group" or node.get("category") == "container":
                continue
            
            layer = node.get("solution_layer", "unknown")
            cost = self._estimate_node_cost(node)
            breakdown[layer] += cost
        
        return dict(breakdown)
    
    def _breakdown_by_category(self, nodes: List[Dict]) -> Dict[str, float]:
        """Calculate cost breakdown by category"""
        breakdown = defaultdict(float)
        
        for node in nodes:
            if node.get("type") == "group" or node.get("category") == "container":
                continue
            
            category = node.get("category", "unknown")
            cost = self._estimate_node_cost(node)
            breakdown[category] += cost
        
        return dict(breakdown)
    
    def _breakdown_by_region(self, nodes: List[Dict]) -> Dict[str, float]:
        """Calculate cost breakdown by region"""
        breakdown = defaultdict(float)
        
        for node in nodes:
            if node.get("type") == "group" or node.get("category") == "container":
                continue
            
            region = node.get("region", "global")
            cost = self._estimate_node_cost(node)
            breakdown[region] += cost
        
        return dict(breakdown)
    
    def _identify_cost_drivers(self, nodes: List[Dict]) -> List[Dict[str, Any]]:
        """Identify top 5 most expensive components"""
        node_costs = []
        
        for node in nodes:
            if node.get("type") == "group" or node.get("category") == "container":
                continue
            
            cost = self._estimate_node_cost(node)
            if cost > 0:
                node_costs.append({
                    "node_id": node.get("id"),
                    "node_label": node.get("data", {}).get("label", node.get("id")),
                    "category": node.get("category"),
                    "monthly_cost_usd": cost,
                    "percentage_of_total": 0.0,  # Will be calculated
                })
        
        # Sort by cost descending
        node_costs.sort(key=lambda x: x["monthly_cost_usd"], reverse=True)
        
        # Calculate percentages
        total = sum(n["monthly_cost_usd"] for n in node_costs)
        if total > 0:
            for node in node_costs:
                node["percentage_of_total"] = round((node["monthly_cost_usd"] / total) * 100, 1)
        
        # Return top 5
        return node_costs[:5]
    
    def _generate_optimizations(
        self, 
        nodes: List[Dict], 
        selected_arch: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations"""
        optimizations = []
        
        # Check for compute instances
        compute_nodes = [n for n in nodes if n.get("category") == "compute"]
        for node in compute_nodes:
            config = node.get("config", {})
            if config.get("max_instances", 0) > 10:
                optimizations.append({
                    "node_id": node.get("id"),
                    "recommendation_type": "reserved_instances",
                    "title": "Consider Reserved Instances",
                    "description": f"Use Reserved Instances for {node.get('data', {}).get('label', node.get('id'))} to save up to 40%",
                    "potential_savings_usd": self._estimate_node_cost(node) * 0.4,
                    "impact": "No performance impact",
                    "effort": "Low",
                })
        
        # Check for data replication
        data_nodes = [n for n in nodes if n.get("category") == "data"]
        replicas = [n for n in data_nodes if n.get("config", {}).get("replication_role") == "replica"]
        if len(replicas) > 2:
            optimizations.append({
                "node_id": None,
                "recommendation_type": "reduce_replication",
                "title": "Optimize Data Replication",
                "description": f"Review if {len(replicas)} database replicas are necessary",
                "potential_savings_usd": sum(self._estimate_node_cost(n) for n in replicas[2:]),
                "impact": "May affect read performance in some regions",
                "effort": "Medium",
            })
        
        # Check for storage optimization
        storage_nodes = [n for n in nodes if n.get("category") in ("storage", "data")]
        for node in storage_nodes:
            config = node.get("config", {})
            if config.get("disk_type") == "ssd" and config.get("disk_gb", 0) > 1000:
                optimizations.append({
                    "node_id": node.get("id"),
                    "recommendation_type": "tiered_storage",
                    "title": "Implement Storage Tiering",
                    "description": f"Use lifecycle policies to move infrequently accessed data to cheaper storage tiers",
                    "potential_savings_usd": self._estimate_node_cost(node) * 0.3,
                    "impact": "Minimal - applies to cold data",
                    "effort": "Low",
                })
        
        # Check for observability
        observability_nodes = [n for n in nodes if n.get("category") == "observability"]
        if len(observability_nodes) > 0:
            optimizations.append({
                "node_id": None,
                "recommendation_type": "log_retention",
                "title": "Optimize Log Retention",
                "description": "Set appropriate log retention policies (30 days for most logs, 90 days for audit logs)",
                "potential_savings_usd": 200.0,
                "impact": "No functional impact",
                "effort": "Low",
            })
        
        # Check for multi-region deployment
        regions = set(n.get("region") for n in nodes if n.get("region"))
        if len(regions) > 2:
            optimizations.append({
                "node_id": None,
                "recommendation_type": "region_consolidation",
                "title": "Review Multi-Region Strategy",
                "description": f"Currently deployed in {len(regions)} regions. Consider consolidating if full multi-region redundancy isn't required.",
                "potential_savings_usd": 1000.0,
                "impact": "May affect latency in some regions",
                "effort": "High",
            })
        
        return optimizations
    
    def _estimate_node_cost(self, node: Dict[str, Any]) -> float:
        """
        Estimate monthly cost for a single node.
        
        This is a simplified estimation. In production, you'd use actual pricing data.
        """
        category = node.get("category", "")
        config = node.get("config", {})
        
        # Base costs by category (monthly USD)
        base_costs = {
            "compute": 100.0,
            "data": 150.0,
            "storage": 50.0,
            "network": 80.0,
            "security": 30.0,
            "cache": 75.0,
            "messaging": 120.0,
            "observability": 50.0,
        }
        
        base = base_costs.get(category, 50.0)
        
        # Adjust based on resources
        cpu = config.get("cpu_count", 1)
        ram = config.get("ram_gb", 4)
        disk = config.get("disk_gb", 100)
        
        # Simple multiplier based on resources
        resource_multiplier = (cpu * 0.3) + (ram * 0.1) + (disk * 0.001)
        
        # Adjust for scaling
        min_instances = config.get("min_instances", 1)
        if min_instances:
            base *= min_instances
        
        # Adjust for multi-AZ
        if config.get("multi_az"):
            base *= 1.2
        
        total = base * (1 + resource_multiplier)
        
        return round(total, 2)


class CostOptimizer:
    """Provide cost optimization strategies"""
    
    def suggest_optimizations(
        self,
        graph: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest cost optimizations based on architecture and requirements.
        
        Returns list of optimization suggestions with potential savings.
        """
        analyzer = CostAnalyzer()
        return analyzer._generate_optimizations(
            graph.get("nodes", []),
            requirements
        )
