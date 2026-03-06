import logging
from typing import Dict, List, Optional
from .product_schemas import (
    ResolvedArchitectureJSON, ResolvedNode, ResolvedProduct, Product
)
from .product_catalog import ProductCatalogStore
from ..graph.graph_schemas import GraphTopologyJSON
from ..blocks.block_registry import BlockRegistryStore
from ..graph.simple_layout import apply_simple_layout

logger = logging.getLogger(__name__)


class ProductResolutionEngine:
    """Map graph nodes to actual cloud products"""
    
    def __init__(
        self,
        product_catalog_store: ProductCatalogStore,
        block_registry: BlockRegistryStore
    ):
        self.product_catalog = product_catalog_store
        self.block_registry = block_registry
    
    def resolve(
        self,
        graph: GraphTopologyJSON,
        architecture_id: str,
        preferences: Optional[Dict] = None
    ) -> ResolvedArchitectureJSON:
        """
        Resolve products for each node in the graph.
        Embeds resolved_products directly within each node (matching plan document).
        
        Args:
            graph: Graph topology
            architecture_id: Architecture ID
            preferences: Deployment preferences (cloud provider preference, etc.)
            
        Returns:
            ResolvedArchitectureJSON with products embedded in graph nodes
        """
        logger.info(f"Resolving products for {len(graph.nodes)} nodes")
        
        preferred_provider = None
        if preferences:
            preferred_provider = preferences.get("cloud_provider_preference", "").lower()
        
        total_cost = 0.0
        
        # Create a modified graph with products embedded in nodes
        graph_dict = graph.dict()
        resolved_nodes = []
        
        for node_dict in graph_dict["nodes"]:
            # Skip external nodes
            if node_dict.get("category") == "external":
                resolved_nodes.append(node_dict)
                continue
            
            # Get block definition to understand capabilities
            block = None
            capability_ref = node_dict.get("capability_ref")
            if capability_ref:
                block = self.block_registry.get_block(capability_ref)
            
            # Find matching products
            # Create a temporary node object for matching
            from ..graph.graph_schemas import Node, NodeData
            temp_node = Node(
                id=node_dict["id"],
                type=node_dict["type"],
                category=node_dict["category"],
                region=node_dict.get("region"),
                capability_ref=capability_ref,
                data=NodeData(**node_dict["data"]),
                config=node_dict.get("config")
            )
            
            products = self._find_matching_products(temp_node, block)
            
            # Rank products by preference
            ranked_products = self._rank_products(products, preferred_provider)
            
            # Create resolved products
            resolved_products = []
            for i, product in enumerate(ranked_products[:3]):  # Top 3 products
                resolved_products.append({
                    "provider": self._get_provider_for_product(product),
                    "product_name": product.product_name,
                    "product_id": product.product_id,
                    "recommended": (i == 0)  # First one is recommended
                })
                
                if i == 0:
                    total_cost += product.monthly_cost_usd_estimate
            
            # Embed resolved_products in the node
            node_dict["resolved_products"] = resolved_products
            resolved_nodes.append(node_dict)
        
        # Update graph with resolved nodes
        graph_dict["nodes"] = resolved_nodes
        
        # Apply layout to position nodes
        logger.info("Applying layout to graph...")
        graph_dict = apply_simple_layout(graph_dict)
        
        logger.info(f"Resolved {len(resolved_nodes)} nodes with products and applied layout")
        
        return ResolvedArchitectureJSON(
            architecture_id=architecture_id,
            graph=graph_dict,
            estimated_monthly_cost_usd=round(total_cost, 2)
        )
    
    def _find_matching_products(
        self,
        node,
        block
    ) -> List[Product]:
        """Find products that match the node's requirements"""
        products = []
        
        # Try to match by category first
        if node.category:
            products = self.product_catalog.find_products_by_category(node.category)
        
        # If we have block capabilities, filter by capabilities
        if block and block.capabilities_provided:
            matching_products = []
            for product in products:
                # Check if product has required capabilities
                matches = True
                for cap, required in block.capabilities_provided.items():
                    if required and not product.capabilities.get(cap):
                        matches = False
                        break
                
                if matches:
                    matching_products.append(product)
            
            if matching_products:
                products = matching_products
        
        return products
    
    def _rank_products(
        self,
        products: List[Product],
        preferred_provider: Optional[str]
    ) -> List[Product]:
        """Rank products by preference and suitability"""
        if not products:
            return []
        
        # Separate by provider
        preferred = []
        others = []
        
        for product in products:
            provider = self._get_provider_for_product(product)
            if preferred_provider and provider == preferred_provider:
                preferred.append(product)
            else:
                others.append(product)
        
        # Sort by cost (lower is better)
        preferred.sort(key=lambda p: p.monthly_cost_usd_estimate)
        others.sort(key=lambda p: p.monthly_cost_usd_estimate)
        
        # Preferred products first, then others
        return preferred + others
    
    def _get_provider_for_product(self, product: Product) -> str:
        """Get provider name for a product"""
        # Look through catalogs to find which one contains this product
        for provider, catalog in self.product_catalog.get_all_catalogs().items():
            if product in catalog.products:
                return provider
        return "unknown"
