import logging
from typing import List, Dict, Optional
from .graph_schemas import GraphTopologyJSON, Node, Edge, NodeData, NodeConfig
from ..blocks.block_schemas import BlockDefinition, DeploymentTopology

logger = logging.getLogger(__name__)


class GraphComposer:
    """Build graph topology from blocks and deployment topology"""
    
    def compose(
        self,
        blocks: List[BlockDefinition],
        deployment_topology: DeploymentTopology,
        topology_constraints: Optional[List[Dict]] = None
    ) -> GraphTopologyJSON:
        """
        Compose a graph from blocks and topology.
        
        Args:
            blocks: List of block definitions
            deployment_topology: Deployment topology metadata
            topology_constraints: Optional topology constraints
            
        Returns:
            GraphTopologyJSON with nodes and edges
        """
        logger.info(f"Composing graph from {len(blocks)} blocks")
        
        nodes = []
        edges = []
        node_counter = {}
        
        # Create external client node if public access
        has_public_access = any(b.category == "security" for b in blocks)
        if has_public_access:
            nodes.append(Node(
                id="client",
                type="external",
                category="external",
                data=NodeData(label="Client", description="End user / browser")
            ))
        
        # Create nodes from blocks
        for block in blocks:
            category = block.category
            node_counter[category] = node_counter.get(category, 0) + 1
            
            # Determine how many instances of this block
            num_instances = self._determine_instance_count(block, deployment_topology)
            
            for i in range(num_instances):
                region = deployment_topology.regions[i % len(deployment_topology.regions)]
                node_id = f"{block.block_id}_{i+1}" if num_instances > 1 else block.block_id
                
                # Determine node role
                role = None
                if num_instances > 1 and block.category == "data":
                    role = "primary" if i == 0 else "replica"
                
                node = Node(
                    id=node_id,
                    type=block.category,
                    category=block.category,
                    region=region,
                    capability_ref=block.block_id,
                    data=NodeData(
                        label=self._generate_label(block, i, num_instances),
                        description=f"{block.block_id} instance"
                    ),
                    config=self._generate_config(block, deployment_topology, role)
                )
                
                nodes.append(node)
        
        # Create edges based on block interfaces and layering
        edges = self._create_edges(nodes, blocks, has_public_access, deployment_topology)
        
        logger.info(f"Created graph with {len(nodes)} nodes and {len(edges)} edges")
        
        return GraphTopologyJSON(nodes=nodes, edges=edges)
    
    def _determine_instance_count(
        self,
        block: BlockDefinition,
        deployment_topology: DeploymentTopology
    ) -> int:
        """Determine how many instances of this block to create"""
        # Data blocks: one per region if multi-region
        if block.category == "data":
            if deployment_topology.replication_required:
                return len(deployment_topology.regions)
            return 1
        
        # Compute blocks: at least 2 for HA if multi_az
        if block.category == "compute":
            if deployment_topology.multi_az:
                return 2
            return 1
        
        # Other blocks: typically 1 instance
        return 1
    
    def _generate_label(
        self,
        block: BlockDefinition,
        instance_index: int,
        total_instances: int
    ) -> str:
        """Generate a human-readable label for the node"""
        category_labels = {
            "compute": "Application Servers",
            "data": "Database",
            "network": "API Gateway" if "api" in block.block_id else "Load Balancer",
            "security": "WAF" if "waf" in block.block_id else "Key Management",
            "cache": "Cache",
            "storage": "Object Storage",
            "messaging": "Event Streaming",
            "observability": "Logging" if "logging" in block.block_id else "Monitoring"
        }
        
        base_label = category_labels.get(block.category, block.category.title())
        
        if total_instances > 1:
            if block.category == "data":
                return f"{'Primary' if instance_index == 0 else 'Replica'} {base_label}"
            else:
                return f"{base_label} {instance_index + 1}"
        
        return base_label
    
    def _generate_config(
        self,
        block: BlockDefinition,
        deployment_topology: DeploymentTopology,
        role: Optional[str] = None
    ) -> NodeConfig:
        """Generate configuration for a node"""
        config = NodeConfig()
        
        # Set basic defaults from resource benchmarks
        if block.resource_benchmarks:
            config.cpu_count = block.resource_benchmarks.min_cpu
            config.ram_gb = block.resource_benchmarks.min_ram_gb
            config.disk_gb = block.resource_benchmarks.disk_gb_default
        
        # Compute-specific config
        if block.category == "compute":
            config.scale_type = "horizontal"
            config.min_instances = 2 if deployment_topology.multi_az else 1
            config.max_instances = 10
        
        # Data-specific config
        if block.category == "data":
            config.public_access = False
            config.multi_az = deployment_topology.multi_az
            if role:
                config.replication_role = role
        
        return config
    
    def _create_edges(
        self,
        nodes: List[Node],
        blocks: List[BlockDefinition],
        has_public_access: bool,
        deployment_topology: DeploymentTopology
    ) -> List[Edge]:
        """Create edges based on layering and interfaces"""
        edges = []
        edge_counter = 0
        
        # Build node lookup
        nodes_by_category = {}
        for node in nodes:
            if node.category not in nodes_by_category:
                nodes_by_category[node.category] = []
            nodes_by_category[node.category].append(node)
        
        # Standard layering: client → waf → api_gateway → compute → data/cache
        if has_public_access and "client" in [n.id for n in nodes]:
            # Client → WAF
            waf_nodes = nodes_by_category.get("security", [])
            for waf in waf_nodes:
                if "waf" in waf.capability_ref:
                    edges.append(Edge(
                        id=f"e{edge_counter}",
                        from_node="client",
                        to=waf.id,
                        protocol="https",
                        type="traffic"
                    ))
                    edge_counter += 1
                    
                    # WAF → API Gateway
                    api_gw_nodes = nodes_by_category.get("network", [])
                    for api_gw in api_gw_nodes:
                        if "api" in api_gw.capability_ref:
                            edges.append(Edge(
                                id=f"e{edge_counter}",
                                from_node=waf.id,
                                to=api_gw.id,
                                protocol="https",
                                type="traffic"
                            ))
                            edge_counter += 1
                            
                            # API Gateway → Compute
                            compute_nodes = nodes_by_category.get("compute", [])
                            for compute in compute_nodes:
                                edges.append(Edge(
                                    id=f"e{edge_counter}",
                                    from_node=api_gw.id,
                                    to=compute.id,
                                    protocol="http",
                                    type="traffic"
                                ))
                                edge_counter += 1
        
        # Compute → Data
        compute_nodes = nodes_by_category.get("compute", [])
        data_nodes = nodes_by_category.get("data", [])
        for compute in compute_nodes:
            for data in data_nodes:
                if data.config and data.config.replication_role == "primary":
                    edges.append(Edge(
                        id=f"e{edge_counter}",
                        from_node=compute.id,
                        to=data.id,
                        protocol="tcp",
                        type="data"
                    ))
                    edge_counter += 1
                elif not data.config or not data.config.replication_role:
                    edges.append(Edge(
                        id=f"e{edge_counter}",
                        from_node=compute.id,
                        to=data.id,
                        protocol="tcp",
                        type="data"
                    ))
                    edge_counter += 1
        
        # Compute → Cache
        cache_nodes = nodes_by_category.get("cache", [])
        for compute in compute_nodes:
            for cache in cache_nodes:
                edges.append(Edge(
                    id=f"e{edge_counter}",
                    from_node=compute.id,
                    to=cache.id,
                    protocol="tcp",
                    type="data"
                ))
                edge_counter += 1
        
        # Compute → Messaging
        messaging_nodes = nodes_by_category.get("messaging", [])
        for compute in compute_nodes:
            for messaging in messaging_nodes:
                edges.append(Edge(
                    id=f"e{edge_counter}",
                    from_node=compute.id,
                    to=messaging.id,
                    protocol="tcp",
                    type="data"
                ))
                edge_counter += 1
        
        # Data replication edges
        if deployment_topology.replication_required:
            primary_data = [n for n in data_nodes if n.config and n.config.replication_role == "primary"]
            replica_data = [n for n in data_nodes if n.config and n.config.replication_role == "replica"]
            
            for primary in primary_data:
                for replica in replica_data:
                    edges.append(Edge(
                        id=f"e{edge_counter}",
                        from_node=primary.id,
                        to=replica.id,
                        protocol="replication",
                        type="replication",
                        replication_mode="active_active"
                    ))
                    edge_counter += 1
        
        return edges
