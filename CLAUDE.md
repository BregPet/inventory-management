# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Factory Inventory Management System Demo with GitHub integration - Full-stack application with Vue 3 frontend, Python FastAPI backend, and in-memory mock data (no database).

> ⚠️ **This repository and any fork you create are PUBLIC.** Do not commit credentials, internal hostnames, or private registry URLs. `client/.npmrc` pins the public npm registry and `client/package-lock.json` is gitignored to prevent locally-configured registries from leaking into commits — leave both in place.

## Critical Tool Usage Rules

### Subagents
Use the Task tool with these specialized subagents for appropriate tasks:

- **vue-expert**: Use for Vue 3 frontend features, UI components, styling, and client-side functionality
  - Examples: Creating components, fixing reactivity issues, performance optimization, complex state management
  - **MANDATORY RULE: ANY time you need to create or significantly modify a .vue file, you MUST delegate to vue-expert**
- **code-reviewer**: Use after writing significant code to review quality and best practices
- **Explore**: Use for understanding codebase structure, searching for patterns, or answering questions about how components work
- **general-purpose**: Use for complex multi-step tasks or when other agents don't fit

### Skills
- **backend-api-test** skill: Use when writing or modifying tests in `tests/backend` directory with pytest and FastAPI TestClient

### MCP Tools
- **ALWAYS use GitHub MCP tools** (`mcp__github__*`) for ALL GitHub operations
  - Exception: Local branches only - use `git checkout -b` instead of `mcp__github__create_branch`
- **ALWAYS use Playwright MCP tools** (`mcp__playwright__*`) for browser testing
  - Test against: `http://localhost:3000` (frontend), `http://localhost:8001` (API)

## Stack
- **Frontend**: Vue 3 + Composition API + Vite (port 3000)
- **Backend**: Python FastAPI (port 8001)
- **Data**: JSON files in `server/data/` loaded via `server/mock_data.py`

## Commands

```bash
# Both servers (macOS/Linux); stop with ./scripts/stop.sh
./scripts/start.sh

# Backend (http://localhost:8001, docs at /docs)
cd server && uv sync && uv run python main.py

# Frontend (http://localhost:3000)
cd client && npm install && npm run dev
cd client && npm run build      # production build -> client/dist/

# Backend tests: tests/ has no pyproject of its own, so borrow the server's uv env.
# (A plain `cd tests && uv run pytest`, as tests/README.md says, fails: pytest not found.)
cd tests && uv run --project ../server pytest
cd tests && uv run --project ../server pytest backend/test_inventory.py::TestInventoryEndpoints::test_get_all_inventory
```

There is no linter, type checker, or frontend test suite configured.

## Architecture

**Backend is one file.** `server/main.py` holds the Pydantic models, the filter helpers, and every route. `server/mock_data.py` loads all `server/data/*.json` into module-level lists when it is imported. Data is read-only and in memory, so restart the server after editing JSON. `tests/backend/conftest.py` puts `server/` on `sys.path` and imports `main.app` directly into a `TestClient`.

**Filter contract (client and server must agree):**
- `client/src/composables/useFilters.js` keeps filter state in module-level refs, so every view shares one filter state. `getCurrentFilters()` maps the UI's Location to the `warehouse` param and Period to `month`.
- `'all'` means no filter. `api.js` leaves `'all'` values out of the query string, and the server also ignores `'all'`.
- In `main.py`, `apply_filters()` matches `warehouse` exactly and `category`/`status` case-insensitively. `filter_by_month()` does a substring match against `order_date` (e.g. `2025-03`), or expands `Q1-2025`…`Q4-2025` through `QUARTER_MAP`, which covers 2025 only.
- Dashboard summary, orders, and reports use `order_date`; inventory has no time dimension.

**Frontend:** routes live in `client/src/main.js`. All HTTP calls go through `client/src/api.js` (base URL hardcoded to `http://localhost:8001/api`). UI strings go through `useI18n` with `client/src/locales/en.js` and `ja.js`, so add new strings to both. `client/CLAUDE.md` and `server/CLAUDE.md` contain more detailed conventions for each side.

## API Endpoints
- `GET /api/inventory` (filters: warehouse, category), `GET /api/inventory/{id}`
- `GET /api/orders` (filters: warehouse, category, status, month), `GET /api/orders/{id}`
- `GET /api/dashboard/summary` - All filters
- `GET /api/demand`, `/api/backlog` - No filters (backlog items get `has_purchase_order` computed from `purchase_orders.json`)
- `GET /api/spending/*` - Summary, monthly, categories, transactions
- `GET /api/reports/quarterly`, `/api/reports/monthly-trends`
- `GET /api/restocking/recommendations?budget=` - Forecast shortfalls (forecast minus stock on hand), increasing trend first then largest gap, filled greedily within budget
- `GET|POST /api/restocking/orders` - Submitted restocking orders; lead time per category (`CATEGORY_LEAD_TIME_DAYS`), order lead time = slowest item. Held in the module-level `restock_orders` list: the only mutable state, lost on restart, cleared by an autouse fixture in `test_restocking.py`

Every `demand_forecasts.json` SKU must exist in `inventory.json`; restocking takes stock and prices from inventory, and a test enforces this.

## Known Gaps (as of 2026-11-03)
- `client/src/api.js` calls `/api/tasks` (GET/POST/DELETE/PATCH) and `/api/purchase-orders` (POST, GET by backlog item), but the backend has none of these routes. The pending models `PurchaseOrder`/`CreatePurchaseOrderRequest` already exist in `main.py`.
- `Dashboard.vue` uses `<PurchaseOrderModal>`, which does not exist in `client/src/components/`.
- `tests/README.md` lists `test_orders.py`, but that file is missing. The suite has 59 tests, not 51.
- `server/generate_data.py` uses an old product catalog (Widgets/Components, etc.) and overwrites `data/orders.json`. Don't run it unless you intend to replace the current data.

## Code Conventions
- Always document non-obvious logic changes with comments

## Common Issues
1. Use unique keys in v-for (not `index`) - use `sku`, `month`, etc.
2. Validate dates before `.getMonth()` calls
3. Update Pydantic models when changing JSON data structure
4. Inventory filters don't support month (no time dimension)
5. Revenue goals: $800K/month single, $9.6M YTD all months

## File Locations
- Views: `client/src/views/*.vue`
- API Client: `client/src/api.js`
- Backend: `server/main.py`, `server/mock_data.py`
- Data: `server/data/*.json`
- Styles: `client/src/App.vue`

## Design System
- Colors: Slate/gray (#0f172a, #64748b, #e2e8f0)
- Status: green/blue/yellow/red
- Charts: Custom SVG, CSS Grid for layouts
- No emojis in UI
