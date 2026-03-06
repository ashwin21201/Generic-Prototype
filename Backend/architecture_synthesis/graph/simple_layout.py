"""
Layout engine for architecture graphs with VPC/subnet support.
Arranges nodes in a left-to-right layered layout with container hierarchies.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Layer order: external → edge → application → integration → data → operations
LAYER_ORDER = ["external", "edge", "application", "integration", "data", "operations"]

# Node dimensions
NODE_WIDTH = 200
NODE_HEIGHT = 100
LAYER_GAP_X = 250  # Horizontal gap between layers
NODE_GAP_Y = 150   # Vertical gap between nodes in same layer

# Container dimensions and padding
SUBNET_PADDING = 50
VPC_PADDING = 80


def apply_simple_layout(graph_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a simple left-to-right layered layout to the graph.
    Handles VPC and subnet containers automatically.
    
    Args:
        graph_dict: Graph dictionary with nodes and edges
        
    Returns:
        Updated graph with positions and sizes added to all nodes
    """
    nodes = graph_dict.get("nodes", [])
    
    if not nodes:
        return graph_dict
    
    # Separate containers from regular nodes
    vpc_node = None
    subnet_nodes = {}
    regular_nodes = []
    
    for node in nodes:
        node_id = node.get("id", "")
        node_type = node.get("type", "")
        
        if node_id.startswith("vpc-"):
            vpc_node = node
        elif node_id.startswith("subnet-"):
            subnet_nodes[node_id] = node
        elif node_type != "group":
            regular_nodes.append(node)
    
    # Group regular nodes by layer
    by_layer = {layer: [] for layer in LAYER_ORDER}
    no_layer = []
    
    for node in regular_nodes:
        layer = node.get("solution_layer", "").lower()
        category = node.get("category", "").lower()
        
        # Determine layer
        if category == "external":
            layer = "external"
        elif not layer:
            # Fallback based on category
            if category in ("security", "network"):
                layer = "edge"
            elif category == "compute":
                layer = "application"
            elif category in ("messaging", "cache"):
                layer = "integration"
            elif category in ("data", "storage"):
                layer = "data"
            elif category == "observability":
                layer = "operations"
            else:
                no_layer.append(node)
                continue
        
        if layer in by_layer:
            by_layer[layer].append(node)
        else:
            no_layer.append(node)
    
    # Position regular nodes layer by layer
    x_pos = 100 + (VPC_PADDING if vpc_node else 0)  # Start x position (with VPC padding)
    
    for layer in LAYER_ORDER:
        layer_nodes = by_layer[layer]
        
        if not layer_nodes:
            continue
        
        # Sort by flow_stage if available, then by priority
        layer_nodes.sort(key=lambda n: (
            n.get("flow_stage", 999),
            -n.get("priority", 50),
            n.get("id", "")
        ))
        
        # Calculate starting y to center the column
        total_height = len(layer_nodes) * NODE_HEIGHT + (len(layer_nodes) - 1) * NODE_GAP_Y
        y_pos = max(100 + (VPC_PADDING if vpc_node else 0), (800 - total_height) // 2)
        
        # Position each node
        for node in layer_nodes:
            # If node has a parent subnet, position is relative to subnet
            parent = node.get("parent_node")
            if parent and parent in subnet_nodes:
                node["position"] = {
                    "x": float(x_pos - (VPC_PADDING / 2)),  # Relative to subnet
                    "y": float(y_pos - (VPC_PADDING / 2))
                }
            else:
                node["position"] = {
                    "x": float(x_pos),
                    "y": float(y_pos)
                }
            y_pos += NODE_HEIGHT + NODE_GAP_Y
        
        x_pos += NODE_WIDTH + LAYER_GAP_X
    
    # Position nodes without a layer
    if no_layer:
        y_pos = 100
        for node in no_layer:
            node["position"] = {
                "x": float(x_pos),
                "y": float(y_pos)
            }
            y_pos += NODE_HEIGHT + NODE_GAP_Y
    
    # Calculate subnet container sizes and positions
    if subnet_nodes:
        for subnet_id, subnet in subnet_nodes.items():
            # Find all nodes in this subnet
            subnet_children = [n for n in regular_nodes if n.get("parent_node") == subnet_id]
            
            if subnet_children:
                # Calculate bounding box
                min_x = min(n["position"]["x"] for n in subnet_children)
                max_x = max(n["position"]["x"] + NODE_WIDTH for n in subnet_children)
                min_y = min(n["position"]["y"] for n in subnet_children)
                max_y = max(n["position"]["y"] + NODE_HEIGHT for n in subnet_children)
                
                # Position subnet at top-left of its children (with padding)
                subnet["position"] = {
                    "x": float(min_x - SUBNET_PADDING),
                    "y": float(min_y - SUBNET_PADDING)
                }
                
                # Set subnet size
                subnet["style"] = {
                    "width": float(max_x - min_x + 2 * SUBNET_PADDING),
                    "height": float(max_y - min_y + 2 * SUBNET_PADDING)
                }
    
    # Calculate VPC container size and position
    if vpc_node:
        # Find all nodes in VPC (subnets + their children)
        vpc_children = list(subnet_nodes.values()) + regular_nodes
        
        if vpc_children:
            # Calculate bounding box
            min_x = min(n["position"]["x"] for n in vpc_children)
            max_x = max(
                n["position"]["x"] + n.get("style", {}).get("width", NODE_WIDTH)
                for n in vpc_children
            )
            min_y = min(n["position"]["y"] for n in vpc_children)
            max_y = max(
                n["position"]["y"] + n.get("style", {}).get("height", NODE_HEIGHT)
                for n in vpc_children
            )
            
            # Position VPC at top-left (with padding)
            vpc_node["position"] = {
                "x": float(min_x - VPC_PADDING),
                "y": float(min_y - VPC_PADDING)
            }
            
            # Set VPC size
            vpc_node["style"] = {
                "width": float(max_x - min_x + 2 * VPC_PADDING),
                "height": float(max_y - min_y + 2 * VPC_PADDING)
            }
    
    logger.info(f"Applied layout to {len(nodes)} nodes ({len(subnet_nodes)} subnets, {'1 VPC' if vpc_node else 'no VPC'})")
    
    return graph_dict
