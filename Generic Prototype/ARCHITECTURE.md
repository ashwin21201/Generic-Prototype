# Intent-Based Architecture Configurator — Architecture

## Two Flows

### 1. Legacy flow (unchanged)
- **Chat** → user answers questions in the legacy UI (`/legacy`).
- **Intent JSON** is stored in memory and sent to **Synthesize**.
- **Synthesize** (`POST /api/synthesize`) runs the full pipeline (policy, block selection, compatibility, graph composition, product resolution, layout) and returns architecture with `graph` and `views.logical` / `views.topology`.
- **Diagram** is shown at `/architecture` using the latest synthesized result.

### 2. New flow (session-based)
- **Intent Builder** (`/intent-builder`) creates an **Intent Session** (`POST /api/v1/intent-builder/sessions`), then **start-chat** and **chat** to collect requirements. Intent is stored in DB per session.
- **Submit & Generate** calls **submit** (`POST /api/v1/intent-builder/sessions/{id}/submit`) then **topology generate** (`POST /api/v1/topologies`) with `intent_json`, `project_id`, `org_id`, optional `session_id`.
- **Topology** is persisted (Topology + TopologyNode + TopologyEdge). User is navigated to **Topology detail** (`/topologies/:id`).
- **Diagram** is loaded via `GET /api/v1/diagram/topologies/{id}/diagram?view=logical|topology` and rendered in **DiagramViewer** (Logical vs Topology view toggles).
- **Topology editing** (add/remove blocks, edit spec, add/remove edges, save layout) uses `POST/DELETE/PATCH /api/v1/topologies/{id}/blocks|edges|layout`.

## Backend

- **Config**: `Backend/core/config.py` — Pydantic Settings (e.g. `DATABASE_URL_ASYNC`, `API_V1_PREFIX`, `CORS_ORIGINS`, `CLAUDE_API_KEY`). Load from `Backend/.env`.
- **DB**: SQLite by default (`configurator.db` in Backend dir). Tables: IntentSession, IntentSchema, Topology, TopologyNode, TopologyEdge, Block, CompliancePolicy, ConstraintRule, AuditLog. Created on app import and on startup.
- **API v1** (prefix `/api/v1`): intent-schema, intent-builder, topologies (generate + editing), diagram, blocks, policies, resource-sizing, impact-analysis, governance.
- **Existing routes** kept: `/api/health`, `/api/chat`, `/api/intent-json`, `/api/synthesize`, `/api/architecture/*`.

## Frontend

- **Router**: `/` → Dashboard, `/intent-builder` → Intent Builder, `/topologies` → list, `/topologies/:id` → detail + DiagramViewer, `/legacy` → legacy chat app, `/architecture` → legacy diagram, `/intent-schema`, `/blocks`, `/policy`, `/impact`, `/audit`.
- **API client**: `Frontend/src/lib/api.js` — base `/api`, methods for intentSchemaApi, intentBuilderApi, topologyApi, blockApi, policyApi, impactAnalysisApi, governanceApi.
- **Proxy**: Vite proxies `/api` → `http://localhost:8000` (see `Frontend/vite.config.js`).

## Env vars (backend)

- `DATABASE_URL_ASYNC` — default `sqlite+aiosqlite:///./configurator.db`
- `CLAUDE_API_KEY` or `OPENAI_API_KEY` — for Intent Builder chat and re-extract
- `LLM_PROVIDER` — `claude` | `openai`
- Optional: `API_V1_PREFIX`, `CORS_ORIGINS`, `DEBUG`, `LOG_LEVEL`

## Run

- Backend: `cd Backend && uvicorn app:app --reload`
- Frontend: `cd Frontend && npm run dev`
- Open `http://localhost:5173` — Dashboard; use Intent Builder to create a session, chat, submit, and open a topology diagram.
