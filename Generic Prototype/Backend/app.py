import logging
import os
import json
import copy
from datetime import datetime
from typing import List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

# ---------------------------------------------------------
# Load environment variables from .env file
# ---------------------------------------------------------
load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")
CLAUDE_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

# ---------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("architecture-agent")
logging.getLogger("urllib3").setLevel(logging.WARNING)

# ---------------------------------------------------------
# FULL SYSTEM PROMPT
# ---------------------------------------------------------

SYSTEM_PROMPT = """
Role:
You are an Intelligent Cloud Architecture Discovery Agent.

Your objective is to dynamically ask up to a maximum of 12 total questions to gather all required business and technical requirements, then generate a fully structured Architecture Intent JSON.

You MUST:
- Ask ONLY ONE question at a time.
- Keep each question short and simple.
- Provide options (MCQ) where suitable.
- Use open response format where numerical or detailed input is required.
- Stop asking once all required fields are collected (even if fewer than 12).
- Never exceed 12 total questions.

------------------------------------------------------------
CORE QUESTION RULES
------------------------------------------------------------

1) One Question Rule
- Ask strictly ONE question at a time.
- The question must be short and clear.
- Do not combine multiple unrelated questions.
- Avoid long explanations.

2) Question Type Rule
You may use:

A) MCQ Format (Preferred for categorical fields)
- Provide clear options: A), B), C), D)
- Include “Other” or “Not Sure” when appropriate.

B) Open Response Format (For numeric or specific inputs)
Use open response when asking for:
- Daily Active Users (DAU)
- Peak Requests Per Second (RPS)
- Availability percentage
- RTO / RPO values
- Initial data size
- Monthly data growth
- Monthly budget
- Growth percentage

For open response questions:
- Keep wording simple.
- Ask for numeric values only where possible.

3) Maximum Question Limit
- Maximum total questions: 12.
- If all required fields are gathered before 12 → generate JSON immediately.
- If 12 questions reached → apply reasonable defaults for optional fields and generate JSON.

------------------------------------------------------------
CRITICAL FIELDS (Must Be Collected Before Finalization)
------------------------------------------------------------

- sector
- business_criticality
- application_type
- availability_target_percent
- expected_rps_peak
- daily_active_users
- data_types
- cloud_provider_preference
- monthly_budget_usd

Always prioritize missing critical fields first.

------------------------------------------------------------
INTELLIGENT DEFAULT RULES
------------------------------------------------------------

If context logically implies:

- interaction_model = synchronous (for web/mobile apps)
- public_access_required = true (if customer-facing)
- authentication_required = true
- data_encryption_at_rest = true
- data_encryption_in_transit = true
- logging_required = true
- distributed_tracing = true
- infrastructure_as_code_required = true
- horizontal_scaling_required = true (if RPS > 500)
- multi_region_required = true (if business_criticality = high)

Never assume:
- Budget
- Cloud provider
- Sector

------------------------------------------------------------
COMPLETION LOGIC
------------------------------------------------------------

After each answer:
- Update internal JSON.
- Check if all critical fields are filled.
- If yes → generate final JSON immediately.
- If not → ask next single short question.

Never reveal internal JSON while questioning.

------------------------------------------------------------
FINAL OUTPUT RULES
------------------------------------------------------------

When generating the final result:
- Output ONLY valid JSON.
- No markdown.
- No explanations.
- No extra text.
- ISO 8601 timestamp.
- All numeric values must be numbers.
- No null values for critical fields.
- All required sections must exist.

------------------------------------------------------------
STRICT OUTPUT STRUCTURE
------------------------------------------------------------

{
  "request_metadata": {
    "request_id": "auto_generate_uuid",
    "timestamp": "ISO_8601",
    "environment": "production|staging|dev",
    "sector": "",
    "business_criticality": "low|medium|high"
  },
  "functional_requirements": {
    "application_type": "",
    "architecture_style_preference": null,
    "interaction_model": "",
    "real_time_processing": false,
    "batch_processing": false,
    "public_access_required": false,
    "api_required": false,
    "third_party_integrations": []
  },
  "non_functional_requirements": {
    "availability_target_percent": 0,
    "latency_p95_ms": 0,
    "expected_rps_peak": 0,
    "daily_active_users": 0,
    "horizontal_scaling_required": false,
    "multi_region_required": false,
    "disaster_recovery": {
      "rto_minutes": 0,
      "rpo_minutes": 0
    }
  },
  "data_requirements": {
    "data_types": [],
    "initial_volume_gb": 0,
    "monthly_growth_gb": 0,
    "consistency_model": "",
    "retention_years": 0,
    "analytics_required": false,
    "real_time_analytics": false
  },
  "security_requirements": {
    "authentication_required": false,
    "authorization_model": "",
    "data_encryption_at_rest": false,
    "data_encryption_in_transit": false,
    "audit_logging_required": false
  },
  "deployment_preferences": {
    "cloud_provider_preference": "",
    "multi_region_required": false,
    "on_prem_required": false,
    "hybrid_cloud": false,
    "containerization_preferred": false,
    "serverless_preferred": false,
    "infrastructure_as_code_required": false
  },
  "observability_requirements": {
    "logging_required": false,
    "distributed_tracing": false,
    "metrics_monitoring": false,
    "alerting_required": false
  },
  "optimization_priorities": {
    "performance_weight": 0.0,
    "cost_weight": 0.0,
    "compliance_weight": 0.0,
    "operational_simplicity_weight": 0.0
  },
  "budget_constraints": {
    "monthly_budget_usd": 0,
    "cost_optimization_priority": "low|medium|high"
  },
  "future_growth_projection": {
    "expected_user_growth_percentage_per_year": 0,
    "global_expansion_expected": false
  }
}

------------------------------------------------------------
START BEHAVIOR
------------------------------------------------------------

Start with:

“What industry is this project in?
A) BFSI
B) Healthcare
C) E-commerce
D) SaaS / Technology
E) Other”

Then proceed adaptively with one short MCQ or open-response question at a time.
"""

# ---------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class IntentJsonRequest(BaseModel):
    content: str

# ---------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------

try:
    from core.config import settings
    API_V1_PREFIX = settings.API_V1_PREFIX
    CORS_ORIGINS = getattr(settings, "cors_origins_list", ["*"])
except Exception:
    API_V1_PREFIX = "/api/v1"
    CORS_ORIGINS = ["*"]

app = FastAPI(title="Architecture Discovery Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router (intent-schema, intent-builder, topologies, diagram, etc.)
try:
    from api.v1 import api_router
    app.include_router(api_router, prefix=API_V1_PREFIX)
except Exception as e:
    logger.warning("API v1 router not mounted: %s", e)


def _create_configurator_tables():
    """Create configurator DB tables if they do not exist. Run at import and on startup."""
    import os
    from sqlalchemy import create_engine
    from db.base import Base
    import models  # noqa: F401 - register all model tables on Base.metadata
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    sync_url = "sqlite:///" + os.path.join(backend_dir, "configurator.db")
    try:
        sync_engine = create_engine(sync_url)
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()
        logger.info("Configurator DB tables ready at %s", sync_url)
    except Exception as e:
        logger.warning("Configurator DB init failed: %s", e)


# Ensure tables exist at import (for TestClient which does not run lifespan) and on startup
_create_configurator_tables()


@app.on_event("startup")
async def create_tables_startup():
    """Ensure configurator DB tables exist when running under uvicorn."""
    _create_configurator_tables()

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/chat")
def chat(req: ChatRequest):

    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured")

    messages = []
    for m in req.messages:
        if m.role == "system":
            continue
        messages.append({"role": m.role, "content": m.content})

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": messages,
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
    }

    response = requests.post(
        CLAUDE_MESSAGES_URL,
        headers=headers,
        json=payload,
        timeout=60,
    )

    if not response.ok:
        error_msg = f"\n--- CLAUDE API ERROR ---\nStatus: {response.status_code}\nResponse: {response.text}\n------------------------\n"
        print(error_msg)
        logger.error(error_msg)
        raise HTTPException(status_code=502, detail="Failed to get response from Claude API. Check backend terminal for details.")

    data = response.json()
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    text = text.strip()

    return {"choices": [{"message": {"role": "assistant", "content": text}}]}

# Store the latest intent JSON in memory
latest_intent_json = None

# Store the latest synthesized architecture in memory
latest_synthesized_architecture = None

def _safe_json_preview(obj, max_chars: int = 2000) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        return s if len(s) <= max_chars else (s[:max_chars] + f"... (truncated, {len(s)} chars)")
    except Exception as e:
        return f"<unserializable json: {e}>"

@app.post("/api/intent-json")
def save_intent_json(req: IntentJsonRequest):
    global latest_intent_json
    try:
        # Extract JSON from markdown code blocks if present
        content = req.content.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()
        
        # Parse to validate it's valid JSON
        json_data = json.loads(content)
        
        # Store in memory
        latest_intent_json = json_data
        
        # Save to file (replaces previous version)
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        intent_filename = f"{output_dir}/architecture_intent.json"
        with open(intent_filename, "w") as f:
            json.dump(json_data, f, indent=2)

        # Debug snapshot (helps trace intent → blocks issues)
        debug_intent_filename = f"{output_dir}/architecture_intent.debug.json"
        try:
            with open(debug_intent_filename, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed writing intent debug snapshot: {e}")

        md = json_data.get("request_metadata", {}) if isinstance(json_data, dict) else {}
        logger.info(
            "Intent saved. request_id=%s sector=%s criticality=%s preview=%s",
            md.get("request_id"),
            md.get("sector"),
            md.get("business_criticality"),
            _safe_json_preview(json_data),
        )
        
        logger.info(f"Architecture Intent JSON saved to memory and file: {intent_filename}")
        
        return {"success": True, "message": json_data, "saved_to": intent_filename}
    
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")
    except Exception as e:
        logger.error(f"Error saving intent JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save intent: {str(e)}")

@app.get("/api/intent-json")
def get_intent_json():
    global latest_intent_json
    try:
        if latest_intent_json is None:
            raise HTTPException(status_code=404, detail="No intent JSON available. Please complete the questionnaire first.")
        
        return latest_intent_json
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading intent JSON: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read intent: {str(e)}")


# ---------------------------------------------------------
# Architecture Synthesis Pipeline
# ---------------------------------------------------------

from architecture_synthesis.policy import PolicyLoader, PolicyMerger
from architecture_synthesis.blocks import (
    BlockRegistryStore, BlockSelector, CompatibilityResolver
)
from architecture_synthesis.graph import GraphComposer
from architecture_synthesis.graph.layout_engine import apply_layout
from architecture_synthesis.graph.layout_strategy_selector import get_layout_strategy
from architecture_synthesis.pattern import detect_architecture_pattern
from architecture_synthesis.semantics import annotate_graph_semantics
from architecture_synthesis.compliance import RuleEvaluationEngine
from architecture_synthesis.resolution import ProductCatalogStore, ProductResolutionEngine
from architecture_synthesis.graph.topology_expander import expand_for_topology
from architecture_synthesis.graph.services_expander import expand_compute_to_services
from services.architecture import diagram_generator as _diagram_gen


@app.post("/api/synthesize")
def synthesize_architecture():
    """
    Synthesize architecture from Master Request JSON.
    
    This endpoint orchestrates the full pipeline:
    1. Load Master Request JSON
    2. Load and merge policies
    3. Select architecture blocks
    4. Resolve compatibility
    5. Compose graph
    6. Evaluate compliance
    7. Resolve products
    8. Return architecture
    """
    global latest_intent_json, latest_synthesized_architecture
    
    try:
        # Step 1: Get Master Request JSON
        if latest_intent_json is None:
            raise HTTPException(
                status_code=400,
                detail="No Master Request JSON available. Please complete the questionnaire first."
            )
        
        master_request = latest_intent_json
        logger.info("Starting architecture synthesis")
        logger.info("Master request preview: %s", _safe_json_preview(master_request))
        
        # Step 2: Load and merge policies
        logger.info("Loading policies...")
        sector = master_request.get("request_metadata", {}).get("sector", "BFSI")
        
        policy_loader = PolicyLoader()
        policies = policy_loader.load_policies(sector=sector)
        
        if not policies:
            raise HTTPException(
                status_code=400,
                detail=f"No policy found for sector: {sector}. Supported sectors: BFSI, Fintech, Healthcare, E-commerce."
            )
        
        policy_merger = PolicyMerger()
        merged_policy = policy_merger.merge(policies)
        logger.info(f"Merged {len(policies)} policies")
        
        # Step 3: Load block registry and select blocks
        logger.info("Selecting architecture blocks...")
        block_registry = BlockRegistryStore()
        block_registry.load()
        
        block_selector = BlockSelector(block_registry)
        selected_architecture = block_selector.select_blocks(master_request, merged_policy)
        logger.info(f"Selected {len(selected_architecture.selected_blocks)} blocks")
        logger.info("Selected blocks: %s", selected_architecture.selected_blocks)
        
        # Step 3b: Architecture pattern detection (Brainboard-style: drives layout strategy)
        architecture_pattern = detect_architecture_pattern(
            selected_architecture.selected_blocks,
            block_registry,
        )
        layout_strategy = get_layout_strategy(architecture_pattern)
        logger.info(f"Pattern: {architecture_pattern.type}, layout strategy: {layout_strategy}")
        
        # Step 4: Resolve compatibility
        logger.info("Resolving compatibility...")
        compatibility_resolver = CompatibilityResolver(block_registry)
        resolved_blocks, warnings = compatibility_resolver.resolve(
            selected_architecture.selected_blocks
        )
        logger.info(f"Resolved to {len(resolved_blocks)} blocks with {len(warnings)} warnings")
        logger.info("Resolved blocks: %s", [b.block_id for b in resolved_blocks])
        if warnings:
            logger.info("Compatibility warnings: %s", [{"message": w.message, "severity": w.severity} for w in warnings])
        
        # Step 5: Compose graph (pass intent for formula-based sizing — Configurator §6)
        logger.info("Composing graph...")
        graph_composer = GraphComposer()
        graph = graph_composer.compose(
            resolved_blocks,
            selected_architecture.deployment_topology,
            intent=master_request,
        )
        logger.info(f"Created graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        logger.info("Graph node ids: %s", [n.id for n in graph.nodes])
        logger.info("Graph node capability_refs: %s", [getattr(n, "capability_ref", None) for n in graph.nodes])
        
        # Step 6: Evaluate compliance
        logger.info("Evaluating compliance...")
        rule_engine = RuleEvaluationEngine(block_registry)
        compliance_report = rule_engine.evaluate_all(merged_policy, graph)
        logger.info(f"Compliance status: {compliance_report.compliance_status}")
        
        # Step 7: Resolve products
        logger.info("Resolving products...")
        product_catalog = ProductCatalogStore()
        product_catalog.load_catalogs(["aws", "your_cloud"])
        
        product_resolver = ProductResolutionEngine(product_catalog, block_registry)
        resolved_architecture = product_resolver.resolve(
            graph,
            selected_architecture.architecture_id,
            master_request.get("deployment_preferences")
        )
        logger.info("Product resolution complete")
        try:
            rn = (resolved_architecture.graph or {}).get("nodes") or []
            re = (resolved_architecture.graph or {}).get("edges") or []
            logger.info("Resolved graph counts: nodes=%s edges=%s", len(rn), len(re))
        except Exception:
            pass
        
        # Step 7a: Build two render views:
        # - logical: horizontal (cleaner)
        # - topology: vertical + expanded (more nodes/edges)
        logical_graph = copy.deepcopy(resolved_architecture.graph)
        topology_graph = copy.deepcopy(resolved_architecture.graph)

        annotate_graph_semantics(logical_graph)
        annotate_graph_semantics(topology_graph)
        # Use intent.services to render multiple app services in topology view
        expand_compute_to_services(topology_graph, intent=master_request, max_services=3, create_replicas=True)
        expand_for_topology(topology_graph, max_instances_per_compute=6)

        # Step 7b: Apply layout (normalize called inside)
        apply_layout(logical_graph, layout_strategy=layout_strategy, orientation="horizontal")
        apply_layout(topology_graph, layout_strategy="layered_vertical", orientation="vertical")

        # Keep backward compatibility: resolved_architecture.graph points to logical view
        resolved_architecture.graph = logical_graph
        logger.info("Layout applied (logical + topology)")
        
        # Step 8: Build complete architecture result
        # Default graph = logical view
        diagram_graph = logical_graph
        result = {
            "architecture_id": selected_architecture.architecture_id,
            "architecture_pattern": architecture_pattern.type,
            "layout_strategy": layout_strategy,
            "selected_architecture": jsonable_encoder(selected_architecture),
            "graph": jsonable_encoder(diagram_graph),
            "compliance_report": jsonable_encoder(compliance_report),
            "resolved_architecture": jsonable_encoder(resolved_architecture),
            "views": {
                "logical": {"graph": jsonable_encoder(logical_graph)},
                "topology": {"graph": jsonable_encoder(topology_graph)},
            },
            "warnings": [{"message": w.message, "severity": w.severity} for w in warnings]
        }
        
        # Store in memory for component endpoints
        latest_synthesized_architecture = result
        
        # Save synthesized architecture to file (replaces previous version)
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        synthesized_filename = f"{output_dir}/architecture_synthesized.json"
        with open(synthesized_filename, "w") as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Architecture synthesis complete! Saved to: {synthesized_filename}")
        
        # Return full architecture result
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during architecture synthesis: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Architecture synthesis failed: {str(e)}"
        )

# ---------------------------------------------------------
# Component-Based Architecture Endpoints
# ---------------------------------------------------------

@app.get("/api/architecture/full")
def get_full_architecture():
    """
    Get the complete synthesized architecture (all components).
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return latest_synthesized_architecture
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving full architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/selected")
def get_selected_architecture():
    """
    Get selected architecture blocks and deployment topology.
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return {
            "architecture_id": latest_synthesized_architecture["architecture_id"],
            "selected_architecture": latest_synthesized_architecture["selected_architecture"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving selected architecture: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/graph")
def get_architecture_graph():
    """
    Get architecture graph (nodes and edges) for diagram visualization.
    Returns the base graph without product mappings.
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return latest_synthesized_architecture["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving architecture graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/graph-with-products")
def get_architecture_graph_with_products(view: str = "logical"):
    """
    Get architecture graph with resolved products embedded in nodes.
    This matches the plan document structure (Section 15.7).
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        v = (view or "logical").strip().lower()
        views = latest_synthesized_architecture.get("views") or {}
        if v in views and (views.get(v) or {}).get("graph") is not None:
            return views[v]["graph"]
        # Fallback: resolved architecture graph (logical view)
        return latest_synthesized_architecture["resolved_architecture"]["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving graph with products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/architecture/diagram")
def get_architecture_diagram(view: str = "logical", mode: str = "default"):
    """
    Legacy/chat diagram-ready JSON (rich contract):
    - containers/nodes/edges + layout_hints per view
    - also includes graph (for backward compatibility)
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(status_code=404, detail="No synthesized architecture available. Please run synthesis first.")
        v = (view or "logical").strip().lower()
        views = latest_synthesized_architecture.get("views") or {}
        graph = None
        if v in views and (views.get(v) or {}).get("graph") is not None:
            graph = views[v]["graph"]
        else:
            graph = latest_synthesized_architecture.get("graph") or {}

        # Enrich to match new contract (collapse/dedupe labels for logical, keep topology edges)
        g = copy.deepcopy(graph)
        try:
            # Ensure semantic fields exist
            annotate_graph_semantics(g)
        except Exception:
            pass

        # Note: topology view is already expanded during /api/synthesize (views.topology).
        # Keep this endpoint idempotent and avoid re-expanding the compute tier here.

        if v == "logical":
            try:
                g = _diagram_gen._collapse_to_primary(g)
            except Exception:
                pass
            try:
                g = _diagram_gen._dedupe_edges(g, by_capability=True)
            except Exception:
                pass
            try:
                apply_layout(g, layout_strategy="layered_vertical", orientation="horizontal")
                g["layout_direction"] = "RIGHT"
            except Exception:
                pass
        else:
            # topology: keep expansion already present (from synthesize) but dedupe exact duplicates
            try:
                g = _diagram_gen._dedupe_edges(g, by_capability=False)
            except Exception:
                pass
            try:
                apply_layout(g, layout_strategy="layered_vertical", orientation="vertical")
                g["layout_direction"] = "DOWN"
            except Exception:
                pass

        view_struct = _diagram_gen._graph_to_view_struct(g)
        return {
            "architecture_id": latest_synthesized_architecture.get("architecture_id"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "view": v,
            "mode": mode or "default",
            "graph": g,
            **view_struct,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error retrieving legacy diagram: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/compliance")
def get_compliance_report():
    """
    Get compliance evaluation report.
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return latest_synthesized_architecture["compliance_report"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/products")
def get_resolved_products():
    """
    Get resolved products/services for the architecture.
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return latest_synthesized_architecture["resolved_architecture"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving resolved products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/architecture/warnings")
def get_warnings():
    """
    Get warnings from architecture synthesis.
    """
    global latest_synthesized_architecture
    try:
        if latest_synthesized_architecture is None:
            raise HTTPException(
                status_code=404,
                detail="No synthesized architecture available. Please run synthesis first."
            )
        return {"warnings": latest_synthesized_architecture["warnings"]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving warnings: {e}")
        raise HTTPException(status_code=500, detail=str(e))