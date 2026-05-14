# GenAI Engine — Multi-Tenant Tasks Design Doc

> **Status:** Draft for team review — revision 2 (adds enforcement pattern coverage from endpoint audit)
> **Author:** Ian McGraw
> **Date:** 2026-05-14

---

## Context

GenAI Engine today assumes a single tenant per deployment. All API keys are global (no scoping), all tasks are visible to anyone with a valid key, and the existing role system (`ORG-ADMIN`, `TASK-ADMIN`, etc.) is built around in-house operator roles, not external tenants.

We need to ship a new demo environment where each user gets isolated access to a single task. Tasks become the tenant boundary. Users on the same demo deployment must not be able to read, modify, or even enumerate each other's tasks, inferences, traces, feedback, or rules. Meanwhile, existing single-tenant customer deployments must continue to work without modification: existing admin keys must keep cross-task access, existing endpoints must not break their request/response contracts, and customers who don't want multi-tenancy must not get it forced on them.

The intended outcome is one engine binary that runs in two modes — single-tenant (default, existing behavior) and multi-tenant (opt-in via API key shape + new endpoints). No fork, no separate deployment topology, no migration burden on existing customers.

---

## Goals

1. Introduce **task-scoped API keys** that can only access their own task's resources.
2. Keep **existing admin keys** working with full cross-task access. Zero contract breaks.
3. Provide **two task-provisioning flows**:
   - Admin-only (always available) — admin keys create `(task, tenant_api_key)` pairs.
   - Public signup (feature-flagged, default off) — anyone can hit an endpoint to get a fresh `(task, tenant_api_key)`.
4. **API-layer-only enforcement** in v1. No Postgres RLS, no schema-per-tenant.
5. **Transparent filtering** on list/aggregate endpoints so tenant clients see scoped results without endpoint shape changes.
6. UI changes only to **hide admin nav** when the logged-in key is tenant-scoped. The UI already accepts a pasted API key.

## Non-Goals

- Multi-task-per-tenant. Each tenant key maps to exactly one task in v1.
- User accounts for demo tenants. No JWT, no Keycloak signup, no email verification.
- Document and embedding multi-tenancy. Tenant keys get **403** on `/documents/*` and embedding endpoints in v1. Revisit if demo users need RAG.
- Per-tenant model providers. Provider credentials stay system-wide and admin-only.
- Per-tenant rate limits or quotas. (Add basic IP-based rate limit on the public signup endpoint; that's it.)
- Postgres Row-Level Security. Documented as a v2 hardening option.
- New permission framework. We extend the existing `PermissionLevelsEnum` model.

---

## Design Decisions

| # | Decision | Why |
|---|---|---|
| 1 | API-layer enforcement, no RLS | Smaller blast radius; demo env is low-stakes; can add RLS as a v2 safety net once the API enforcement is proven. |
| 2 | No user accounts for tenants | UI already authenticates via pasted API key (`src/lib/auth.ts:40`). Adding user accounts would be a bigger change for zero demo benefit. |
| 3 | Two task-creation flows, public one feature-flagged | Admin flow ships always-on; public flow gated by `ENABLE_PUBLIC_TENANT_SIGNUP=false` default so customer deployments never expose it. |
| 4 | Transparent filtering on aggregate endpoints | Keeps API shape backwards-compatible; existing SDK clients see a 1-item list instead of breaking on 403. |
| 5 | Denormalize `task_id` onto rule-result + feedback tables | API-layer filtering needs a column to filter on. Multi-hop joins on hot tables (feedback, rule results) get fragile and slow. |
| 6 | Documents/embeddings = admin-only in v1 | Owner-scoped today, no clean tenant story without bigger schema work. Defer. |
| 7 | Add a single new role: `TENANT-USER` | Existing role system already supports adding roles; the permission frozensets just need this role added where appropriate. |
| 8 | `task_id` on `api_keys` is **nullable** | Null = cross-task admin key (existing behavior). Non-null = tenant-scoped key. Clean backwards-compat. |
| 9 | Four enforcement patterns, not one | Audit revealed task is identified four different ways: path, body, resource-id (via FK), query param. Each needs its own mitigation. A single decorator can't cover all four. |
| 10 | Body-`task_id` mismatch returns 404 | Consistent with path-mismatch behavior. Prevents enumeration. |
| 11 | Trace upload: strict reject on `arthur.task` mismatch | Honest failure beats silent rewrite. Easier to debug client misconfigurations. |
| 12 | Service-name → task mapping disabled for tenant keys | Implicit task routing is too easy to abuse. Tenant keys must send explicit `arthur.task`. Admin keys keep existing fallback. |
| 13 | User-attribution fields (`feedback.user_id`, etc.) deferred to v2 | Lower severity (within-tenant forgery, not cross-tenant breach). Tracked in "What This Doc Is Not Doing". |
| 14 | Tenant model access: ship Option A in v1, hold BYOK for v2 | Blocking `model_providers` endpoints (per design rev 3) leaves tenants with no way to discover models. Three paths considered (see "Tenant Model Access" section). Option A — a sanitized `GET /api/v2/models` endpoint with Arthur-hosted providers — is ~10% the build cost of BYOK and forward-compatible with adding BYOK later (Option C). |

---

## Architecture

### Request flow with task scope

```
HTTP Request
    │
    ▼
Bearer token extraction
(src/auth/authorization_header_elements.py:27)
    │
    ▼
MultiMethodValidator.validate_api_multi_auth()
(src/auth/multi_validator.py:25)
    │
    ├─── API key path ──► api_key_repository.lookup_by_id_and_hash()
    │                       returns ApiKey(id, roles, task_id)   ◄── task_id NEW
    │
    └─── JWT path ───────► Keycloak / JWKS → User(roles, task_id=None)
    │
    ▼
request.state.user_id = user.id
request.state.task_scope = key.task_id        ◄── NEW
    │
    ▼
@permission_checker(...)       (existing — checks role frozenset)
@enforce_task_scope(...)       (NEW — checks task_scope vs path/query task_id)
    │
    ▼
Route handler
    │
    └── Repository methods read request.state.task_scope and inject WHERE task_id = X
        when task_scope is not None
```

### API key model: before / after

```
Before (src/db_models/auth_models.py:18)        After
┌──────────────────────┐                        ┌──────────────────────┐
│ api_keys             │                        │ api_keys             │
├──────────────────────┤                        ├──────────────────────┤
│ id           PK      │                        │ id           PK      │
│ key_hash             │                        │ key_hash             │
│ description          │                        │ description          │
│ is_active            │                        │ is_active            │
│ created_at           │                        │ created_at           │
│ deactivated_at       │                        │ deactivated_at       │
│ roles                │                        │ roles                │
└──────────────────────┘                        │ task_id  FK → tasks  │ ◄── NEW
                                                │   NULLABLE           │
                                                └──────────────────────┘

      task_id IS NULL      →  cross-task admin key (existing behavior)
      task_id IS NOT NULL  →  tenant-scoped key; can only access task_id
```

### Trace ingestion isolation

The trace upload endpoint (`POST /api/v1/traces`) needs its own threat model because the task identifier sits inside an opaque protobuf payload, not the URL. The audit found three resolution paths today, two of which are exploitable under multi-tenancy.

```
POST /api/v1/traces  (body = OTLP protobuf bytes)
    │
    ▼
parse ResourceSpan attributes
(src/services/trace/trace_ingestion_service.py:181-200)
    │
    ├── Path 1: arthur.task attribute present
    │           → use that task_id directly
    │
    ├── Path 2: only service.name attribute present
    │           → look up service_name_map (INSTANCE-WIDE, not tenant-aware)
    │
    └── Path 3: neither present
                → route to UNMAPPED_TASK_ID (global __unmapped__ task)
```

**Threats:**
1. Tenant K1 (scope=T1) sets `arthur.task=T2` in the protobuf → spans land in T2.
2. Tenant K1 omits `arthur.task` but sets `service.name="<another tenant's service>"` (matches their mapping) → spans land in the other tenant's task without an explicit task_id ever appearing.
3. UNMAPPED_TASK_ID is globally readable today; if tenant keys can read it, traces accidentally routed there become a cross-tenant leak channel.

**Mitigations:**

1. **Strict reject on explicit `arthur.task` mismatch.** When `request.state.task_scope is not None` and the protobuf carries an explicit `arthur.task` that differs from scope, return 403. No silent override (per decision 11).

2. **Disable service-name fallback for tenant-scoped keys.** When `task_scope is not None`, the resolver skips Path 2 entirely. Tenant must send explicit `arthur.task`. If neither is present, return 400 `arthur.task resource attribute is required for tenant-scoped keys`. Admin keys (`task_scope is None`) keep the existing Path 2 fallback.

3. **`UNMAPPED_TASK_ID` admin-only.** Any read or query that surfaces traces in the unmapped task requires admin scope. Tenant keys 403. Write side already gated by the two changes above.

Updated resolver shape (pseudocode):

```python
def _resolve_task_id(span, task_scope: UUID | None) -> str:
    explicit = _extract_task_id_from_resource_attributes(span)
    if task_scope is not None:
        if explicit is not None and str(explicit) != str(task_scope):
            raise HTTPException(403, "explicit arthur.task does not match key scope")
        if explicit is None:
            raise HTTPException(400, "tenant-scoped keys must set arthur.task")
        return str(task_scope)
    # Admin path: existing logic preserved (explicit → service_name_map → UNMAPPED)
    if explicit is not None:
        return explicit
    mapped = service_name_map.lookup(span.service_name)
    if mapped is not None:
        return mapped
    return UNMAPPED_TASK_ID
```

### Permission resolution rule

For each endpoint:

```
def can_access(endpoint, current_user, request_task_id):
    1. permission_checker validates current_user.roles overlaps endpoint.required_roles
    2. if current_user.task_scope is None:        # admin / unscoped
           pass through
    3. if endpoint.requires_path_task_id:
           if request_task_id != current_user.task_scope:
               return 404 (not 403 — prevents enumeration)
    4. if endpoint.is_aggregate_list:
           inject task_scope filter into repository call
    5. if endpoint.is_admin_only:                  # e.g., users, model_providers, default_rules write
           return 403
```

---

## Schema Changes

### Migration 1 — Add `task_id` to `api_keys`

```sql
ALTER TABLE api_keys
  ADD COLUMN task_id UUID NULL REFERENCES tasks(id);

CREATE INDEX idx_api_keys_task_id ON api_keys(task_id) WHERE task_id IS NOT NULL;
```

`NULL` for all existing keys = preserves admin behavior.

### Migration 2 — Denormalize `task_id` onto rule-result + feedback + annotation tables

| Table | Today reaches `task_id` via | Action |
|---|---|---|
| `inference_feedback` | `inferences.task_id` (1 hop) | Add `task_id UUID NOT NULL`, backfill from inference, index. |
| `prompt_rule_results` | `inference_prompts.inference_id → inferences.task_id` (2 hop) | Add `task_id UUID NOT NULL`, backfill, index. |
| `response_rule_results` | `inference_responses.inference_id → inferences.task_id` (2 hop) | Add `task_id UUID NOT NULL`, backfill, index. |
| `rule_result_details` | via either of the above (3 hop) | Add `task_id UUID NOT NULL`, backfill, index. |
| `agentic_annotations` | `traces.trace_metadata.task_id` (1 hop) | Add `task_id UUID NOT NULL`, backfill, index. |
| `hallucination_claims`, `pii_entities`, `keyword_entities`, `regex_entities`, `toxicity_scores` | Same as `rule_result_details` (3 hop) | Add `task_id UUID NOT NULL`, backfill, index. |

Backfill happens in the migration. On future inserts, the originating repository method passes `task_id` explicitly. (Trigger-based denorm is a good belt-and-suspenders option but introduces ordering/upgrade complexity — recommend app-level for v1, revisit if drift is observed.)

Estimated migration time on a typical customer DB: under 5 minutes for tables with <10M rows, longer for high-volume inference deployments. Plan for a maintenance window or use `CREATE INDEX CONCURRENTLY` and chunked backfill if needed.

### Migration 3 — No-op for documents and embeddings in v1

Per decision 6, tenant keys can't touch documents/embeddings. No schema change.

### Existing columns reused (no new migration needed)

The signup flow (B) and the demo data-retention recommendation both reference `tasks.is_autocreated`. This is an existing column — added in migration `2026_02_09_1744-843e2d3f46d5_service_name_map_and_default_task_.py:25` (BOOLEAN, NOT NULL, default false). The tenant signup flow sets `is_autocreated=True`; the cleanup job filters on it. No new migration is required for this discriminator.

---

## Auth Model

### Code changes

**`src/db_models/auth_models.py`** — add `task_id: Mapped[str | None]` column with FK to `tasks.id`.

**`src/schemas/internal_schemas.py`** — `ApiKey` pydantic model gets `task_id: UUID | None`. `User.get_user_representation()` propagates it.

**`src/auth/multi_validator.py:25`** — after `request.state.user_id` is set (line 57), also set `request.state.task_scope = api_key.task_id` when the auth path was API key, else `None`.

**`src/dependencies.py`** — new dependency `get_task_scope(request) -> UUID | None` returning `request.state.task_scope`.

### New role: `TENANT-USER`

**`src/utils/constants.py:194`** — append `TENANT_USER = "TENANT-USER"` to the role enum.

**`src/schemas/enums.py:70`** — extend `PermissionLevelsEnum` frozensets:

```python
# Allow TENANT-USER on read-side endpoints they should see:
TASK_READ = frozenset([ORG_ADMIN, ORG_AUDITOR, TASK_ADMIN, TENANT_USER])
INFERENCE_READ = frozenset([..., TENANT_USER])
INFERENCE_WRITE = frozenset([..., TENANT_USER])      # tenants run inferences
FEEDBACK_WRITE = frozenset([..., TENANT_USER])
TRACES_WRITE = frozenset([..., TENANT_USER])         # POST /api/v1/traces
DEFAULT_RULES_READ = frozenset([..., TENANT_USER])   # they need to know which apply
USAGE_READ = frozenset([..., TENANT_USER])           # for their own task
MODELS_READ = frozenset([ORG_ADMIN, ORG_AUDITOR, TASK_ADMIN, TENANT_USER])  # NEW — sanitized model registry (see "Tenant Model Access")

# Deliberately NOT adding TENANT-USER to:
TASK_WRITE, API_KEY_WRITE, API_KEY_READ, USER_*, MODEL_PROVIDER_*,
DEFAULT_RULES_WRITE, APP_CONFIG_*, ROTATE_SECRETS, PASSWORD_RESET
```

### New decorator: `@enforce_task_scope(path_param="task_id")`

Wraps endpoints that take a `task_id` in path or query. After `permission_checker` passes:

```python
def enforce_task_scope(path_param: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            scope = kwargs.get("request").state.task_scope
            path_task_id = kwargs.get(path_param)
            if scope is not None and str(scope) != str(path_task_id):
                # 404 not 403 to prevent enumeration
                raise HTTPException(404, detail="Task not found")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Repository changes

For tables that get a denormalized `task_id` (migration 2), repository methods get a `task_scope: UUID | None` parameter. When set, queries add a `.filter(Table.task_id == task_scope)` clause. When `None` (admin keys), queries pass through unchanged.

Affected repositories (concrete file list):
- `src/repositories/inference_repository.py`
- `src/repositories/feedback_repository.py` (if separate, else inside inference_repository)
- `src/repositories/rule_result_repository.py`
- `src/repositories/telemetry_repository.py` (traces, annotations)
- `src/repositories/tasks_repository.py:71-105`
- `src/repositories/api_key_repository.py`

### Tenant signup flow B

```
POST /api/v2/tenant/signup       (no auth required)
  │
  ├── if feature flag ENABLE_PUBLIC_TENANT_SIGNUP != true ──► 404
  │
  ├── rate limit per IP (10/hour default)                  ──► 429
  │
  ├── BEGIN TRANSACTION
  │   ├── INSERT tasks (name="demo-{short_uuid}", is_autocreated=True)
  │   ├── apply default rules (existing logic)
  │   ├── INSERT api_keys (roles=[TENANT-USER], task_id=new_task_id)
  │   └── COMMIT
  │
  └── 201 Created
      {
        "task_id": "...",
        "task_name": "demo-...",
        "api_key": "<one-time visible Bearer token>"
      }
```

Implementation notes:
- Reuse `tasks_repository.create_task()` and `api_key_repository.create_api_key()`.
- Feature flag lives in `src/utils/config.py` (existing config pattern).
- Rate limiting via existing FastAPI rate-limit middleware if present, else add `slowapi`.

### Admin signup flow A

Extend `POST /api/v2/tasks` to optionally mint a tenant API key in one shot:

```
POST /api/v2/tasks
  Body:
    {
      "name": "...",
      "create_tenant_key": true   # NEW, optional, default false
    }

  Response (when create_tenant_key=true):
    {
      "task": { ... },
      "api_key": "<one-time visible Bearer token>"
    }
```

When `create_tenant_key` is false (existing clients), response shape is unchanged.

---

## Enforcement Patterns

The endpoint audit identified four ways genai-engine endpoints today identify which task they operate on, plus a fifth admin-only category. The `@enforce_task_scope` decorator from the original draft only handles the first one. We need four enforcement mechanisms total.

| Pattern | How task is identified | Enforcement mechanism |
|---|---|---|
| **A** — Path task_id | `/tasks/{task_id}/...` | `@enforce_task_scope` decorator (path-level) |
| **B** — Body task_id | request body has `task_id` field | `@enforce_body_task_scope` decorator (body-level) |
| **C** — Resource-id-scoped | path has `/inferences/{id}` etc.; task reached via FK on the resource | Repository-level filter; every `get_X_by_id()` accepts `task_scope` |
| **D** — Query-param task_ids | `?task_ids=...` query string | `@enforce_query_task_scope` decorator (query-level) |
| **E** — Unscoped / admin-only | no task concept (model_providers, users, default_rules write) | Existing `@permission_checker` frozensets exclude `TENANT-USER` |

### Pattern A — `@enforce_task_scope(path_param="task_id")`

(Existing.) Wraps endpoints with `{task_id}` in the URL path. See "Auth Model" above for the implementation.

### Pattern B — `@enforce_body_task_scope(body_field="task_id")` — NEW

Wraps endpoints where the task identifier lives in the request body. Reads the field off the parsed Pydantic body model and compares to `request.state.task_scope`.

```python
def enforce_body_task_scope(body_field: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            scope = request.state.task_scope
            if scope is None:
                return await func(*args, **kwargs)  # admin key, passthrough
            # find the body Pydantic model in kwargs that has the field
            body = next((v for v in kwargs.values() if hasattr(v, body_field)), None)
            if body is None:
                raise HTTPException(500, f"body_field={body_field} not found in handler args")
            body_value = getattr(body, body_field)
            if body_value is None:
                raise HTTPException(400, f"{body_field} required in body")
            if str(body_value) != str(scope):
                raise HTTPException(404, "Task not found")  # 404 not 403 — prevents enumeration
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Pattern C — Repository-level filter for resource-id lookups — NEW

No decorator. The fix lives in the repository so we can't forget it in a handler.

Every `get_X_by_id()` repository method that fetches a task-scoped resource gains an optional `task_scope: UUID | None` parameter. When set, the query adds a `.filter(Table.task_id == task_scope)`. The handler always passes `request.state.task_scope`:

```python
# Before
def get_inference(self, inference_id: str) -> Inference | None:
    return (self.db_session.query(DatabaseInference)
            .filter(DatabaseInference.id == inference_id)
            .first())

# After
def get_inference(self, inference_id: str, task_scope: UUID | None = None) -> Inference | None:
    q = self.db_session.query(DatabaseInference).filter(DatabaseInference.id == inference_id)
    if task_scope is not None:
        q = q.filter(DatabaseInference.task_id == str(task_scope))
    return q.first()
```

When the row isn't found (either because the id doesn't exist, OR because it exists but belongs to a different task), the handler returns 404. Identical response shape — no enumeration.

Why repository-level instead of a decorator: handlers for resource-id-scoped endpoints almost always need to read the resource anyway. A decorator would have to fetch the resource separately, then the handler fetches it again. Pushing the filter into the existing fetch keeps it to one query.

### Pattern D — `@enforce_query_task_scope(query_param="task_ids")` — NEW

Wraps endpoints that accept a `task_ids` query parameter. If scope is set, intersect with scope.

```python
def enforce_query_task_scope(query_param: str = "task_ids"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            scope = request.state.task_scope
            if scope is None:
                return await func(*args, **kwargs)  # admin key, passthrough
            user_task_ids = kwargs.get(query_param) or []
            if not user_task_ids:
                # no filter specified — inject scope as the filter
                kwargs[query_param] = [str(scope)]
            else:
                # filter specified — any task_id outside scope is a 403
                outside = [t for t in user_task_ids if str(t) != str(scope)]
                if outside:
                    raise HTTPException(403, "task_ids outside scope")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Pattern E — Admin-only via permission frozensets (existing mechanism)

Endpoints that operate on platform-level resources (model_providers, default_rules write, users CRUD, app configuration, secrets rotation) are already gated by `@permission_checker`. Their permission frozensets deliberately omit `TENANT-USER`. No new mechanism needed — see "New role: `TENANT-USER`" above for the frozenset additions.

---

## Endpoint-by-endpoint policy

Symbols: ✅ = allowed for tenant keys, ❌ = 403/404, 🪟 = allowed but filtered to their task. The "Pattern" column maps each endpoint to its enforcement mechanism (A/B/C/D/E from the Enforcement Patterns section).

### Pattern coverage at a glance

This subsection maps every audited task-sensitive endpoint to its enforcement pattern. For the access decision (allow / 403 / filter), see the per-category tables below.

#### Pattern B — Body-task_id endpoints (12 — `@enforce_body_task_scope`)

These accept `task_id` (or similar) in the request body. Without enforcement, a tenant key could POST claiming `task_id=<other_tenant>` and write into another task.

| Endpoint | Body field | File:line |
|---|---|---|
| `POST /api/v1/inferences` | `task_id` | `routers/v1/legacy_span_routes.py:450` |
| `POST /api/v1/agentic-prompts` | `task_id` | `routers/v1/agentic_prompt_routes.py:165` |
| `POST /api/v1/agentic-experiments` | `task_id` | `routers/v1/agentic_experiment_routes.py:86` |
| `POST /api/v1/agentic-notebooks` | `task_id` | `routers/v1/agentic_notebook_routes.py:33` |
| `POST /api/v1/prompt_experiments` | `task_id` | `routers/v1/prompt_experiment_routes.py:93` |
| `POST /api/v1/agent_polling/register` | `task_id` | `routers/v1/agent_polling_routes.py:25` |
| `POST /api/v1/agent_polling/start` | `task_id` | `routers/v1/agent_polling_routes.py:54` |
| `POST /api/v1/chatbots` | `task_id` | `routers/v1/chatbot_routes.py:29` |
| `POST /api/v1/chat` | `task_id` | `routers/v1/chat_routes.py:64` |
| `POST /chat` (v2 app chat) | `task_id` | `routers/v2/chat_routes.py:64` |
| `POST /api/chat/default_task` | `task_id` (system-wide config) | `routers/chat_routes.py:366` — **admin-only** |
| `POST /api/v2/configuration` | `chat_task_id` (system-wide config) | `routers/v2/system_management_routes.py:112` — **admin-only** |

The last two set system-wide configuration to point at a task. They stay admin-only (Pattern E) — `@enforce_body_task_scope` is not enough by itself.

#### Pattern C — Resource-id-scoped endpoints (~35 — repository-level filter)

The path takes a resource ID (not a task_id), and the resource has `task_id` via FK. Repository method needs the `task_scope` parameter.

**Trace and span lookups:**
- `GET /api/v1/traces/{trace_id}` → `span_repository.get_trace_by_id`
- `GET /api/v1/traces/{trace_id}/metrics` → `span_repository.get_trace_by_id`
- `GET /api/v1/traces/spans/{span_id}` → `span_repository.get_span_by_id`
- `GET /api/v1/traces/spans/{span_id}/metrics` → `span_repository.get_span_by_id`
- `GET /api/v1/traces/sessions/{session_id}` → `span_repository.get_session_by_id`
- `GET /api/v1/traces/sessions/{session_id}/metrics` → same
- `GET /api/v1/traces/annotations/{annotation_id}` → annotation lookup
- `GET /api/v1/traces/{trace_id}/annotations` → trace ownership check (also Pattern A-adjacent — uses trace_id not task_id but treated as resource-id)
- `POST /api/v1/traces/{trace_id}/annotations` → same; **write side**
- `DELETE /api/v1/traces/{trace_id}/annotations` → same; **write side**

**Inference/feedback lookups:**
- `GET /api/v1/inferences/{inference_id}` → `inference_repository.get_inference`
- `GET /api/v1/inferences/{inference_id}/feedback` → same
- `GET /api/v1/inferences/{inference_id}/rule_results` → same
- `POST /api/v2/feedback/{inference_id}` → must resolve inference's task_id before write
- `POST /api/v2/validate_response/{inference_id}` (deprecated, tenant=❌ anyway)

**Agentic prompt / experiment / notebook:**
- `GET/POST/DELETE /api/v1/agentic-prompts/{prompt_id}/*` (10+ endpoints) → `agentic_prompt_repository._get_db_prompt`
- `GET/PATCH/DELETE /api/v1/agentic-experiments/{experiment_id}` → `agentic_experiment_repository._get_db_experiment`
- `GET /api/v1/agentic-experiments/{experiment_id}/runs` → same
- `GET/PUT/DELETE /api/v1/agentic-notebooks/{notebook_id}` → `agentic_notebook_repository._get_db_notebook`
- `GET/PUT /api/v1/agentic-notebooks/{notebook_id}/state` → same
- `GET /api/v1/agentic-notebooks/{notebook_id}/history` → same

**Continuous eval:**
- `GET/DELETE /api/v1/continuous_evals/{eval_id}` → continuous_eval_repository
- `GET /api/v1/continuous_evals/{eval_id}/results` → same
- `GET/POST /api/v1/continuous_evals/{eval_id}/runs` → same
- `GET/DELETE /api/v1/continuous_evals/{eval_id}/runs/{run_id}` → same
- `GET /api/v1/continuous_evals/{eval_id}/runs/{run_id}/results` → same
- `GET /api/v1/continuous_evals/{eval_id}/runs/{run_id}/status` → same

**Prompt experiments (separate from agentic):**
- `GET/PATCH/DELETE /api/v1/prompt_experiments/{experiment_id}` → `prompt_experiment_repository`
- `GET /api/v1/prompt_experiments/{experiment_id}/versions` → same
- `GET /api/v1/prompt_experiments/{experiment_id}/results` → same

**Chat conversations:**
- `GET/DELETE /api/v1/chat/{conversation_id}` → chat repository
- `POST /api/v1/chat/{conversation_id}/message` → same; **write side**
- `POST /api/v1/chat/{conversation_id}/regenerate` → same; **write side**
- `GET /chat/conversation/{conversation_id}` → same
- `PUT /chat/conversation/{conversation_id}` → same; **write side**

**Chatbots:**
- `PUT /api/v1/chatbots/{chatbot_id}` → chatbot repo
- `DELETE /api/v1/chatbots/{chatbot_id}` → same

**Datasets:**
- `PATCH /api/v2/datasets/{dataset_id}` → `datasets_repository._get_db_dataset`
- `DELETE /api/v2/datasets/{dataset_id}` → same
- `GET /api/v2/datasets/{dataset_id}/versions/{version_number}/rows/{row_id}` → same

#### Pattern D — Query-param `task_ids` endpoints (7 — `@enforce_query_task_scope`)

| Endpoint | Notes |
|---|---|
| `GET /api/v1/traces` | optional `task_ids` |
| `GET /api/v1/traces/spans` | optional `task_ids` |
| `GET /api/v1/traces/sessions` | **required** `task_ids` |
| `GET /api/v1/traces/users` | **required** `task_ids` |
| `GET /api/v1/inferences` | optional `task_ids` |
| `GET /api/v2/inferences/query` | optional `task_ids` |
| `GET /api/v2/feedback/query` | optional `task_ids` |

For "required" cases, decorator behavior unchanged — caller must still supply, but values are intersected against scope.

#### Pattern E — Unscoped / admin-only (frozenset exclusion of `TENANT-USER`)

`POST/DELETE /api/v2/default_rules*`, `GET/PUT/DELETE /api/v1/model_providers*`, `POST /api/v1/secrets/rotation`, `POST/GET/DELETE /users*`, `POST/GET/DELETE /auth/api_keys*`, `POST /api/v2/configuration`, `POST /api/chat/default_task`, and any future endpoint operating on global state.

#### Special: `POST /api/v1/traces`

See "Trace ingestion isolation" subsection in Architecture. Pattern-B-style validation plus disabling the service-name fallback.

---

### Public utility — no change

| Endpoint | Tenant key |
|---|---|
| `GET /health` | ✅ (public) |
| `GET /docs`, `GET /openapi.json` | ✅ (public) |
| `GET /api/v2/display-settings` | ✅ (public) |
| `POST /api/v2/csp_report` | ✅ (public) |
| `/auth/login`, `/auth/callback`, `/auth/logout/*`, `/auth/config` | ✅ (public, unused by tenant keys) |

### Task management

| Endpoint | Tenant key | Notes |
|---|---|---|
| `POST /api/v2/tasks` | ❌ | Admin-only. Flow A extends this for admins to mint tenant keys. |
| `GET /api/v2/tasks` | 🪟 | Filter to `[their_task]`. |
| `POST /api/v2/tasks/search` | 🪟 | Filter to their task. |
| `GET /api/v2/tasks/{id}` | ✅ if their task / 404 if not | |
| `DELETE /api/v2/tasks/{id}` | ❌ | Lifecycle is admin-managed. |
| `POST /api/v2/tasks/{id}/unarchive` | ❌ | Same. |
| `POST /api/v2/tasks/{id}/rules` | ✅ if their task | `@enforce_task_scope`. |
| `PATCH /api/v2/tasks/{id}/rules/{rule_id}` | ✅ if their task | |
| `DELETE /api/v2/tasks/{id}/rules/{rule_id}` | ✅ if their task | |
| `POST /api/v2/tasks/{id}/metrics` | ✅ if their task | |
| `PATCH /api/v2/tasks/{id}/metrics/{metric_id}` | ✅ if their task | |
| `DELETE /api/v2/tasks/{id}/metrics/{metric_id}` | ✅ if their task | |

### Inference / traces / feedback

| Endpoint | Tenant key |
|---|---|
| Inference endpoints (POST validate, etc.) | ✅ if their task; repo filters reads |
| `POST /api/v1/traces` (task_id in body) | ✅ if their task; 403/404 otherwise |
| Feedback endpoints | ✅ if their task |

### Configuration / registry

| Endpoint | Tenant key | Notes |
|---|---|---|
| `GET /api/v2/default_rules` | ✅ | They need visibility into which rules apply to them. |
| `POST /api/v2/default_rules` | ❌ | Affects all tasks. |
| `DELETE /api/v2/default_rules/{id}` | ❌ | Affects all tasks. |
| `POST /api/v2/rules/search` | 🪟 | Return defaults + their task's rules. |
| `GET /api/v1/model_providers` | ❌ | Leaks which providers are configured. |
| `GET /api/v1/model_providers/{p}/available_models` | ❌ | Per-provider read is also a leak vector — a tenant can probe known provider IDs (`anthropic`, `openai`, `azure`, …) and infer the configured set from 200 vs 404, which is the same information the list endpoint blocks. Both must be admin-only. Tenants discover available models via the new sanitized endpoint (see "Tenant Model Access" section). |
| `GET /api/v2/models` (NEW) | ✅ | Sanitized model registry. Returns model identifiers tenants can use, without provider configuration. See "Tenant Model Access" section. |
| `PUT/DELETE /api/v1/model_providers/{p}` | ❌ | |
| `POST /api/v1/secrets/rotation` | ❌ | |
| `GET /api/v2/configuration` | ❌ | System-level config (chat task ID, etc.). |
| `POST /api/v2/configuration` | ❌ | |

### Usage / metrics

| Endpoint | Tenant key | Notes |
|---|---|---|
| `GET /api/v2/usage/tokens` | 🪟 | Endpoint already accepts filters. Inject `task_id` from `request.state.task_scope`. |

**Note on aggregate metrics surface:** genai-engine has essentially one aggregate metric endpoint today (`/usage/tokens`). There is no Prometheus scrape, no `/admin/stats`, no engine-wide counters endpoint. OpenTelemetry instrumentation pushes to NewRelic outbound. If new aggregate-metric endpoints are added later (engine-wide P99 latency, scorer pass rates, tenant count for ops dashboards), they MUST default to admin-only — tenant keys 403. This is a "convention to enforce in code review" risk, not something this plan can solve structurally.

### API key management

| Endpoint | Tenant key |
|---|---|
| `POST /auth/api_keys/` | ❌ |
| `GET /auth/api_keys/` | ❌ |
| `GET /auth/api_keys/{id}` | ❌ |
| `DELETE /auth/api_keys/deactivate/{id}` | ❌ |

### User management

| Endpoint | Tenant key |
|---|---|
| `POST /users`, `GET /users`, `DELETE /users/{id}` | ❌ |
| `POST /users/{id}/reset_password` | ❌ |
| `GET /users/permissions/check` | ✅ | Useful for the UI to know what to show. |

### Documents / embeddings

| Endpoint | Tenant key |
|---|---|
| All `/documents/*` and embedding endpoints | ❌ (admin-only in v1) |

### Deprecated

| Endpoint | Tenant key |
|---|---|
| `POST /api/v2/validate_prompt` | ❌ |
| `POST /api/v2/validate_response/{id}` | ❌ |

### New endpoints

| Endpoint | Auth |
|---|---|
| `POST /api/v2/tasks` (extended with `create_tenant_key`) | Admin |
| `POST /api/v2/tenant/signup` (NEW) | Public, feature-flag-gated |

---

## Tenant Model Access

Blocking `GET /api/v1/model_providers` and the per-provider `available_models` endpoint (per the enumeration-leak fix in design rev 3) closes the infra leak but leaves tenant users with no way to discover which models they can use. We have to pick one of three paths.

### Option A — Arthur hosts, sanitized model registry (RECOMMENDED for v1)

Arthur (the engine operator) configures `model_providers` globally, admin-only. Tenants discover models through a new endpoint that returns model identifiers without exposing provider configuration.

**Mechanism:**
- New endpoint: `GET /api/v2/models`, accessible to tenant keys
- Response shape (illustrative):
  ```json
  [
    { "id": "claude-opus-4-7",        "display_name": "Claude Opus 4.7",        "context_window": 1000000 },
    { "id": "gpt-4o",                  "display_name": "GPT-4o",                  "context_window": 128000 },
    { "id": "gemini-2.0-pro",          "display_name": "Gemini 2.0 Pro",          "context_window": 2000000 }
  ]
  ```
- Strictly no provider field. No credentials. No deployment names. No endpoints.
- Optional v1.1: admin-set flag `model_providers.expose_to_tenants BOOLEAN NOT NULL DEFAULT FALSE` for explicit opt-in per provider. Defer to v1.1 if it makes v1 too big.
- The existing `GET /api/v1/model_providers*` endpoints stay admin-only.
- New permission: `MODELS_READ = frozenset([ORG_ADMIN, ORG_AUDITOR, TASK_ADMIN, TENANT_USER])`.

**Tradeoffs:**

| Pro | Con |
|---|---|
| Zero tenant setup — works the moment a user signs up | Arthur pays all LLM bills |
| Demo env stays clickable | Tenants can't use models Arthur didn't pre-configure |
| Tenants never hand their API keys to Arthur | Tenants on enterprise plans usually want their own billing/compliance relationship |
| Forward-compatible with Option B (same endpoint, response shape extends cleanly) | Limits choice to Arthur's curated set |
| ~1-2 days to implement | Sanitization is on the engine: model IDs that contain provider names (`gpt-4o`, fine; `anthropic-prod-deployment-1`, leak) need a renaming pass |

**Implementation cost:** ~1-2 days human / ~30 min CC.

### Option B — Bring Your Own Keys (BYOK), per-tenant model providers

Each tenant configures their own model providers within their task. Arthur runs the inference; the LLM API keys belong to the tenant.

**Mechanism:**
- Schema: add `task_id UUID NULL` to `model_providers`. NULL = global/admin (existing). Non-null = tenant-scoped. Same nullable pattern as `api_keys.task_id`.
- Schema: add `task_id UUID NULL` to `secret_storage` for the encrypted credential rows the provider config references.
- New endpoints (Pattern A — path-scoped):
  - `POST /api/v2/tasks/{task_id}/model_providers`
  - `GET  /api/v2/tasks/{task_id}/model_providers`
  - `PUT  /api/v2/tasks/{task_id}/model_providers/{provider_id}`
  - `DELETE /api/v2/tasks/{task_id}/model_providers/{provider_id}`
- Inference path: when a tenant key triggers inference, resolve providers in priority order: tenant-task-scoped → global. Tenant config overrides global silently.
- UI: new provider-config screen scoped to the user's task. Form fields per provider (API key, endpoint URL for self-hosted, etc.).
- Secret encryption: existing `secret_storage` table and master key are sufficient for v1 BYOK. Per-tenant encryption keys are a separate v3 hardening; not blocking.

**Tradeoffs:**

| Pro | Con |
|---|---|
| Tenants own their LLM costs and billing | Tenants must onboard their own API keys (real friction for demo) |
| Tenants get a data-locality story (their cloud, their compliance) | Bigger schema change — `task_id` on `model_providers` AND `secret_storage`, plus the routes |
| Production-grade multi-tenancy story | New attack surface (per-tenant secret handling) |
| Tenants can use models Arthur doesn't support | UI work: a scoped provider-config screen |
| | ~1-2 weeks of work vs. ~1-2 days for A |
| | Demo env onboarding loses the "just sign up and go" UX |

**Implementation cost:** ~1-2 weeks human / ~6-8 hours CC.

### Option C — Hybrid (A in v1, B layered on later)

Ship A in v1. Add B on top as v2 once we have multi-tenant customers who need their own billing or compliance story.

**Mechanism:**
- v1: Option A. Tenants use Arthur-hosted models via `GET /api/v2/models`.
- v2: Add Option B. `GET /api/v2/models` response merges Arthur defaults + tenant-configured models. Tenants who never configure a provider see only defaults (Option A behavior preserved). Tenants who configure providers see defaults plus their own.

**Tradeoffs:**

| Pro | Con |
|---|---|
| Demo env stays frictionless for casual users | `GET /api/v2/models` response shape must be designed v1 so it can later merge BYOK models without breaking changes |
| Production tenants get BYOK when they actually need it | Two systems to maintain long-term |
| Forward-compatible | Slightly more design care up front |
| Lowest-risk path | |

**Implementation cost:** Same as A in v1, plus B's cost when v2 lands.

### Recommendation for v1: Option A (with Option C as the long-term path)

**Why:**
1. The demo env's target user is "evaluating genai-engine," and friction matters more than billing flexibility.
2. Implementation cost is ~10% of Option B.
3. Forward-compatible: BYOK can be added later as Option C without breaking the v1 response shape.
4. Cost concern for Arthur is bounded — we can rate-limit per-task and cap demo usage if abuse becomes a concern (a separate concern from this design doc).

**Required for v1:**
- New endpoint: `GET /api/v2/models`, returning sanitized model identifiers (id, display_name, context_window). No provider field.
- New permission frozenset: `MODELS_READ` including `TENANT-USER`.
- Sanitization pass on model IDs to make sure no provider-identifying strings sneak through (especially for custom Azure deployment names or self-hosted endpoints).
- Existing `MODEL_PROVIDER_*` permissions stay admin-only (unchanged from rev 3).

**Open for team discussion:**
1. Is "Arthur eats LLM costs for demo tenants" acceptable financially? If not, jump straight to Option C with BYOK as the v1 path for cost-sensitive deployments.
2. Do paying multi-tenant customers ever expect to BYOK? If yes, schedule Option B sooner (target v2 quarter X).
3. Should we expose `context_window` and other model capabilities in the v1 response, or keep it minimal (just id + display_name)? More capability fields = better UI, but also more sanitization to do.

---

## UI Changes

The genai-engine UI at `arthur-engine/genai-engine/ui/` already authenticates via pasted API key (`src/lib/auth.ts:40`, `src/lib/api.ts:52`). Minimal changes needed:

1. On login, hit `GET /users/permissions/check` to get the current user's effective permissions.
2. If the response includes `TENANT-USER` role and a `task_scope`, set the UI into "tenant mode":
   - Hide admin nav items (users, model providers, default rules write, system config).
   - Hide the task switcher; deep-link the user to their task's dashboard.
   - Hide the "Create API Key" UI.
3. Otherwise (admin key or JWT user), no UI change.

This is one new conditional layer in the route guard. Estimated 1-2 days of UI work.

---

## Implementation Plan (phased)

### Phase 1 — Schema + auth plumbing (no behavior change)
1. Alembic migration: add `task_id` to `api_keys` (nullable).
2. Alembic migration: denormalize `task_id` onto rule-result, feedback, annotation tables. Backfill in-migration.
3. Add `task_id` to `ApiKey` pydantic schema; propagate through `get_user_representation()`.
4. Update `multi_validator.py` to set `request.state.task_scope`.
5. Add `get_task_scope()` dependency in `src/dependencies.py`.
6. Add `TENANT-USER` role to `src/utils/constants.py`.
7. **All existing tests pass without modification** (no behavior change yet — `task_id` is always NULL on existing keys).

### Phase 2 — Enforcement (still backwards-compatible)
1. Add four decorators: `@enforce_task_scope` (path), `@enforce_body_task_scope` (body), `@enforce_query_task_scope` (query). Pattern C is repository-level, no decorator.
2. Apply pattern-A decorator to every endpoint with `{task_id}` in path.
3. Apply pattern-B decorator to all 12 body-task_id endpoints from the audit.
4. Apply pattern-D decorator to all 7 query-param `task_ids` endpoints.
5. Update repository methods to accept `task_scope` and inject filter when set. Concrete method list:
   - `inference_repository.get_inference`
   - `span_repository.get_trace_by_id`, `get_span_by_id`, `get_session_by_id`, `compute_span_metrics`
   - `feedback_repository.create_feedback` (also handles the resource-lookup-before-write pattern)
   - `datasets_repository._get_db_dataset` (and all callers: `get_dataset`, `update_dataset`, `delete_dataset`, version/row methods)
   - `agentic_notebook_repository._get_db_notebook` (and all callers)
   - `agentic_prompt_repository._get_db_prompt` (and all callers)
   - `agentic_experiment_repository._get_db_experiment` (and all callers)
   - `prompt_experiment_repository._get_db_experiment` (and all callers)
   - `continuous_eval_repository.get_eval_by_id`, run lookups
   - `chat_repository.get_conversation_by_id` and message/regenerate paths
   - `chatbot_repository.get_chatbot_by_id`
   - `annotation_repository.get_annotation_by_id`
6. Update `trace_ingestion_service._resolve_task_id` per "Trace ingestion isolation" — strict reject + disable service-name fallback for tenant keys.
7. Add `TENANT-USER` to the permission frozensets per the table above (including new `MODELS_READ`).
8. Implement `GET /api/v2/models` (Option A from "Tenant Model Access"). Returns sanitized model identifiers + display names + context windows. Sources from existing `model_providers` config; sanitization layer strips provider-identifying strings from model IDs. New router `src/routers/v2/model_routes.py`.
9. **Existing admin keys (task_id=NULL) continue to work unchanged.** Tests confirm this.

**Revised estimate:** human ~10-12 days / CC ~6-8 hours. Up from the original ~5 days / ~3 hours estimate because the audit surfaced ~35 resource-id-scoped endpoints + 12 body-task_id endpoints + 7 query-param endpoints + the trace-ingestion rewrite, all of which were under-counted in revision 1.

### Phase 3 — Provisioning flows
1. Extend `POST /api/v2/tasks` with `create_tenant_key` option (Flow A).
2. Add `POST /api/v2/tenant/signup` endpoint (Flow B) behind `ENABLE_PUBLIC_TENANT_SIGNUP` feature flag.
3. Add rate limiting on the signup endpoint.

### Phase 4 — UI
1. Permissions check on login; cache role + task_scope in `AuthContext`.
2. Route guard: hide admin sections for `TENANT-USER`.
3. Deep-link to task dashboard.

### Phase 5 — Verification + docs
1. End-to-end tests for tenant isolation (see Verification section).
2. CHANGELOG entries.
3. Customer-facing release note (multi-tenant is opt-in via the new endpoint + feature flag; existing keys unaffected).

---

## Backwards Compatibility

Concrete claims:

1. **All existing API keys** have `task_id = NULL` after migration. The auth code paths for `task_id IS NULL` (admin keys) are identical to today.
2. **No existing endpoint changes shape.** New optional fields only (`create_tenant_key` on task creation request, `api_key` in task creation response when that field is true).
3. **No existing client SDK breaks.** Aggregate endpoints stay shape-compatible — admin keys see the full list, tenant keys see a 1-item list.
4. **Existing role frozensets are not narrowed.** `TENANT-USER` is added to relevant frozensets; existing roles are not removed.
5. **`ENABLE_PUBLIC_TENANT_SIGNUP` is `false` by default.** Customer deployments never expose the public endpoint unless explicitly enabled.

Risk areas where someone could miss something:
- A repository method that doesn't yet accept `task_scope` will silently return cross-tenant data to a tenant key. Mitigation: lint rule or PR-time check that every repository method touching task-scoped tables accepts `task_scope`. See Verification → fuzz test.
- New endpoints added in the future may forget `@enforce_task_scope`. Mitigation: same lint approach. Document the requirement in the routers' README.

---

## Verification

### Unit tests
- Migration produces `task_id` column on `api_keys` and on denormalized tables. (Use Alembic test harness.)
- `MultiMethodValidator` sets `request.state.task_scope` correctly for API key, JWT, and admin paths.
- `@enforce_task_scope` raises 404 when path scope mismatches.
- `@enforce_body_task_scope` raises 404 when body field mismatches scope, 400 when field is missing.
- `@enforce_query_task_scope` raises 403 when `task_ids` query contains anything outside scope; injects scope when query is empty.
- Repository methods (Pattern C): `get_X(id, task_scope=T2)` returns None for a row that exists with `task_id=T1`. With `task_scope=None`, the row is returned regardless.
- Trace ingestion: `_resolve_task_id` raises 403 when explicit `arthur.task` differs from scope; 400 when explicit absent and scope is non-null; passes through with admin path.
- `permission_checker` correctly admits/rejects `TENANT-USER` per the updated frozensets.

### Integration tests
- Create two tasks (T1, T2) and tenant keys (K1→T1, K2→T2) and one admin key (A). Seed each task with at least one inference, feedback row, trace, span, annotation, dataset, notebook, prompt, experiment, and conversation.
- **Pattern A — Path scope:** K1 hits every `/tasks/{task_id}/*` endpoint with `task_id=T2`. Expect 404.
- **Pattern B — Body scope:** K1 POSTs to every body-task_id endpoint with `body.task_id=T2`. Expect 404. With `body.task_id=T1`, expect normal success.
- **Pattern C — Resource ID scope:** K1 calls every resource-id-scoped GET/PATCH/DELETE with a T2-owned resource's ID (inference, span, trace, dataset, notebook, prompt, experiment, conversation, feedback target). Expect 404 on every one. **Feedback planting test:** K1 POSTs `/api/v2/feedback/{T2_inference_id}` — expect 404 and verify no feedback row was written.
- **Pattern D — Query-param scope:** K1 calls every `task_ids`-accepting endpoint with `?task_ids=T2`. Expect 403. With no `task_ids`, expect transparent filter to T1. With `?task_ids=T1`, expect 200.
- **Trace ingestion strict reject:** K1 posts an OTLP protobuf with `arthur.task=T2`. Expect 403, verify no spans written. K1 posts a protobuf with no `arthur.task` and only `service.name`. Expect 400 (tenant must send explicit). Admin posts the same payload with no explicit task → falls back to service-name map (existing behavior).
- **Cross-task enumeration:** K1 calls `GET /api/v2/tasks`, expects only T1 in the list. K1 calls `GET /api/v2/tasks/search`, expects only T1.
- **Admin still works:** A calls every endpoint above; expects unchanged behavior (full visibility, no filtering).
- **Aggregate filtering:** K1 calls `GET /api/v2/usage/tokens`; expects only T1's usage.
- **Admin-only blocks (Pattern E):** K1 calls `POST /auth/api_keys/`, `GET /users`, `GET /api/v2/configuration`, `POST /api/v2/default_rules`, `POST /api/chat/default_task`, `GET /api/v1/model_providers`, `GET /api/v1/model_providers/anthropic/available_models` (and other known provider IDs — probe-resistance), `POST /api/v1/secrets/rotation`. Expect 403 each.
- **API key tampering:** K1 calls `DELETE /auth/api_keys/deactivate/{A_key_id}` (admin key). Expect 403. (Today: would succeed.)
- **Tenant model registry:** K1 calls `GET /api/v2/models`. Expect 200 with a list of `{id, display_name, context_window}` entries. Assert every entry has no `provider` field, no credential fields, no internal deployment names. Anonymous request: 401/403. Admin (A): same response as tenant (the endpoint is a sanitized view, not a privileged one).
- **Tenant signup flow A:** A calls `POST /api/v2/tasks` with `create_tenant_key=true`; receives a new task + key. New key only sees that task.
- **Tenant signup flow B:** anonymous request to `/api/v2/tenant/signup` with feature flag off returns 404. With feature flag on, returns 201 + a new task + key. Subsequent calls share rate limit per IP.

### Fuzz / coverage test
A test that enumerates every FastAPI route in the app and asserts the right enforcement is wired up. One assertion per pattern. Failing assertion = a developer added an endpoint without scope enforcement.

```python
# Pseudocode
for route in app.routes:
    handler = route.endpoint
    # Pattern A
    if "task_id" in route.path_params:
        assert has_decorator(handler, enforce_task_scope), \
            f"{route.path} has {{task_id}} but is missing @enforce_task_scope"
    # Pattern B
    body_model = inspect_body_model(handler)
    if body_model is not None and "task_id" in body_model.__fields__:
        assert has_decorator(handler, enforce_body_task_scope), \
            f"{route.path} body has task_id but missing @enforce_body_task_scope"
    # Pattern D
    if "task_ids" in inspect_query_params(handler):
        assert has_decorator(handler, enforce_query_task_scope), \
            f"{route.path} accepts task_ids query but missing @enforce_query_task_scope"
```

Pattern C (repository-level) is harder to assert generically. Coverage test for repos: assert every method on a `TaskScopedRepository` base class that takes a resource_id-shaped parameter also accepts `task_scope: UUID | None`. Mark this as a stretch goal — easier to enforce via code review.

### Manual smoke test
1. Run engine in single-tenant mode (default config). Existing admin key works as before.
2. Run engine with `ENABLE_PUBLIC_TENANT_SIGNUP=true`. `curl POST /api/v2/tenant/signup` returns a task + key.
3. Paste key into UI. Confirm UI loads task dashboard, admin nav hidden, task switcher hidden.
4. Try to hit admin endpoint with tenant key. Confirm 403.
5. Send inferences via tenant key. Confirm they land in the right task.
6. Verify with admin key that the tenant's inferences are visible (admin sees all).
7. Spin up second tenant. Confirm cross-tenant isolation.

### Performance baseline
- Tenant key auth path adds one extra column read (`task_id`) per request. Negligible.
- Repository filter injection adds `WHERE task_id = X` to queries. With indexes from migration 2, this is a free or faster query.
- Public signup endpoint: rate-limit + DB transaction. Budget under 500ms.

---

## Open Questions / Risks

1. **Task name collisions** in Flow B. Multiple users hitting `/tenant/signup` simultaneously could collide on auto-generated names. Mitigation: use `demo-{8-char-uuid}` and accept tiny collision probability, or make name unique constraint and retry on conflict.
2. **Default-rule visibility** to tenants. If you ever introduce per-customer default rules, the current "all defaults visible to tenant keys" rule needs revisiting. Today defaults are global so it's safe.
3. **Audit logging.** Existing audit log (if any) doesn't track `task_scope` on events. Out of scope for v1, but flagging.
4. **Demo env data retention.** Public signup creates tasks freely; without a cleanup job, the demo DB grows forever. Recommend a daily job: archive tasks where `is_autocreated=true` and `created_at < now() - 7 days`. Out of scope for this design doc; track as separate work.
5. **Rate limit tuning.** 10/hour/IP is a guess. May need adjustment based on actual demo traffic patterns.

---

## Files To Be Modified (concrete list)

### Backend — migrations
- `alembic/versions/{new}_add_task_id_to_api_keys.py` (new)
- `alembic/versions/{new}_denorm_task_id_to_rule_results.py` (new)

### Backend — models / schemas
- `src/db_models/auth_models.py` (api_keys `task_id`)
- `src/db_models/inference_models.py` (feedback `task_id`)
- `src/db_models/rule_result_models.py` (denorm `task_id`)
- `src/db_models/agentic_annotation_models.py` (denorm `task_id`)
- `src/schemas/internal_schemas.py` (ApiKey pydantic, User propagation)
- `src/schemas/enums.py:70` (extend permission frozensets with TENANT-USER)

### Backend — auth + dependencies + utils
- `src/auth/multi_validator.py:25-74` (set `request.state.task_scope`)
- `src/dependencies.py` (new `get_task_scope()` dependency)
- `src/utils/constants.py:194` (add TENANT-USER role)
- `src/utils/users.py` (new decorators: `enforce_task_scope`, `enforce_body_task_scope`, `enforce_query_task_scope`)
- `src/utils/config.py` (add `ENABLE_PUBLIC_TENANT_SIGNUP` flag)

### Backend — repositories (Pattern C surface)
- `src/repositories/api_key_repository.py`
- `src/repositories/tasks_repository.py`
- `src/repositories/inference_repository.py` (get_inference + task_scope)
- `src/repositories/feedback_repository.py` (create_feedback + resource-lookup task_scope)
- `src/repositories/rule_result_repository.py`
- `src/repositories/telemetry_repository.py` (traces, annotations)
- `src/repositories/span_repository.py` (get_trace_by_id, get_span_by_id, get_session_by_id, get_users_metadata)
- `src/repositories/datasets_repository.py` (_get_db_dataset + all callers)
- `src/repositories/agentic_notebook_repository.py` (_get_db_notebook + all callers)
- `src/repositories/agentic_prompt_repository.py` (_get_db_prompt + all callers)
- `src/repositories/agentic_experiment_repository.py` (_get_db_experiment + all callers)
- `src/repositories/prompt_experiment_repository.py` (_get_db_experiment + all callers)
- `src/repositories/continuous_eval_repository.py` (eval + run lookups)
- `src/repositories/chat_repository.py` (conversation lookups)
- `src/repositories/chatbot_repository.py` (chatbot lookups)

### Backend — trace ingestion (the special case)
- `src/services/trace/trace_ingestion_service.py` (refactor `_resolve_task_id` per "Trace ingestion isolation"; gate service_name_map for tenant keys)

### Backend — routers
- `src/routers/v2/task_management_routes.py` (extend POST `/tasks` + add `/tenant/signup`)
- `src/routers/api_key_routes.py` (apply scope checks)
- `src/routers/v2/model_routes.py` (NEW — `GET /api/v2/models` sanitized model registry, see "Tenant Model Access")
- Apply `@enforce_task_scope` (Pattern A):
  - `src/routers/v2/task_management_routes.py` (all `{task_id}` endpoints)
  - `src/routers/v1/continuous_eval_routes.py` (all `{task_id}` endpoints)
  - `src/routers/v1/llm_eval_routes.py` (all `{task_id}` endpoints)
  - `src/routers/v1/trace_api_routes.py` (`{trace_id}/annotations` endpoints — note: trace_id not task_id, treated similarly)
  - `src/routers/v2/validate_routes.py` (`{task_id}` variants)
- Apply `@enforce_body_task_scope` (Pattern B):
  - `src/routers/v1/legacy_span_routes.py` (POST /inferences)
  - `src/routers/v1/agentic_prompt_routes.py` (POST prompts)
  - `src/routers/v1/agentic_experiment_routes.py` (POST experiments)
  - `src/routers/v1/agentic_notebook_routes.py` (POST notebooks)
  - `src/routers/v1/prompt_experiment_routes.py` (POST experiments)
  - `src/routers/v1/agent_polling_routes.py` (register, start)
  - `src/routers/v1/chatbot_routes.py` (POST chatbots)
  - `src/routers/v1/chat_routes.py` (POST chat)
  - `src/routers/v2/chat_routes.py` (POST chat)
- Apply `@enforce_query_task_scope` (Pattern D):
  - `src/routers/v1/trace_api_routes.py` (GET /traces, /traces/spans, /traces/sessions, /traces/users)
  - `src/routers/v1/legacy_span_routes.py` (GET /inferences)
  - `src/routers/v2/query_routes.py` (GET /inferences/query)
  - `src/routers/v2/feedback_routes.py` (GET /feedback/query)
- Resource-lookup task_scope wiring (Pattern C — handler-side passing only, no decorator):
  - All endpoints in the "Pattern C — Resource-id-scoped endpoints" section above

### UI
- `ui/src/lib/auth.ts`
- `ui/src/contexts/AuthContext.tsx`
- Route guard for admin sections (whatever file routes are defined in)

### Config
- `src/utils/config.py` (add `ENABLE_PUBLIC_TENANT_SIGNUP` flag)

### Tests
- `tests/integration/test_multi_tenant_isolation.py` (new)
- `tests/unit/test_enforce_task_scope.py` (new)
- `tests/coverage/test_route_scope_coverage.py` (new — the fuzz test)

### Docs
- `docs/MULTI_TENANCY_DESIGN.md` (this document)
- `CHANGELOG.md` (new entry)

---

## What This Doc Is Not Doing

Calling these out so they don't get lost:

- Not adding Postgres RLS. (Future v2 hardening.)
- Not adding per-tenant rate limits. (Just an IP rate limit on signup.)
- Not adding tenant-aware audit logging. (Future work.)
- Not adding multi-task-per-tenant support. (Future work — the model is forward-compatible but the UI and endpoints assume single-task.)
- Not changing the JWT/Keycloak admin user flow. (Untouched.)
- Not touching documents/embeddings. (Tenant keys 403 in v1.)
- Not building a tenant admin tier between admin and tenant. (Could be added in v2 by introducing a new role.)
- **Not validating `feedback.user_id` / `inference.user_id` body fields.** These let a caller attribute feedback or an inference to any user string. Within-tenant only — not a cross-tenant breach — so deferred. Track for v2 if forgery within a tenant becomes a concern. Affected endpoints: `POST /api/v2/feedback/{inference_id}`, `POST /api/v2/validate_prompt`, `POST /api/v2/tasks/{task_id}/validate_response/{inference_id}`.
- **Not implementing BYOK (bring-your-own-keys) model providers.** Option B from the "Tenant Model Access" section. Deferred to v2 per the path-C strategy: v1 ships sanitized Arthur-hosted models (Option A), v2 layers BYOK on top without breaking the response shape. The schema change required (adding `task_id` to `model_providers` and `secret_storage`) is documented but not in scope for v1.
