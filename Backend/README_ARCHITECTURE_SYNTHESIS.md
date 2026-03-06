# Architecture Synthesis Platform

This is a complete implementation of the Architecture Synthesis Platform based on the ARCHITECTURE_SYNTHESIS_PLAN document.

## Overview

The platform takes a Master Request JSON (user intent) and automatically generates a compliant, optimized cloud architecture with the following pipeline:

```
Master Request JSON
  ↓
Policy Loading & Merging (BFSI, Regional, Org)
  ↓
Block Selection (Compute, Data, Network, Security, etc.)
  ↓
Compatibility Resolution (Dependencies & Conflicts)
  ↓
Graph Composition (Nodes & Edges)
  ↓
Compliance Evaluation (Rules & Violations)
  ↓
Product Resolution (AWS, Your Cloud, etc.)
  ↓
Architecture Diagram + Metadata
```

## Directory Structure

```
Backend/
├── architecture_synthesis/
│   ├── policy/              # Policy loading and merging
│   │   ├── policy_schemas.py
│   │   ├── policy_loader.py
│   │   └── policy_merger.py
│   ├── blocks/              # Block selection and compatibility
│   │   ├── block_schemas.py
│   │   ├── block_registry.py
│   │   ├── block_selector.py
│   │   └── compatibility_resolver.py
│   ├── graph/               # Graph composition
│   │   ├── graph_schemas.py
│   │   └── graph_composer.py
│   ├── compliance/          # Compliance evaluation
│   │   ├── compliance_schemas.py
│   │   └── rule_engine.py
│   └── resolution/          # Product resolution
│       ├── product_schemas.py
│       ├── product_catalog.py
│       └── product_resolver.py
├── policies/
│   └── sectors/
│       └── bfsi.json        # BFSI sector policy
├── blocks/
│   └── block_registry.json  # Architecture building blocks
├── products/
│   ├── aws_catalog.json     # AWS product catalog
│   └── your_cloud_catalog.json
├── outputs/
│   └── architecture_intent_*.json
├── app.py                   # FastAPI application
└── test_synthesis.py        # Test script
```

## Components

### 1. Policy Module
- **PolicyLoader**: Loads policy JSON files by sector/region/org
- **PolicyMerger**: Merges multiple policies with conflict resolution
- **Schemas**: PolicyJSON, Rule, MergedPolicy

### 2. Block Selection Module
- **BlockRegistryStore**: Manages architecture building blocks
- **BlockSelector**: Maps intent + policy → blocks
- **CompatibilityResolver**: Resolves dependencies and conflicts

### 3. Graph Composition Module
- **GraphComposer**: Builds nodes and edges from blocks
- Creates deployment topology (regions, replication, HA)

### 4. Compliance Module
- **RuleEvaluationEngine**: Evaluates policy rules against graph
- Rule types: capability, deployment, topology, relationship, quantitative
- Generates compliance reports with violations and risk scores

### 5. Product Resolution Module
- **ProductCatalogStore**: Manages product catalogs (AWS, Your Cloud, etc.)
- **ProductResolutionEngine**: Maps blocks to actual cloud products
- Supports provider preferences and cost estimation

## API Endpoints

### POST /api/synthesize
Synthesizes architecture from Master Request JSON.

**Request**: No body required (uses stored Master Request JSON)

**Response**:
```json
{
  "architecture_id": "arch_abc123",
  "selected_architecture": {
    "selected_blocks": [...],
    "deployment_topology": {...},
    "scoring_summary": {...},
    "estimated_monthly_cost_usd": 5000
  },
  "graph": {
    "nodes": [...],
    "edges": [...]
  },
  "compliance_report": {
    "compliance_status": "compliant",
    "risk_score": 0.0,
    "checks": [...],
    "violations": []
  },
  "resolved_architecture": {
    "resolved_products": [...]
  },
  "warnings": []
}
```

## Configuration Files

### BFSI Policy (policies/sectors/bfsi.json)
- Encryption at rest/transit required
- Multi-region deployment (≥2 regions)
- No public database access
- WAF required for public APIs
- Mandatory blocks: centralized_logging, key_management_service

### Block Registry (blocks/block_registry.json)
Available blocks:
- **Compute**: microservices_compute
- **Data**: managed_nosql_db, managed_relational_db
- **Network**: api_gateway, load_balancer
- **Security**: waf_layer, key_management_service
- **Cache**: distributed_cache
- **Storage**: object_storage
- **Messaging**: event_streaming_layer
- **Observability**: centralized_logging, monitoring_and_alerting

Each block includes:
- Capabilities provided
- Interfaces (ingress/egress)
- Dependencies and conflicts
- Performance/cost profiles
- Resource benchmarks (CPU, RAM, disk)
- Compliance tags

### Product Catalogs
- **AWS**: EC2, RDS, DynamoDB, MSK, WAF, API Gateway, etc.
- **Your Cloud**: YC VM, YC PostgreSQL, YC WAF, etc.

## Testing

Run the test script:
```bash
cd Backend
python test_synthesis.py
```

This will:
1. Load the Master Request JSON
2. Execute the full synthesis pipeline
3. Display results for each step
4. Show final architecture summary

## Usage Example

1. **Complete the questionnaire** to generate Master Request JSON
2. **Call the synthesis endpoint**:
   ```bash
   curl -X POST http://localhost:8000/api/synthesize
   ```
3. **Receive complete architecture** with:
   - Selected blocks
   - Graph topology (nodes + edges)
   - Compliance report
   - Product mappings (AWS, Your Cloud)
   - Cost estimate

## Key Features

✅ **Policy-Aware**: Automatically applies BFSI compliance rules  
✅ **Multi-Region**: Supports active-active replication  
✅ **HA/DR**: Configures high availability and disaster recovery  
✅ **Cost Optimization**: Estimates monthly costs  
✅ **Provider Agnostic**: Maps to AWS, Your Cloud, or others  
✅ **Compliance Validation**: Checks rules and reports violations  
✅ **Auto-Remediation**: Can automatically fix violations (configurable)  

## Next Steps

1. **Deploy Layer**: Implement execution plan builder and deployment orchestrator
2. **Diagram Renderer**: Convert graph to visual diagram (Cytoscape/React Flow)
3. **Resource Sizing**: Implement formula-based CPU/RAM/disk calculation
4. **Advanced Compliance**: Add more rule evaluators and auto-remediation
5. **UI Integration**: Connect to frontend for visualization

## Architecture Flow

```
User Intent (Questionnaire)
  ↓
Master Request JSON
  ↓
[Policy Engine] → Load BFSI policy → Merge rules
  ↓
[Block Selector] → Determine categories → Match capabilities → Score blocks
  ↓
[Compatibility Resolver] → Add dependencies → Remove conflicts
  ↓
[Graph Composer] → Create nodes → Create edges → Apply topology
  ↓
[Compliance Engine] → Evaluate rules → Check patterns → Calculate risk
  ↓
[Product Resolver] → Match capabilities → Rank by preference → Map products
  ↓
Final Architecture (Graph + Products + Compliance)
```

## Notes

- The implementation follows the document's Section 16 (Low Level Design)
- All JSON schemas match the document's specifications
- The pipeline is modular and extensible
- Each component can be tested independently
- Logging is enabled for debugging and audit trails
