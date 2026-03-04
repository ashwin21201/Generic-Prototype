# Resolved Architecture Structure Update

## Summary
Updated the resolved architecture structure to match the plan document (Section 15.7) by embedding resolved products directly within graph nodes instead of maintaining them as a separate array.

## Changes Made

### 1. Schema Update (`product_schemas.py`)

**Before:**
```python
class ResolvedArchitectureJSON(BaseModel):
    architecture_id: str
    graph: Dict[str, Any]  # Separate graph
    resolved_products: List[ResolvedNode]  # Products as separate array
    estimated_monthly_cost_usd: float
```

**After:**
```python
class ResolvedArchitectureJSON(BaseModel):
    architecture_id: str
    graph: Dict[str, Any]  # Graph with products embedded in nodes
    estimated_monthly_cost_usd: float
```

### 2. Product Resolver Update (`product_resolver.py`)

**Key Changes:**
- Products are now embedded directly in each node's `resolved_products` field
- The graph structure now contains nodes with products included
- Matches the plan document structure exactly

**New Structure:**
```json
{
  "architecture_id": "arch_001",
  "graph": {
    "nodes": [
      {
        "id": "waf_1",
        "type": "security",
        "capability_ref": "waf_layer",
        "resolved_products": [
          {
            "provider": "your_cloud",
            "product_name": "YC WAF",
            "product_id": "yc-waf",
            "recommended": true
          },
          {
            "provider": "aws",
            "product_name": "AWS WAF",
            "product_id": "aws-waf",
            "recommended": false
          }
        ]
      }
    ],
    "edges": [...]
  },
  "estimated_monthly_cost_usd": 4300.0
}
```

### 3. New API Endpoint (`app.py`)

Added new endpoint for accessing the resolved graph:

```python
@app.get("/api/architecture/graph-with-products")
def get_architecture_graph_with_products():
    """
    Get architecture graph with resolved products embedded in nodes.
    This matches the plan document structure (Section 15.7).
    """
```

## API Endpoints Summary

| Endpoint | Description | Returns |
|----------|-------------|---------|
| `GET /api/architecture/graph` | Base graph without products | Nodes + edges (no products) |
| `GET /api/architecture/graph-with-products` | Graph with products embedded | Nodes (with products) + edges |
| `GET /api/architecture/products` | Full resolved architecture | Complete resolved architecture JSON |

## Benefits

1. **Plan Compliance**: Now matches the architecture plan document structure exactly (Section 15.7, lines 973-1045)
2. **Simpler Frontend Integration**: Products are directly accessible within each node
3. **Better Data Locality**: Product information is co-located with node data
4. **Cleaner API**: Single graph structure contains all necessary information

## Migration Notes

- The synthesize endpoint still returns the full structure with all components
- The `resolved_architecture` section now has products embedded in the graph
- Frontend code should use `/api/architecture/graph-with-products` for diagram rendering with product hover details
- The base `/api/architecture/graph` endpoint remains for cases where product info is not needed

## Testing

After restarting the server, test by:
1. Running the questionnaire to generate intent JSON
2. Calling `/api/synthesize`
3. Checking the `resolved_architecture.graph.nodes[].resolved_products` structure
4. Verifying the new `/api/architecture/graph-with-products` endpoint

## Alignment with Plan Document

✅ **Section 15.7** (Resolved Architecture JSON): Structure now matches exactly
✅ **Section 16.3.7** (Product Resolution Engine): Implementation follows the interface contract
✅ **Section 2** (All JSON Types Overview): Resolved Architecture JSON (#7) now correct
