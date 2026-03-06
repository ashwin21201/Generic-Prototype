"""API v1 router: mounts all sub-routers under API_V1_PREFIX."""
from fastapi import APIRouter
from api.v1 import (
    intent_schema,
    intent_builder,
    blocks as blocks_router,
    resource_sizing,
    impact_analysis,
    governance,
    policy as policy_router,
    topology_generation,
    topology_editing,
    diagram as diagram_router,
)

api_router = APIRouter()

api_router.include_router(intent_schema.router, prefix="/intent-schema", tags=["intent-schema"])
api_router.include_router(intent_builder.router, prefix="/intent-builder", tags=["intent-builder"])
api_router.include_router(blocks_router.router, prefix="/blocks", tags=["blocks"])
api_router.include_router(resource_sizing.router, prefix="/resource-sizing", tags=["resource-sizing"])
api_router.include_router(impact_analysis.router, prefix="/impact-analysis", tags=["impact-analysis"])
api_router.include_router(governance.router, prefix="/governance", tags=["governance"])
api_router.include_router(policy_router.router, prefix="/policies", tags=["policies"])
api_router.include_router(topology_generation.router, prefix="/topologies", tags=["topologies"])
api_router.include_router(topology_editing.router, prefix="/topologies", tags=["topology-editing"])
api_router.include_router(diagram_router.router, prefix="/diagram", tags=["diagram"])
