# Brainboard-Style Pipeline Additions

This document describes the extra pipeline steps added to align with Brainboard-style architecture diagram synthesis: pattern detection, semantic annotation, graph normalization, and layout strategy selection.

## Pipeline Order (Current)

1. Questionnaire → Intent JSON (LLM)
2. Policy Merge
3. Block Selection
4. **Architecture Pattern Detection** (new)
5. Compatibility Resolution
6. Graph Composer
7. Sizing Engine (inside composer)
8. Compliance Check
9. Product Resolver
10. **Semantic Graph Annotation** (new)
11. **Graph Normalization** (new, also inside layout)
12. **Layout Strategy Selection** (new)
13. Graph Layout Engine (uses semantic fields + strategy)
14. ReactFlow Rendering

## New Components

### 1. Architecture Pattern Detection (`pattern/architecture_pattern_detector.py`)

- **When:** After Block Selection, before Compatibility Resolution.
- **Input:** Selected block IDs, block registry.
- **Output:** `ArchitecturePattern(type, layout_strategy)`.
- **Logic:** Infers pattern from block categories/IDs (e.g. messaging + event_streaming → `event_driven`/radial; batch + storage → `data_pipeline`/horizontal; compute + gateway → `web_service`/layered_vertical).

### 2. Semantic Mapping Constants (`semantics/constants.py`)

- **CATEGORY_TO_LAYER:** Category → solution layer (external, edge, application, integration, data, operations).
- **CATEGORY_TO_ZONE:** Category → network zone (edge, compute, data_ops).
- **CAPABILITY_ROLE_MAP:** Block ID → semantic role (ingress_security, ingress_gateway, application_service, integration_bus, primary_data, observability, security_support).
- **ROLE_PLACEMENT:** Semantic role → placement type (traffic_path, data_path, side).
- **FLOW_STAGE:** Semantic role → vertical stage (0–6).
- **CATEGORY_SHAPES:** Category → shape (cloud, rectangle, shield, hexagon, cylinder, circle).
- **ROLE_PRIORITY:** Semantic role → visual priority (for ordering).

### 3. Graph Semantic Annotator (`semantics/graph_semantic_annotator.py`)

- **When:** After Product Resolution, before Layout.
- **Input:** Graph (nodes + edges).
- **Output:** Same graph with each node enriched with `semantic_role`, `solution_layer`, `network_zone`, `flow_stage`, `placement_type`, `shape`, `priority`.
- **Used by:** Layout engine (ordering, placement) and frontend (optional visual grammar).

### 4. Graph Normalizer (`graph/graph_normalizer.py`)

- **When:** Inside `apply_layout()` before layout runs.
- **Purpose:** Normalize edge keys (`from_node`, `to`) so layout and renderer see a consistent graph.

### 5. Layout Strategy Selector (`graph/layout_strategy_selector.py`)

- **When:** After Pattern Detection, value used at layout time.
- **Mapping:** `web_service` → layered_vertical, `event_driven` → radial, `data_pipeline` → horizontal, `serverless` → radial, `mesh` → force.
- **Current layout engine:** Implements layered_vertical (zone-based subnets + flow_stage/placement_type ordering). Other strategies can be added later (e.g. ELK).

### 6. Layout Engine Changes (`graph/layout_engine.py`)

- **`apply_layout(graph, layout_strategy="layered_vertical")`** now accepts an optional strategy and calls `normalize_graph` first.
- When nodes have **semantic fields** (`flow_stage`, `placement_type`, `semantic_role`), the engine uses them for layer and role (traffic_path vs support vs observability) and sorts by `_flow_stage_order_key` within each zone.
- Containers remain zone-based (Edge, Compute, Data & Ops); internal ordering and roles are driven by semantics.

## API Response Additions

The `/api/synthesize` result now includes:

- **`architecture_pattern`:** Detected pattern type (e.g. `web_service`).
- **`layout_strategy`:** Selected layout strategy (e.g. `layered_vertical`).

Graph nodes in `resolved_architecture.graph.nodes` include semantic fields for the frontend:

- `semantic_role`, `solution_layer`, `network_zone`, `flow_stage`, `placement_type`, `shape`, `priority`

The diagram page passes these through to ReactFlow node `data` for future shape/icon mapping.
