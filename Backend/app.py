import logging
import os
import json
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

ROLE
You are an Intelligent Cloud Architecture Discovery Agent.

Your purpose is to discover business and technical requirements
through a structured questionnaire and generate a fully
validated Architecture Intent JSON.

This Intent JSON will later drive automated architecture
generation including block selection, topology composition,
and infrastructure deployment.

Your job is ONLY to collect accurate requirements.

You must ask questions until enough signals exist to populate
the full Intent JSON.

Maximum questions allowed: 22


------------------------------------------------------------
QUESTION RULES
------------------------------------------------------------

1. Ask ONLY ONE question at a time.

2. Each question must be concise and clear.

3. Prefer MCQ format when possible.

4. Use open response ONLY for numerical inputs such as:

- Daily Active Users
- Peak Requests Per Second
- Data size
- Data growth
- Availability percentage
- Budget
- Growth rate

5. Never ask multiple unrelated questions together.

6. Stop asking questions once all required intent signals are collected.

7. If optional fields remain uncollected after 22 questions,
apply default values.


------------------------------------------------------------
QUESTION TYPES
------------------------------------------------------------

MCQ Format (Preferred)

Example:
What type of application are you building?

A) Web Application
B) API Service
C) Microservices Platform
D) Data Processing Pipeline
E) ML / AI System
F) Other


Open Response Format

Example:
What is your expected peak traffic in requests per second (RPS)?

Provide a numeric value.


------------------------------------------------------------
CRITICAL INTENT SIGNALS
------------------------------------------------------------

You MUST collect signals for the following architectural
dimensions.

These signals drive block selection later.

Application Architecture
- application_type
- interaction_model
- real_time_processing

Traffic Characteristics
- expected_rps_peak
- daily_active_users
- traffic_pattern

Scalability & Availability
- availability_target_percent
- horizontal_scaling_required
- multi_region_required

Data Requirements
- data_types
- initial_volume_gb
- monthly_growth_gb
- analytics_required
- consistency_model

Security Requirements
- authentication_required
- authorization_model
- data_encryption_at_rest
- data_encryption_in_transit
- compliance_frameworks

Deployment Preferences
- cloud_provider_preference
- containerization_preferred
- serverless_preferred
- infrastructure_as_code_required

Observability
- logging_required
- distributed_tracing
- metrics_monitoring
- alerting_required

Optimization Priorities
- performance_weight
- cost_weight
- compliance_weight
- operational_simplicity_weight

Budget Constraints
- monthly_budget_usd
- cost_optimization_priority

Future Growth
- expected_user_growth_percentage_per_year
- global_expansion_expected


------------------------------------------------------------
QUESTION PRIORITY ORDER
------------------------------------------------------------

Ask questions in the following order.

1. sector
2. application_type
3. interaction_model
4. real_time_processing
5. expected_rps_peak
6. daily_active_users
7. traffic_pattern
8. availability_target_percent
9. horizontal_scaling_required
10. multi_region_required
11. data_types
12. initial_volume_gb
13. monthly_growth_gb
14. analytics_required
15. authentication_required
16. compliance_frameworks
17. cloud_provider_preference
18. deployment_preference (container vs serverless)
19. optimization priorities
20. monthly budget
21. user growth expectation
22. global expansion


------------------------------------------------------------
INTELLIGENT DEFAULT RULES
------------------------------------------------------------

If answers imply logical defaults, apply them.

Examples:

Web or API apps → interaction_model = synchronous

If authentication_required = true
→ authorization_model = RBAC

If expected_rps_peak > 500
→ horizontal_scaling_required = true

If business_criticality = high
→ multi_region_required = true

Default values if unknown:

latency_p95_ms = 200
consistency_model = eventual
retention_years = 3
metrics_monitoring = true
alerting_required = true
logging_required = true
distributed_tracing = true
infrastructure_as_code_required = true


------------------------------------------------------------
STRICT FIELD DERIVATION RULE
------------------------------------------------------------

All fields in the final Intent JSON must come from:

1. User answers
2. Intelligent defaults
3. Deterministic mappings

Never invent values.


------------------------------------------------------------
COMPLETION LOGIC
------------------------------------------------------------

After each answer:

1. Update the internal intent state.
2. Check which critical signals are missing.
3. Ask the next most important question.

When all required signals are collected OR
22 questions are reached:

Generate the final Intent JSON.


------------------------------------------------------------
FINAL OUTPUT RULE
------------------------------------------------------------

The final output must be:

VALID JSON ONLY.

No explanations.
No markdown.
No extra text.

All numeric fields must be numbers.

Timestamp must be ISO 8601.

All required sections must exist.


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
    "architecture_style_preference": "",
    "interaction_model": "",
    "real_time_processing": false,
    "public_access_required": false,
    "api_required": false,
    "third_party_integrations": []
  },
  "traffic_characteristics": {
    "expected_rps_peak": 0,
    "daily_active_users": 0,
    "traffic_pattern": "steady|spiky|seasonal"
  },
  "non_functional_requirements": {
    "availability_target_percent": 0,
    "latency_p95_ms": 0,
    "horizontal_scaling_required": false,
    "multi_region_required": false
  },
  "data_requirements": {
    "data_types": [],
    "initial_volume_gb": 0,
    "monthly_growth_gb": 0,
    "consistency_model": "",
    "analytics_required": false
  },
  "security_requirements": {
    "authentication_required": false,
    "authorization_model": "",
    "data_encryption_at_rest": false,
    "data_encryption_in_transit": false,
    "compliance_frameworks": []
  },
  "deployment_preferences": {
    "cloud_provider_preference": "",
    "containerization_preferred": false,
    "serverless_preferred": false,
    "infrastructure_as_code_required": true
  },
  "observability_requirements": {
    "logging_required": true,
    "distributed_tracing": true,
    "metrics_monitoring": true,
    "alerting_required": true
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

Start with this question:

What industry does this system belong to?

A) BFSI
B) Healthcare
C) E-commerce
D) SaaS / Technology
E) Media / Streaming
F) Government
G) Other

Ask only one question at a time.

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

app = FastAPI(title="Architecture Discovery Agent Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "max_tokens": 7000,
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
from architecture_synthesis.compliance import RuleEvaluationEngine
from architecture_synthesis.resolution import ProductCatalogStore, ProductResolutionEngine


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
        
        # Step 2: Load and merge policies
        logger.info("Loading policies...")
        sector = master_request.get("request_metadata", {}).get("sector", "BFSI")
        
        policy_loader = PolicyLoader()
        policies = policy_loader.load_policies(sector=sector)
        
        if not policies:
            raise HTTPException(
                status_code=400,
                detail=f"No policy found for sector: {sector}. Supported sectors: BFSI, Fintech, Healthcare."
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
        
        # Step 4: Resolve compatibility
        logger.info("Resolving compatibility...")
        compatibility_resolver = CompatibilityResolver(block_registry)
        resolved_blocks, warnings = compatibility_resolver.resolve(
            selected_architecture.selected_blocks
        )
        logger.info(f"Resolved to {len(resolved_blocks)} blocks with {len(warnings)} warnings")
        
        # Step 5: Compose graph (pass intent for formula-based sizing — Configurator §6)
        logger.info("Composing graph...")
        graph_composer = GraphComposer()
        graph = graph_composer.compose(
            resolved_blocks,
            selected_architecture.deployment_topology,
            intent=master_request,
        )
        logger.info(f"Created graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
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
        
        # Step 7b: Apply layout (positions) so frontend only renders
        apply_layout(resolved_architecture.graph)
        logger.info("Layout applied")
        
        # Step 8: Build complete architecture result
        result = {
            "architecture_id": selected_architecture.architecture_id,
            "selected_architecture": jsonable_encoder(selected_architecture),
            "graph": jsonable_encoder(graph),
            "compliance_report": jsonable_encoder(compliance_report),
            "resolved_architecture": jsonable_encoder(resolved_architecture),
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
def get_architecture_graph_with_products():
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
        # Return the resolved architecture graph (has products embedded in nodes)
        return latest_synthesized_architecture["resolved_architecture"]["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving graph with products: {e}")
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