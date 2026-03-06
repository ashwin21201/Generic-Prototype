# Configurator Layer Alignment — Document vs Code

This document maps the **Intent-Based Architecture — Configurator Layer (Addendum)** to the current codebase: what is implemented, what is partially done, and what remains.

---

## 1. North Star and Problem Statement

| Document | Current code |
|----------|--------------|
| **Problem**: Hardcoded coupling between Intent JSON field names, Block category dispatch, Resource Sizing formulas, and Compliance. Any JSON change requires code change. | **Reality**: Block selector and deployment topology still read intent via hardcoded paths (`functional_requirements`, `non_functional_requirements`, etc.). Sizing now supports **optional** formula-based path when blocks declare `intent_field_mappings` and `sizing_formulas`. |
| **Solution**: Configurator Layer — meta-configuration; runtime is a generic evaluator. | **Reality**: First step in place: blocks can declare field mappings and sizing formulas; Field Resolver + Formula Engine evaluate when present. Full config-driven category derivation and schema registry are not yet in code. |

---

## 2. Intent and Intent Schema

| Document (§4, §11) | Current code |
|--------------------|--------------|
| Intent Schema Registry with versioning; Field Registry; Impact Analysis on field change. | **Not implemented.** No schema registry, no versioning, no impact analyzer. |
| Intent fields drive Category Derivation and Capability Requirements (e.g. `application_type`, `expected_rps_peak`, `optimization_priorities`). | Intent is the **Master Request JSON** with `functional_requirements`, `non_functional_requirements`, `data_requirements`, `security_requirements`, `deployment_preferences`, `optimization_priorities`. Block selector uses these paths **in code**. |
| Intent JSON Builder (chatbot) → rich Intent JSON (§19). | Chat + structured prompt in `app.py` produce the same Master Request structure; no separate Intent Builder service or completeness scorer. |

**Implemented:**  
- Intent is passed through the pipeline and into **graph composition** as `intent` for formula-based sizing.  
- **Field resolution** uses dot-path into current intent (e.g. `non_functional_requirements.expected_rps_peak` → `rps`) when blocks declare `intent_field_mappings`.

---

## 3. Blocks and Block Registry

| Document (§5, §17) | Current code |
|--------------------|--------------|
| Blocks declare **Field Mappings**: `intent_path` → `maps_to` (variable name). | **Implemented.** `BlockDefinition` has `intent_field_mappings: List[IntentFieldMapping]`. `microservices_compute` in `block_registry.json` has example mappings. |
| Blocks declare **Sizing Formulas** as expression strings (e.g. `cpu_count: "max(min_cpu, ceil(rps / rps_per_cpu))"`). | **Implemented.** `BlockDefinition` has `sizing_formulas: Dict[str, str]`. Same block has `cpu_count` and `ram_gb` formulas. |
| Validation: field paths exist in Intent Schema; formula variables resolve from mappings. | **Not implemented.** No Intent Schema to validate against; formula variables come from mappings + benchmarks only. |
| Block Registry Manager UI, versioning, audit. | **Not implemented.** Registry is file-based (`blocks/block_registry.json`), no UI or versioning. |

**Implemented:**  
- Block schema and registry support **optional** `intent_field_mappings` and `sizing_formulas`.  
- Existing blocks without these fields continue to use benchmark defaults only.

---

## 4. Formula Engine and Rule Engine (§6)

| Document | Current code |
|----------|--------------|
| **Step 1 — Field Resolution**: Load block field mappings, resolve intent paths to local variables, add benchmark constants → variable context. | **Implemented.** `architecture_synthesis.engines.field_resolver.resolve_variable_context(intent, block)`. |
| **Step 2 — Formula Engine**: Parse and evaluate expression strings safely. | **Implemented.** `architecture_synthesis.engines.formula_engine.evaluate_sizing_formulas(formulas, variables)` using `simpleeval`. Supports `max`, `min`, `ceil`, `floor`, `round`. |
| **Step 3 — Rule Engine**: Declarative rules (max, min, clamp, intersect, enforce) on resource specs from policy. | **Partially.** Compliance evaluates **graph-level** rules (capability, deployment, topology, relationship). **Resource-level** constraint application (e.g. clamp `cpu_count` by policy min/max) is **not** implemented. |

---

## 5. Block Selection — 6 Dimensions (§11)

| Dimension | Document | Current code |
|-----------|----------|--------------|
| 1. Category Derivation | Intent signals → which categories needed. | **In code:** `_determine_categories(master_request)` using `functional_requirements`, `data_requirements`, `non_functional_requirements`, etc. |
| 2. Capability Requirements | Intent + policy → required capabilities per category. | **In code:** `_determine_required_capabilities(...)`. |
| 3. Block Filtering | Registry scan by category + capabilities. | **In code:** `_find_candidate_blocks(category, required_capabilities)`. |
| 4. Dependency Resolution | Selected blocks pull in required/optional dependencies. | **In code:** `CompatibilityResolver.resolve(selected_blocks)` adds missing dependencies. |
| 5. Scoring & Ranking | Optimization weights → best block per category. | **In code:** `_score_and_select(candidates, optimization_priorities)`. |
| 6. Policy Enforcement | Mandatory blocks, forbidden patterns, capability rules. | **In code:** Mandatory blocks added; compliance rule engine evaluates graph. |

**Gap:** Category derivation and capability rules are **hardcoded** (if/else on intent sections). Document expects these to be **config-driven** (e.g. from Intent Schema + Block Registry config). No config store or UI for that yet.

---

## 6. Topology — 4 Dimensions (§12)

| Dimension | Document | Current code |
|-----------|----------|--------------|
| 1. Node Creation | Selected blocks + intent (multi_region, horizontal_scaling, availability) → instances and regions. | **In code:** `GraphComposer._determine_instance_count`, regions from `DeploymentTopology`. |
| 2. Edge Resolution | Block interfaces (ingress/egress) + requires → edges. | **In code:** `_create_edges` uses layering and categories (client → WAF → API GW → compute → data/cache/messaging). |
| 3. Layering Rules | Convention + policy (e.g. network → security → api_gw → compute → data). | **In code:** Implicit in `_create_edges`. |
| 4. Topology Validation | Policy topology rules (no public DB, data residency, etc.). | **In code:** `RuleEvaluationEngine` evaluates topology/relationship rules on the graph. |

---

## 7. Resource Sizing

| Document | Current code |
|----------|--------------|
| Category Dispatcher + hardcoded calculators (Compute, Data, Cache, Storage) → **eliminated** by Formula Engine. | **No category dispatcher.** Sizing is either: (1) **formula-based** when block has `sizing_formulas` and intent is passed, or (2) **benchmark defaults** (min_cpu, min_ram_gb, disk_gb_default) from `resource_benchmarks`. |
| Formula expressions in config; safe evaluator. | **Implemented** for blocks that declare formulas; evaluator is `simpleeval`. |

---

## 8. Diagram-Ready JSON and Layout (§21, §22)

| Document | Current code |
|----------|--------------|
| Diagram-Ready JSON: containers, nodes, edges, layout hints, legend, views. | Graph has **nodes** and **edges**; layout engine adds **positions**, **parent_node** (VPC, subnets), **extent**. No separate “Diagram-Ready” envelope; frontend consumes `resolved_architecture.graph`. |
| Layout: LR (left-to-right); wrapping thresholds. | **Layout engine** does topological (DAG) layering and VPC/subnet grouping; direction is top-down flow. LR and wrapping thresholds from doc are not yet applied. |
| Frontend: thin transformer, ELK for layout. | Frontend uses ReactFlow; layout **positions** come from backend. No ELK on frontend. |

---

## 9. What Was Changed in This Pass

1. **Block schema** (`block_schemas.py`):  
   - `IntentFieldMapping` model.  
   - `BlockDefinition.intent_field_mappings`, `BlockDefinition.sizing_formulas`.

2. **Field Resolver** (`architecture_synthesis/engines/field_resolver.py`):  
   - `resolve_variable_context(intent, block)` from intent paths + benchmarks.

3. **Formula Engine** (`architecture_synthesis/engines/formula_engine.py`):  
   - `evaluate_sizing_formulas(formulas, variables)` using `simpleeval`.

4. **Graph Composer** (`graph_composer.py`):  
   - `compose(..., intent=...)`; `_generate_config(..., intent=...)` uses formula-based sizing when block has formulas and intent is provided.

5. **App pipeline** (`app.py`):  
   - Passes `master_request` as `intent` into `graph_composer.compose(...)`.

6. **Block registry** (`blocks/block_registry.json`):  
   - `microservices_compute` now has `intent_field_mappings` and `sizing_formulas` as examples.

7. **Dependency:**  
   - `simpleeval>=1.0.0` added to `requirements.txt`.

---

## 10. What Is Still Not in Code (Summary)

- Intent Schema Registry (versioned schema, field registry, impact analysis).  
- Config-driven category derivation and capability rules (no code change when intent shape changes).  
- Rule Engine application to **resource specs** (max/min/clamp from policy).  
- Configurator UI (Intent Schema Builder, Block Registry Manager, Policy Rule Manager).  
- Impact Analyzer, audit log, approval workflow, version rollback.  
- Diagram-Ready JSON envelope and LR layout/wrapping as per §21–22.  
- Async topology generation (e.g. Celery), job polling, universal response envelope.  
- Intent JSON Builder as a separate service with completeness scorer and “What We Understood” preview.  

These are the main items to add for full alignment with the Configurator Layer addendum.
