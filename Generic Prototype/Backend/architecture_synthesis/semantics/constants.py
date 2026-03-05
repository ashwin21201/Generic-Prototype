"""
Semantic mapping constants for render-ready diagram nodes.
Drives layout (flow_stage, placement_type) and visual grammar (shape, priority).
"""

# Category → Solution Layer (vertical ordering of architecture tiers)
CATEGORY_TO_LAYER = {
    "external": "external",
    "security": "edge",
    "network": "edge",
    "compute": "application",
    "messaging": "integration",
    "cache": "integration",
    "data": "data",
    "storage": "data",
    "observability": "operations",
    "data_processing": "data",
    "container": "infrastructure",
}

# Category → Network Zone (subnet placement)
CATEGORY_TO_ZONE = {
    "external": "external",
    "security": "edge",
    "network": "edge",
    "compute": "compute",
    "messaging": "compute",
    "cache": "compute",
    "data": "data_ops",
    "storage": "data_ops",
    "observability": "data_ops",
    "data_processing": "data_ops",
    "container": "infrastructure",
}

# Capability (block_id) → Semantic Role (layout behavior)
CAPABILITY_ROLE_MAP = {
    "waf_layer": "ingress_security",
    "api_gateway": "ingress_gateway",
    "api_gateway_": "ingress_gateway",
    "load_balancer": "ingress_gateway",
    "cdn_layer": "ingress_gateway",
    "microservices_compute": "application_service",
    "serverless_compute": "application_service",
    "container_orchestration": "application_service",
    "batch_processing_compute": "application_service",
    "gpu_compute": "application_service",
    "event_streaming_layer": "integration_bus",
    "message_queue": "integration_bus",
    "pub_sub_messaging": "integration_bus",
    "distributed_cache": "integration_bus",
    "managed_nosql_db": "primary_data",
    "managed_relational_db": "primary_data",
    "data_warehouse": "primary_data",
    "time_series_database": "primary_data",
    "graph_database": "primary_data",
    "object_storage": "primary_data",
    "block_storage": "primary_data",
    "archive_storage": "primary_data",
    "centralized_logging": "observability",
    "monitoring_and_alerting": "observability",
    "key_management_service": "security_support",
    "secrets_manager": "security_support",
    "identity_provider": "security_support",
    "network_firewall": "ingress_security",
    "service_mesh": "integration_bus",
    "stream_processing": "data_processing",
    "etl_pipeline": "data_processing",
}

# Semantic Role → Placement Type (traffic_path = center, side = left/right)
ROLE_PLACEMENT = {
    "ingress_security": "traffic_path",
    "ingress_gateway": "traffic_path",
    "application_service": "traffic_path",
    "primary_data": "data_path",
    "data_processing": "data_path",
    "integration_bus": "side",
    "observability": "side",
    "security_support": "side",
}

# Flow stage for vertical ordering (main path)
FLOW_STAGE = {
    "external": 0,
    "ingress_security": 1,
    "ingress_gateway": 2,
    "application_service": 3,
    "integration_bus": 4,
    "primary_data": 5,
    "data_processing": 5,
    "observability": 6,
    "security_support": 1,  # same tier as edge but placement_type=side
}

# Category → Visual shape (AWS-style)
CATEGORY_SHAPES = {
    "external": "cloud",
    "network": "rectangle",
    "security": "shield",
    "compute": "rectangle",
    "messaging": "hexagon",
    "cache": "rectangle",
    "data": "cylinder",
    "storage": "cylinder",
    "observability": "circle",
    "data_processing": "rectangle",
}

# Semantic role → Visual priority (higher = more prominent/centered)
ROLE_PRIORITY = {
    "ingress_gateway": 100,
    "application_service": 90,
    "primary_data": 80,
    "integration_bus": 60,
    "observability": 40,
    "security_support": 30,
    "ingress_security": 95,
    "data_processing": 70,
}
