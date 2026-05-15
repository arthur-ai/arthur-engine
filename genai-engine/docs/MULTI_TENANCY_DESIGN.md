# GenAI Engine — Multi-Tenant Organizations Design Doc

> **Status:** Draft for team review — revision 4 (introduces organizations as the tenant boundary; multiple tasks per org; blocks tenant trace uploads)
> **Author:** Ian McGraw
> **Date:** 2026-05-15

---

## Context

GenAI Engine today assumes a single tenant per deployment. All API keys are global (no scoping), all tasks are visible to anyone with a valid key, and the existing role system (`ORG-ADMIN`, `TASK-ADMIN`, etc.) is built around in-house operator roles, not external tenants.

We need to ship a new demo environment where each user gets isolated access to one or more tasks. The tenant boundary is the **organization** — an org can contain multiple tasks, and a tenant API key is scoped to a single org. Users on the same demo deployment must not be able to read, modify, or even enumerate tasks (or any resource within them) belonging to a different org. Meanwhile, existing single-tenant customer deployments must continue to work without modification: existing admin keys must keep cross-org access, existing endpoints must not break their request/response contracts, and customers who don't want multi-tenancy must not get it forced on them.

The intended outcome is one engine binary that runs in two modes — single-tenant (default, existing behavior — everything sits inside a synthetic "default" org) and multi-tenant (opt-in via creating additional orgs and minting org-scoped API keys). No fork, no separate deployment topology, no migration burden on existing customers.

---

## Goals

1. Introduce an **`organizations`** entity that becomes the tenant boundary. Tasks belong to exactly one org.
2. Introduce **org-scoped API keys** that can only access tasks within their org (and any resource transitively under those tasks).
3. Keep **existing admin keys** working with full cross-org access. Zero contract breaks.
4. Provide **two provisioning flows**:
   - Admin-only (always available) — admin keys create `(org, task, tenant_api_key)` bundles, or add tasks/keys to existing orgs.
   - Public signup (feature-flagged, default off) — anyone can hit an endpoint to get a fresh `(org, task, tenant_api_key)`.
5. **API-layer-only enforcement** in v1. No Postgres RLS, no schema-per-tenant.
6. **Transparent filtering** on list/aggregate endpoints so tenant clients see scoped results without endpoint shape changes.
7. UI changes only to **hide admin nav** when the logged-in key is org-scoped. The UI already accepts a pasted API key.

## Non-Goals

- User accounts for demo tenants. No JWT, no Keycloak signup, no email verification.
- Document and embedding multi-tenancy. Tenant keys get **403** on `/documents/*` and embedding endpoints in v1. Revisit if demo users need RAG.
- Per-tenant model providers (BYOK). Provider credentials stay system-wide and admin-only. (See "Tenant Model Access".)
- Per-tenant rate limits or quotas. (Add basic IP-based rate limit on the public signup endpoint; that's it.)
- Tenant trace uploads. `POST /api/v1/traces` is admin-only in v1 (see decision 14).
- Postgres Row-Level Security. Documented as a v2 hardening option.
- New permission framework. We extend the existing `PermissionLevelsEnum` model.

---

## Design Decisions

| # | Decision | Why |
|---|---|---|
| 1 | API-layer enforcement, no RLS | Smaller blast radius; demo env is low-stakes; can add RLS as a v2 safety net once the API enforcement is proven. |
| 2 | No user accounts for tenants | UI already authenticates via pasted API key (`src/lib/auth.ts:40`). Adding user accounts would be a bigger change for zero demo benefit. |
| 3 | Two task-creation flows, public one feature-flagged | Admin flow ships always-on; public flow gated by `ENABLE_PUBLIC_TENANT_SIGNUP=false` default so customer deployments never expose it. |
| 4 | Transparent filtering on aggregate endpoints | Keeps API shape backwards-compatible; existing SDK clients see a scoped list instead of breaking on 403. |
| 5 | Denormalize **both** `task_id` AND `org_id` onto rule-result + feedback + annotation tables | API-layer filtering needs columns to filter on. Multi-hop joins on hot tables (feedback, rule results) get fragile and slow. Denorm both so per-task filters and per-org filters are equally fast. |
| 6 | Documents/embeddings = admin-only in v1 | Owner-scoped today, no clean tenant story without bigger schema work. Defer. |
| 7 | Add a single new role: `TENANT-USER` | Existing role system already supports adding roles; the permission frozensets just need this role added where appropriate. |
| 8 | `org_id` on `api_keys` is **nullable** | Null = cross-org admin key (existing behavior). Non-null = org-scoped tenant key. Clean backwards-compat. |
| 9 | Four enforcement patterns, not one | Audit revealed task is identified four different ways: path, body, resource-id (via FK), query param. Each needs its own mitigation. |
| 10 | Path / body / query `task_id` mismatch returns 404 | Consistent across patterns. Prevents enumeration. |
| 11 | **Organization is the tenant boundary** (not task) | An org can host multiple tasks. A tenant API key carries `org_id`; access to any task in that org is allowed. Forward-compatible with future expansion (per-org users, billing, defaults). Single-task-per-tenant is a special case (org with one task). |
| 12 | **System tasks live in a dedicated `system` org** | The existing `tasks.is_system_task` flag identifies internal tasks (e.g., chat default, auto-created infrastructure). These migrate into a `system` org so tenant keys cannot resolve them via any code path. Admin keys see them via cross-org access. |
| 13 | **Existing tasks migrate into a `default` org** | All pre-existing tasks (not `is_system_task=True`) get assigned to a synthetic `default` org during migration. Preserves single-tenant customer behavior: their admin keys (org_id NULL) see everything, and the schema's NOT NULL constraint on `tasks.org_id` is satisfied. |
| 14 | **Tenant users cannot upload traces** (`POST /api/v1/traces` admin-only) | Trace ingestion accepts `arthur.task` in opaque protobuf payloads and has a service-name fallback. Both vectors are exploitable. Rather than ship a partial fix (strict-reject + disable fallback), block tenant trace uploads entirely in v1. Re-enable selectively in v2 if a use case appears. |
| 15 | User-attribution fields (`feedback.user_id`, etc.) deferred to v2 | Lower severity (within-tenant forgery, not cross-tenant breach). Tracked in "What This Doc Is Not Doing". |
| 16 | Model providers: allow tenant reads on existing endpoints | `ModelProviderResponse` / `ModelProviderModelList` contain zero credential or infra fields — only `{provider, enabled}` and `{provider, available_models}`. Zero UI changes; existing endpoints stay. BYOK deferred to v2. (See "Tenant Model Access".) |

---

## Architecture

### Tenant model: organizations → tasks → resources

```
┌────────────────────┐
│  organizations     │  NEW
├────────────────────┤
│ id          PK     │
│ name               │
│ created_at         │
│ is_system   bool   │ ◄── true for the system org; false otherwise
└────────────────────┘
         ▲
         │ 1
         │
         │ many
         ▼
┌────────────────────┐
│  tasks             │
├────────────────────┤
│ id          PK     │
│ name               │
│ org_id      FK     │ ◄── NEW, NOT NULL (default org for legacy tasks)
│ is_system_task     │
│ is_autocreated     │
│ ...existing cols   │
└────────────────────┘
         ▲
         │ 1
         │
         │ many
         ▼
┌──────────────────────────────────────────┐
│  inferences, traces, feedback, datasets, │
│  rule_results, annotations, ...          │
├──────────────────────────────────────────┤
│ task_id     FK   (existing)              │
│ org_id      FK   (NEW on hot tables —    │
│                   Migration 2 denorm)    │
└──────────────────────────────────────────┘

API keys
┌────────────────────┐
│  api_keys          │
├────────────────────┤
│ id          PK     │
│ key_hash           │
│ roles              │
│ org_id      FK     │ ◄── NEW, NULLABLE
└────────────────────┘
       org_id IS NULL      → cross-org admin key (existing behavior)
       org_id IS NOT NULL  → org-scoped tenant key
```

### Request flow with org scope

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
    │                       returns ApiKey(id, roles, org_id)    ◄── org_id NEW
    │
    └─── JWT path ───────► Keycloak / JWKS → User(roles, org_id=None)
    │
    ▼
request.state.user_id  = user.id
request.state.org_scope = key.org_id        ◄── NEW (None for admin)
    │
    ▼
@permission_checker(...)       (existing — checks role frozenset)
@enforce_org_scope(...)        (NEW — checks task→org match for path/body/query task_id)
    │
    ▼
Route handler
    │
    └── Repository methods read request.state.org_scope and inject WHERE org_id = X
        when org_scope is not None
```

### Permission resolution rule

For each endpoint:

```
def can_access(endpoint, current_user, request_task_id):
    1. permission_checker validates current_user.roles overlaps endpoint.required_roles
    2. if current_user.org_scope is None:           # admin / unscoped
           pass through
    3. if endpoint.references_task_id (path / body / query):
           resolve task_id → task.org_id
           if task.org_id != current_user.org_scope:
               return 404 (not 403 — prevents enumeration)
    4. if endpoint.is_aggregate_list:
           inject org_scope filter into repository call
    5. if endpoint.is_admin_only:                   # e.g., users, default_rules write, POST /traces
           return 403
```

### Trace ingestion: admin-only in v1

`POST /api/v1/traces` is **gated to admin keys in v1**. Tenant keys receive 403.

Rationale: the trace upload accepts `arthur.task` inside an opaque protobuf payload and has a service-name → task_id fallback map that is instance-wide (not org-aware). Both vectors would let a tenant upload spans to another org's task. Rather than ship a partial fix (strict-reject mismatch + disable fallback), we block tenant uploads entirely in v1 and revisit in v2 if a real use case appears.

Implementation: drop `TENANT-USER` from the `TRACES_WRITE` permission frozenset (currently empty, will not include it). All other trace-related endpoints (reads via `GET /api/v1/traces*`, annotations, sessions) remain accessible to tenants subject to the org-scope checks. Admin keys behave exactly as today — no change to `trace_ingestion_service.py` internals required.

---

## Schema Changes

### Migration 0 — Create `organizations` table; seed `default` and `system` orgs

```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_organizations_name ON organizations(name);
CREATE UNIQUE INDEX idx_organizations_is_system ON organizations(is_system) WHERE is_system = TRUE;

INSERT INTO organizations (name, is_system) VALUES ('default', FALSE);
INSERT INTO organizations (name, is_system) VALUES ('system',  TRUE);
```

The partial unique index on `is_system` enforces "at most one system org." The `default` org has no special flag — it's just a regular org used for backwards compat with single-tenant deployments.

### Migration 1 — Add `org_id` to `tasks`; backfill

```sql
-- Step 1: add nullable column
ALTER TABLE tasks ADD COLUMN org_id UUID REFERENCES organizations(id);

-- Step 2: backfill
UPDATE tasks
   SET org_id = (SELECT id FROM organizations WHERE name = 'system')
 WHERE is_system_task = TRUE;

UPDATE tasks
   SET org_id = (SELECT id FROM organizations WHERE name = 'default')
 WHERE org_id IS NULL;

-- Step 3: enforce NOT NULL after backfill
ALTER TABLE tasks ALTER COLUMN org_id SET NOT NULL;

CREATE INDEX idx_tasks_org_id ON tasks(org_id);
```

Two-step nullable→backfill→NOT NULL pattern keeps the migration safe to apply against a live database.

### Migration 2 — Add `org_id` to `api_keys` (nullable)

```sql
ALTER TABLE api_keys
  ADD COLUMN org_id UUID NULL REFERENCES organizations(id);

CREATE INDEX idx_api_keys_org_id ON api_keys(org_id) WHERE org_id IS NOT NULL;
```

`NULL` for all existing keys = preserves admin behavior on existing single-tenant deployments.

### Migration 3 — Denormalize `task_id` AND `org_id` onto rule-result + feedback + annotation tables

| Table | Columns added | Backfill source |
|---|---|---|
| `inference_feedback` | `task_id UUID NOT NULL`, `org_id UUID NOT NULL` | `inferences.task_id` → `tasks.org_id` |
| `prompt_rule_results` | `task_id`, `org_id` | `inference_prompts → inferences.task_id → tasks.org_id` |
| `response_rule_results` | `task_id`, `org_id` | `inference_responses → inferences.task_id → tasks.org_id` |
| `rule_result_details` | `task_id`, `org_id` | via prompt/response rule_result |
| `agentic_annotations` | `task_id`, `org_id` | `traces.trace_metadata.task_id → tasks.org_id` |
| `hallucination_claims`, `pii_entities`, `keyword_entities`, `regex_entities`, `toxicity_scores` | `task_id`, `org_id` | via `rule_result_details` |

Index on `org_id` for each table. On future inserts, the originating repository method passes both `task_id` and `org_id` explicitly. (Trigger-based denorm is a good belt-and-suspenders option but introduces ordering/upgrade complexity — recommend app-level for v1.)

Estimated migration time on a typical customer DB: under 5 minutes for tables with <10M rows, longer for high-volume inference deployments. Plan for a maintenance window or use `CREATE INDEX CONCURRENTLY` and chunked backfill if needed.

### Migration 4 — No-op for documents and embeddings in v1

Per decision 6, tenant keys can't touch documents/embeddings. No schema change.

### Existing columns reused (no new migration needed)

The signup flow (B) and the demo data-retention recommendation both reference `tasks.is_autocreated`. This is an existing column — added in migration `2026_02_09_1744-843e2d3f46d5_service_name_map_and_default_task_.py:25` (BOOLEAN, NOT NULL, default false). The tenant signup flow sets `is_autocreated=True`; the cleanup job filters on it.

Similarly, `tasks.is_system_task` already exists and is used by Migration 1 to route system tasks into the system org.

---

## Auth Model

### Code changes

**`src/db_models/organization_models.py`** (NEW) — define `DatabaseOrganization` with id, name, is_system, created_at.

**`src/db_models/task_models.py`** — add `org_id: Mapped[str]` column with FK to `organizations.id`, NOT NULL, and relationship to `Organization`.

**`src/db_models/auth_models.py`** — add `org_id: Mapped[str | None]` column with FK to `organizations.id`, nullable.

**`src/schemas/internal_schemas.py`** — `ApiKey` pydantic model gets `org_id: UUID | None`. `Task` pydantic model gets `org_id: UUID`. `User.get_user_representation()` propagates `org_id`.

**`src/auth/multi_validator.py:25`** — after `request.state.user_id` is set, also set `request.state.org_scope = api_key.org_id` when the auth path was API key, else `None`.

**`src/dependencies.py`** — new dependency `get_org_scope(request) -> UUID | None` returning `request.state.org_scope`.

### New role: `TENANT-USER`

**`src/utils/constants.py:194`** — append `TENANT_USER = "TENANT-USER"` to the role enum.

**`src/schemas/enums.py:70`** — extend `PermissionLevelsEnum` frozensets:

```python
# Allow TENANT-USER on read-side endpoints they should see:
TASK_READ = frozenset([ORG_ADMIN, ORG_AUDITOR, TASK_ADMIN, TENANT_USER])
INFERENCE_READ = frozenset([..., TENANT_USER])
INFERENCE_WRITE = frozenset([..., TENANT_USER])      # tenants run inferences
FEEDBACK_WRITE = frozenset([..., TENANT_USER])
DEFAULT_RULES_READ = frozenset([..., TENANT_USER])   # they need to know which apply
USAGE_READ = frozenset([..., TENANT_USER])           # for their own org's tasks
MODEL_PROVIDER_READ = frozenset([..., TENANT_USER])  # read responses contain no credentials

# Deliberately NOT adding TENANT-USER to:
TASK_WRITE,            # task creation/deletion is admin-managed in v1
TRACES_WRITE,          # tenant users cannot upload traces (decision 14)
API_KEY_*,
USER_*,
MODEL_PROVIDER_WRITE,
DEFAULT_RULES_WRITE,
APP_CONFIG_*,
ROTATE_SECRETS,
PASSWORD_RESET,
ORG_*                  # NEW — org CRUD is admin-only
```

### New decorators

#### `@enforce_org_scope(path_param="task_id")` — Pattern A

Wraps endpoints with `{task_id}` in the URL path. Resolves the task to its org and compares to the caller's `org_scope`.

```python
def enforce_org_scope(path_param: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)  # admin key, passthrough
            path_task_id = kwargs.get(path_param)
            if path_task_id is None:
                raise HTTPException(500, f"path_param={path_param} not found")
            task = task_lookup_cache.get(path_task_id) or tasks_repo.get_task_by_id(path_task_id)
            if task is None or str(task.org_id) != str(scope):
                raise HTTPException(404, "Task not found")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

The lookup result can be cached on `request.state` so handler-side repository calls don't re-fetch the task.

#### `@enforce_body_org_scope(body_field="task_id")` — Pattern B

Reads `task_id` from the parsed Pydantic body, resolves to org, compares.

```python
def enforce_body_org_scope(body_field: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)
            body = next((v for v in kwargs.values() if hasattr(v, body_field)), None)
            if body is None:
                raise HTTPException(500, f"body_field={body_field} not found")
            body_value = getattr(body, body_field)
            if body_value is None:
                raise HTTPException(400, f"{body_field} required in body")
            task = tasks_repo.get_task_by_id(body_value)
            if task is None or str(task.org_id) != str(scope):
                raise HTTPException(404, "Task not found")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

#### `@enforce_query_org_scope(query_param="task_ids")` — Pattern D

```python
def enforce_query_org_scope(query_param: str = "task_ids"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)
            user_task_ids = kwargs.get(query_param) or []
            if not user_task_ids:
                # no filter — inject "all tasks in my org" via repo, OR rewrite query to list scoped task_ids
                kwargs[query_param] = [str(t.id) for t in tasks_repo.list_tasks_by_org(scope)]
            else:
                # validate every supplied task_id is in caller's org
                tasks = tasks_repo.get_tasks_by_ids(user_task_ids)
                outside = [t for t in tasks if str(t.org_id) != str(scope)]
                missing = set(user_task_ids) - {str(t.id) for t in tasks}
                if outside or missing:
                    raise HTTPException(403, "task_ids include items outside caller's org")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Repository changes (Pattern C — resource-id lookups)

Every `get_X_by_id()` method that fetches a task-scoped resource gains an optional `org_scope: UUID | None` parameter. When set, the query filters by the denormalized `org_id` column (added in Migration 3):

```python
# Before
def get_inference(self, inference_id: str) -> Inference | None:
    return (self.db_session.query(DatabaseInference)
            .filter(DatabaseInference.id == inference_id)
            .first())

# After
def get_inference(self, inference_id: str, org_scope: UUID | None = None) -> Inference | None:
    q = self.db_session.query(DatabaseInference).filter(DatabaseInference.id == inference_id)
    if org_scope is not None:
        q = q.filter(DatabaseInference.org_id == str(org_scope))
    return q.first()
```

Handler always passes `org_scope=request.state.org_scope`. Returns None when the row is missing OR belongs to a different org → handler 404s. Admin keys (org_scope=None) skip the filter.

For tables without a denormalized `org_id`, the repository joins through `tasks`:

```python
q = q.join(Task, Task.id == Table.task_id).filter(Task.org_id == str(org_scope))
```

This is fine for low-volume tables. The denormalized `org_id` (Migration 3) is for hot tables only.

### Tenant signup flow B — public endpoint

```
POST /api/v2/tenant/signup       (no auth required)
  │
  ├── if feature flag ENABLE_PUBLIC_TENANT_SIGNUP != true ──► 404
  │
  ├── rate limit per IP (10/hour default)                  ──► 429
  │
  ├── BEGIN TRANSACTION
  │   ├── INSERT organizations (name="demo-{short_uuid}", is_system=false)
  │   ├── INSERT tasks (name="demo-{short_uuid}", org_id=new_org_id, is_autocreated=True)
  │   ├── apply default rules (existing logic)
  │   ├── INSERT api_keys (roles=[TENANT-USER], org_id=new_org_id)
  │   └── COMMIT
  │
  └── 201 Created
      {
        "org_id":   "...",
        "task_id":  "...",
        "task_name": "demo-...",
        "api_key":  "<one-time visible Bearer token>"
      }
```

Implementation notes:
- Reuse `tasks_repository.create_task()` and `api_key_repository.create_api_key()`, plus a new `organizations_repository.create_organization()`.
- Feature flag lives in `src/utils/config.py` (existing config pattern).
- Rate limiting via existing FastAPI rate-limit middleware if present, else add `slowapi`.

### Admin signup flow A — extend POST /tasks

```
POST /api/v2/tasks
  Body (existing fields plus):
    {
      "name": "...",
      "org_id": "<optional, defaults to 'default' org>",
      "create_tenant_key": true   # NEW, optional, default false
    }

  Response (when create_tenant_key=true):
    {
      "task": { ... },
      "api_key": "<one-time visible Bearer token>"
    }
```

Behavior:
- If `org_id` omitted → task is created in the `default` org. Preserves backwards compat for admin clients that never knew about orgs.
- If `org_id` provided → task is created in that org. Admin must have provided a real org_id; otherwise 400.
- If `create_tenant_key=true` → admin gets back a `TENANT-USER` API key scoped to the (new or existing) org. Useful for creating multiple tasks in the same org and minting one key for the whole org.

Admin can also create an org separately via the new endpoints below, then mint keys against it.

### New endpoints: org management (admin-only)

| Endpoint | Description |
|---|---|
| `POST   /api/v2/organizations` | Create a new org. Admin-only. |
| `GET    /api/v2/organizations` | List orgs. Admin-only. |
| `GET    /api/v2/organizations/{org_id}` | Get org by ID. Admin-only. |
| `DELETE /api/v2/organizations/{org_id}` | Archive an org (cascade: archive its tasks; refuse if not empty unless `?force=true`). Admin-only. Refuses if `is_system=true`. |
| `POST   /api/v2/organizations/{org_id}/api_keys` | Mint a tenant API key for this org. Admin-only. |

New permissions: `ORG_WRITE = frozenset([ORG_ADMIN])`, `ORG_READ = frozenset([ORG_ADMIN, ORG_AUDITOR])`. Neither includes `TENANT-USER`.

---

## Enforcement Patterns

The endpoint audit identified four ways genai-engine endpoints today identify which task they operate on, plus a fifth admin-only category. Each pattern resolves via task → org and checks against the caller's `org_scope`.

| Pattern | How task is identified | Enforcement mechanism |
|---|---|---|
| **A** — Path task_id | `/tasks/{task_id}/...` | `@enforce_org_scope` decorator |
| **B** — Body task_id | request body has `task_id` field | `@enforce_body_org_scope` decorator |
| **C** — Resource-id-scoped | path has `/inferences/{id}` etc.; task reached via FK on the resource | Repository-level filter; every `get_X_by_id()` accepts `org_scope` |
| **D** — Query-param task_ids | `?task_ids=...` query string | `@enforce_query_org_scope` decorator |
| **E** — Unscoped / admin-only | no task concept (model_providers write, users, default_rules write, POST traces) | Existing `@permission_checker` frozensets exclude `TENANT-USER` |

(Implementation of each decorator and the repository-level filter pattern is detailed in "Auth Model" above.)

---

## Endpoint-by-endpoint policy

Symbols: ✅ = allowed for tenant keys, ❌ = 403/404, 🪟 = allowed but filtered to caller's org.

### Pattern coverage at a glance

#### Pattern B — Body-task_id endpoints (12 — `@enforce_body_org_scope`)

These accept `task_id` (or similar) in the request body. The decorator resolves the body's task_id to its org and compares to caller's `org_scope`.

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
| `POST /api/chat/default_task` | `task_id` (system-wide config) | `routers/chat_routes.py:366` — **admin-only (Pattern E)** |
| `POST /api/v2/configuration` | `chat_task_id` (system-wide config) | `routers/v2/system_management_routes.py:112` — **admin-only (Pattern E)** |

The last two set system-wide configuration. They stay admin-only.

#### Pattern C — Resource-id-scoped endpoints (~35 — repository-level filter)

The path takes a resource ID, and the resource has `task_id` (and now `org_id` on hot tables). Repository method filters by `org_id` when scope is set.

**Trace and span lookups** (all reads — POST `/api/v1/traces` is now ❌ via Pattern E):
- `GET /api/v1/traces/{trace_id}` → `span_repository.get_trace_by_id`
- `GET /api/v1/traces/{trace_id}/metrics` → same
- `GET /api/v1/traces/spans/{span_id}` → `span_repository.get_span_by_id`
- `GET /api/v1/traces/spans/{span_id}/metrics` → same
- `GET /api/v1/traces/sessions/{session_id}` → `span_repository.get_session_by_id`
- `GET /api/v1/traces/sessions/{session_id}/metrics` → same
- `GET /api/v1/traces/annotations/{annotation_id}` → annotation lookup
- `GET /api/v1/traces/{trace_id}/annotations` → trace ownership check
- `POST /api/v1/traces/{trace_id}/annotations` → **write side; tenant can annotate traces in their org**
- `DELETE /api/v1/traces/{trace_id}/annotations` → same; write side

**Inference / feedback lookups:**
- `GET /api/v1/inferences/{inference_id}` → `inference_repository.get_inference`
- `GET /api/v1/inferences/{inference_id}/feedback` → same
- `GET /api/v1/inferences/{inference_id}/rule_results` → same
- `POST /api/v2/feedback/{inference_id}` → resolves inference → org before write

**Agentic prompt / experiment / notebook:** all `/{prompt_id|experiment_id|notebook_id}` endpoints route through `agentic_*_repository._get_db_*()` with `org_scope`.

**Continuous eval, prompt experiments, chat conversations, chatbots, datasets:** same pattern.

#### Pattern D — Query-param `task_ids` endpoints (7 — `@enforce_query_org_scope`)

| Endpoint | Notes |
|---|---|
| `GET /api/v1/traces` | optional `task_ids` |
| `GET /api/v1/traces/spans` | optional `task_ids` |
| `GET /api/v1/traces/sessions` | **required** `task_ids` |
| `GET /api/v1/traces/users` | **required** `task_ids` |
| `GET /api/v1/inferences` | optional `task_ids` |
| `GET /api/v2/inferences/query` | optional `task_ids` |
| `GET /api/v2/feedback/query` | optional `task_ids` |

For "required" cases, decorator behavior unchanged — caller must still supply, but every supplied id must resolve to a task in the caller's org. Unsupplied case: decorator expands the filter to "all tasks in caller's org."

#### Pattern E — Unscoped / admin-only (frozenset exclusion of `TENANT-USER`)

- **`POST /api/v1/traces` (NEW in rev 4 — was previously allowed with mitigations; now blocked entirely per decision 14)**
- `POST/GET/DELETE /api/v2/organizations*` (admin org management)
- `POST/DELETE /api/v2/default_rules*`
- `PUT/DELETE /api/v1/model_providers/{p}` (write side)
- `POST /api/v1/secrets/rotation`
- `POST/GET/DELETE /users*`
- `POST/GET/DELETE /auth/api_keys*`
- `POST /api/v2/configuration`, `GET /api/v2/configuration`
- `POST /api/chat/default_task`
- Any future endpoint operating on global state

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
| `POST /api/v2/tasks` | ❌ | Admin-only. Admins can specify `org_id` (default = `default` org) and `create_tenant_key`. |
| `GET /api/v2/tasks` | 🪟 | Filter to tasks in caller's org. |
| `POST /api/v2/tasks/search` | 🪟 | Same. |
| `GET /api/v2/tasks/{id}` | ✅ if in caller's org / 404 if not | Pattern A. |
| `DELETE /api/v2/tasks/{id}` | ❌ | Lifecycle admin-managed. |
| `POST /api/v2/tasks/{id}/unarchive` | ❌ | Same. |
| `POST /api/v2/tasks/{id}/rules` | ✅ if in caller's org | Pattern A. |
| `PATCH /api/v2/tasks/{id}/rules/{rule_id}` | ✅ if in caller's org | |
| `DELETE /api/v2/tasks/{id}/rules/{rule_id}` | ✅ if in caller's org | |
| `POST /api/v2/tasks/{id}/metrics` | ✅ if in caller's org | |
| `PATCH /api/v2/tasks/{id}/metrics/{metric_id}` | ✅ if in caller's org | |
| `DELETE /api/v2/tasks/{id}/metrics/{metric_id}` | ✅ if in caller's org | |

### Inference / traces / feedback

| Endpoint | Tenant key | Notes |
|---|---|---|
| Inference endpoints (POST validate, etc.) | ✅ if in caller's org | Pattern B. |
| `POST /api/v1/traces` | **❌ (admin-only in v1)** | Decision 14. |
| `GET /api/v1/traces*` (reads) | ✅ if in caller's org | Patterns C and D. |
| Feedback endpoints | ✅ if in caller's org | Pattern C. |

### Organization management (new)

| Endpoint | Tenant key |
|---|---|
| `POST /api/v2/organizations` | ❌ |
| `GET /api/v2/organizations` | ❌ |
| `GET /api/v2/organizations/{org_id}` | ❌ |
| `DELETE /api/v2/organizations/{org_id}` | ❌ |
| `POST /api/v2/organizations/{org_id}/api_keys` | ❌ |

### Configuration / registry

| Endpoint | Tenant key | Notes |
|---|---|---|
| `GET /api/v2/default_rules` | ✅ | They need visibility into which rules apply to them. |
| `POST /api/v2/default_rules` | ❌ | Affects all tasks. |
| `DELETE /api/v2/default_rules/{id}` | ❌ | Same. |
| `POST /api/v2/rules/search` | 🪟 | Return defaults + caller's org's task rules. |
| `GET /api/v1/model_providers` | ✅ | Response is `[{provider, enabled}]` — no credentials. |
| `GET /api/v1/model_providers/{p}/available_models` | ✅ | Response is `{provider, available_models}` — model identifiers only. |
| `PUT/DELETE /api/v1/model_providers/{p}` | ❌ | Write side accepts credentials. |
| `POST /api/v1/secrets/rotation` | ❌ | |
| `GET /api/v2/configuration` | ❌ | System-level. |
| `POST /api/v2/configuration` | ❌ | |

### Usage / metrics

| Endpoint | Tenant key | Notes |
|---|---|---|
| `GET /api/v2/usage/tokens` | 🪟 | Inject `org_id` filter (transparently sums across all tasks in caller's org). |

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
| `GET /users/permissions/check` | ✅ |

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
| `POST /api/v2/tasks` (extended with `org_id`, `create_tenant_key`) | Admin |
| `POST /api/v2/organizations` | Admin |
| `GET /api/v2/organizations` | Admin |
| `GET /api/v2/organizations/{id}` | Admin |
| `DELETE /api/v2/organizations/{id}` | Admin |
| `POST /api/v2/organizations/{id}/api_keys` | Admin |
| `POST /api/v2/tenant/signup` | Public, feature-flag-gated |

---

## Tenant Model Access

Tenant users need to know which models they can use. The existing `GET /api/v1/model_providers*` endpoints return responses that contain no credentials, no endpoints, and no deployment names:

```python
class ModelProviderResponse(BaseModel):
    provider: ModelProvider              # enum value, public
    enabled: bool                        # whether credentials are configured

class ModelProviderModelList(BaseModel):
    provider: ModelProvider              # enum value, public
    available_models: List[str]          # list of model identifiers
```

FastAPI's `response_model` enforces these schemas. The supported `ModelProvider` enum is part of the public OpenAPI surface. Whether each provider is enabled is not a meaningful secret on a customer deployment, and on the demo env all providers are intentionally exposed to all tenants anyway.

**v1: Option 0** — add `TENANT-USER` to the `MODEL_PROVIDER_READ` permission frozenset; leave `MODEL_PROVIDER_WRITE` admin-only. Zero UI changes. The UI continues to call the existing endpoints.

**v2: Option C (hybrid)** — extend the same endpoints so that when a tenant key is used, the response merges global providers with any tenant-org-scoped providers (BYOK). Backwards-compatible — orgs that never configure their own providers see only globals.

(Earlier revisions of this doc considered a new sanitized `GET /api/v2/models` endpoint and full BYOK in v1. Both are deferred — see "What This Doc Is Not Doing".)

---

## UI Changes

The genai-engine UI at `arthur-engine/genai-engine/ui/` already authenticates via pasted API key (`src/lib/auth.ts:40`, `src/lib/api.ts:52`). Minimal changes needed:

1. On login, hit `GET /users/permissions/check` to get the current user's effective permissions and `org_scope` (if any).
2. If the response includes `TENANT-USER` role and a non-null `org_scope`, set the UI into "tenant mode":
   - Hide admin nav items (users, organizations, model provider config, default rules write, system config).
   - Show only tasks within the caller's org in the task switcher.
   - Hide the "Create API Key" UI.
3. Otherwise (admin key or JWT user), no UI change.

This is one new conditional layer in the route guard. Estimated 1-2 days of UI work.

---

## Implementation Plan (phased)

### Phase 1 — Schema + auth plumbing (no behavior change)
1. Migration 0: create `organizations` table; seed `default` + `system` orgs.
2. Migration 1: add `org_id` to `tasks`; backfill (system tasks → system org, others → default org); enforce NOT NULL.
3. Migration 2: add `org_id` to `api_keys` (nullable).
4. Migration 3: denormalize `task_id` + `org_id` onto rule-result / feedback / annotation tables. Backfill in-migration.
5. Add `DatabaseOrganization` model and Pydantic `Organization` schema.
6. Add `org_id` to `Task` and `ApiKey` schemas; propagate via `get_user_representation()`.
7. Update `multi_validator.py` to set `request.state.org_scope`.
8. Add `get_org_scope()` dependency in `src/dependencies.py`.
9. Add `TENANT-USER` role to `src/utils/constants.py`.
10. **All existing tests pass without modification** (admin keys still have org_id=NULL; everything backfilled into default/system org).

### Phase 2 — Enforcement (still backwards-compatible)
1. Add four decorators: `@enforce_org_scope` (path), `@enforce_body_org_scope` (body), `@enforce_query_org_scope` (query). Pattern C is repository-level, no decorator.
2. Apply pattern-A decorator to every endpoint with `{task_id}` in path.
3. Apply pattern-B decorator to all 10 body-task_id endpoints from the audit (excluding the 2 admin-only system-config endpoints).
4. Apply pattern-D decorator to all 7 query-param `task_ids` endpoints.
5. Update repository methods to accept `org_scope` and inject filter when set:
   - `inference_repository.get_inference`
   - `span_repository.get_trace_by_id`, `get_span_by_id`, `get_session_by_id`, `compute_span_metrics`
   - `feedback_repository.create_feedback` (resource-lookup-before-write)
   - `datasets_repository._get_db_dataset` (and all callers)
   - `agentic_notebook_repository._get_db_notebook` (and all callers)
   - `agentic_prompt_repository._get_db_prompt` (and all callers)
   - `agentic_experiment_repository._get_db_experiment` (and all callers)
   - `prompt_experiment_repository._get_db_experiment` (and all callers)
   - `continuous_eval_repository.get_eval_by_id`, run lookups
   - `chat_repository.get_conversation_by_id` and message/regenerate paths
   - `chatbot_repository.get_chatbot_by_id`
   - `annotation_repository.get_annotation_by_id`
   - `tasks_repository.get_task_by_id` and list methods
6. Add `TENANT-USER` to the permission frozensets per the table above. Explicitly **omit** `TRACES_WRITE` (decision 14).
7. **Existing admin keys (org_id=NULL) continue to work unchanged.** Tests confirm this.

**Estimate:** human ~10-14 days / CC ~8-10 hours. Up slightly from rev 3 due to org-scope resolution adding a task→org lookup in every decorator (cacheable on `request.state` to avoid re-fetching).

### Phase 3 — Org management + provisioning flows
1. New `organizations_repository.py` and routes (`POST/GET/DELETE /api/v2/organizations*`).
2. Extend `POST /api/v2/tasks` with optional `org_id` (defaults to default org) and `create_tenant_key` (Flow A).
3. Extend `POST /api/v2/organizations/{org_id}/api_keys` to mint org-scoped tenant keys (Flow A alternative).
4. Add `POST /api/v2/tenant/signup` endpoint (Flow B) behind `ENABLE_PUBLIC_TENANT_SIGNUP` feature flag. Creates org + task + key in one transaction.
5. Add rate limiting on the signup endpoint.

### Phase 4 — UI
1. Permissions check on login; cache role + org_scope in `AuthContext`.
2. Route guard: hide admin sections for `TENANT-USER`.
3. Task switcher filters to caller's org.

### Phase 5 — Verification + docs
1. End-to-end tests for org isolation (see Verification section).
2. CHANGELOG entries.
3. Customer-facing release note (multi-tenant is opt-in via the new org endpoints + feature flag; existing keys + tasks unaffected).

---

## Backwards Compatibility

Concrete claims:

1. **All existing API keys** have `org_id = NULL` after migration. Auth code paths for `org_id IS NULL` (admin keys) are identical to today.
2. **All existing tasks** are assigned to the `default` org (or `system` org if `is_system_task=True`). Single-tenant customer deployments operate exactly as before — they just happen to have one user-facing org.
3. **No existing endpoint changes shape.** New optional fields only (`org_id` and `create_tenant_key` on task creation; the signup response and org endpoints are net-new).
4. **No existing client SDK breaks.** Aggregate endpoints stay shape-compatible — admin keys see the full list, tenant keys see an org-scoped subset.
5. **Existing role frozensets are not narrowed.** `TENANT-USER` is added to relevant frozensets; existing roles are not removed.
6. **`ENABLE_PUBLIC_TENANT_SIGNUP` is `false` by default.** Customer deployments never expose the public endpoint unless explicitly enabled.

Risk areas where someone could miss something:
- A repository method that doesn't yet accept `org_scope` will silently return cross-org data to a tenant key. Mitigation: lint rule or PR-time check that every repository method touching task-scoped tables accepts `org_scope`. See Verification → fuzz test.
- New endpoints added in the future may forget `@enforce_org_scope`. Mitigation: same lint approach. Document the requirement in the routers' README.
- The task → org lookup in every decorator adds a DB hit per request. Mitigation: cache the resolved task on `request.state` so handler-side repository calls don't re-fetch.

---

## Verification

### Unit tests
- Migrations produce `organizations` table, `tasks.org_id` (NOT NULL with backfill), `api_keys.org_id` (nullable), `org_id` columns on Migration 3 tables.
- Default org + system org rows exist after Migration 0; partial unique index prevents a second system org.
- `MultiMethodValidator` sets `request.state.org_scope` correctly for API key, JWT, and admin paths.
- `@enforce_org_scope` raises 404 when path's task_id resolves to an org other than caller's.
- `@enforce_body_org_scope` raises 404 when body field's task resolves to a different org; 400 when field is missing.
- `@enforce_query_org_scope` raises 403 when `task_ids` contains anything outside caller's org; expands to all-org-tasks when `task_ids` is absent.
- Repository methods (Pattern C): `get_X(id, org_scope=O2)` returns None for a row whose task is in O1. With `org_scope=None`, the row is returned regardless.
- `permission_checker` correctly admits/rejects `TENANT-USER` per the updated frozensets, including the negative case for `TRACES_WRITE`.

### Integration tests
- Seed: two orgs (O1, O2), each with two tasks (O1→{T1a, T1b}, O2→{T2a, T2b}). Mint tenant keys K1→O1, K2→O2. Mint admin key A. Seed each task with at least one inference, feedback row, trace, span, annotation, dataset, notebook, prompt, experiment, and conversation.
- **Multi-task within org:** K1 reads both T1a and T1b. Expect success on both — K1 sees all of O1's tasks.
- **Pattern A — Path scope:** K1 hits every `/tasks/{task_id}/*` endpoint with `task_id=T2a`. Expect 404.
- **Pattern B — Body scope:** K1 POSTs to every body-task_id endpoint with `body.task_id=T2a`. Expect 404. With `body.task_id=T1a`, expect success.
- **Pattern C — Resource ID scope:** K1 calls every resource-id-scoped GET/PATCH/DELETE with a T2a-owned resource ID. Expect 404. **Feedback planting test:** K1 POSTs `/api/v2/feedback/{T2a_inference_id}` — expect 404, verify no feedback row written.
- **Pattern D — Query-param scope:** K1 calls every `task_ids`-accepting endpoint with `?task_ids=T2a`. Expect 403. With no `task_ids`, expect transparent filter to {T1a, T1b}. With `?task_ids=T1a,T1b`, expect 200.
- **Trace upload blocked for tenants:** K1 POSTs `/api/v1/traces` with any payload. Expect 403. A (admin) posts the same payload — expect 201, spans land per existing logic (`arthur.task` → service_name_map → UNMAPPED).
- **Cross-org enumeration:** K1 calls `GET /api/v2/tasks`, expects {T1a, T1b}. K1 calls `GET /api/v2/tasks/search`, expects same.
- **Admin still works:** A calls every endpoint above; expects unchanged behavior (full visibility, no filtering).
- **Aggregate filtering:** K1 calls `GET /api/v2/usage/tokens`; expects sum across O1's tasks only.
- **Admin-only blocks (Pattern E):** K1 calls `POST /api/v1/traces`, `POST /api/v2/organizations`, `POST /auth/api_keys/`, `GET /users`, `GET /api/v2/configuration`, `POST /api/v2/default_rules`, `POST /api/chat/default_task`, `PUT /api/v1/model_providers/anthropic`, `POST /api/v1/secrets/rotation`. Expect 403 each.
- **Model provider reads (Option 0):** K1 calls `GET /api/v1/model_providers`. Expect 200 with `[{provider, enabled}]`. Verify no credential fields in response.
- **System org isolation:** K1 attempts to read any task in the `system` org via every pattern. Expect 404 on every one. Admin (A) can read system tasks.
- **API key tampering:** K1 calls `DELETE /auth/api_keys/deactivate/{A_key_id}`. Expect 403.
- **Tenant signup flow A:** A calls `POST /api/v2/tasks` with `create_tenant_key=true` and no `org_id` → task lands in default org, key minted for default org. A calls again with `org_id=O1` → task lands in O1, key minted for O1.
- **Tenant signup flow B:** anonymous request to `/api/v2/tenant/signup` with feature flag off returns 404. With flag on, returns 201 + a fresh org + task + key. Subsequent calls share rate limit per IP.
- **Default org backfill:** existing tasks (no `is_system_task`) now have `org_id = default_org.id`. System tasks have `org_id = system_org.id`. Admin key sees all of them.

### Fuzz / coverage test
A test that enumerates every FastAPI route and asserts the right enforcement is wired up. Failing assertion = a developer added an endpoint without scope enforcement.

```python
# Pseudocode
for route in app.routes:
    handler = route.endpoint
    # Pattern A
    if "task_id" in route.path_params:
        assert has_decorator(handler, enforce_org_scope), \
            f"{route.path} has {{task_id}} but is missing @enforce_org_scope"
    # Pattern B
    body_model = inspect_body_model(handler)
    if body_model is not None and "task_id" in body_model.__fields__:
        assert has_decorator(handler, enforce_body_org_scope), \
            f"{route.path} body has task_id but missing @enforce_body_org_scope"
    # Pattern D
    if "task_ids" in inspect_query_params(handler):
        assert has_decorator(handler, enforce_query_org_scope), \
            f"{route.path} accepts task_ids query but missing @enforce_query_org_scope"
```

Pattern C (repository-level) is harder to assert generically. Coverage test for repos: assert every method on a `TaskScopedRepository` base class that takes a resource_id-shaped parameter also accepts `org_scope: UUID | None`. Stretch goal — easier to enforce via code review.

### Manual smoke test
1. Run engine in single-tenant mode (default config). Existing admin key sees all tasks in default + system orgs.
2. Run engine with `ENABLE_PUBLIC_TENANT_SIGNUP=true`. `curl POST /api/v2/tenant/signup` returns a fresh org + task + key.
3. Paste tenant key into UI. Confirm UI loads tasks within that org only, admin nav hidden.
4. Try to hit admin endpoint with tenant key. Confirm 403.
5. Send inferences via tenant key. Confirm they land in tasks within tenant's org.
6. Try to upload traces via tenant key. Confirm 403.
7. Admin creates a second task in the tenant's org via `POST /api/v2/tasks` with `org_id`. Tenant now sees both tasks.
8. Spin up second tenant. Confirm cross-org isolation.

### Performance baseline
- Tenant key auth path adds one extra column read (`org_id`) per request. Negligible.
- Each Pattern A/B decorator adds a task → org lookup. Cache the resolved task on `request.state` so handler-side repository calls don't re-fetch (~1 lookup per request).
- Repository filter injection adds `WHERE org_id = X` to queries. With indexes from Migration 3, this is fast on hot tables.
- Public signup endpoint: rate-limit + DB transaction. Budget under 500ms.

---

## Open Questions / Risks

1. **Task name collisions** in Flow B. Multiple users hitting `/tenant/signup` simultaneously could collide on auto-generated org or task names. Mitigation: use `demo-{8-char-uuid}` and accept tiny collision probability, or make name unique constraint and retry on conflict.
2. **Default-rule visibility** to tenants. Defaults are global today; if per-org default rules ever ship, this assumption needs revisiting.
3. **Audit logging.** Existing audit log (if any) doesn't track `org_scope`. Out of scope for v1, but flagging.
4. **Demo env data retention.** Public signup creates orgs + tasks freely; without a cleanup job, the demo DB grows forever. Recommend a daily job: archive orgs (and their tasks) where every task has `is_autocreated=true` and `created_at < now() - 7 days`. Out of scope for this design doc.
5. **Rate limit tuning.** 10/hour/IP is a guess. May need adjustment based on actual demo traffic patterns.
6. **Org deletion semantics.** `DELETE /api/v2/organizations/{org_id}` — cascade vs refuse if non-empty? Plan refuses by default unless `?force=true`. Open question whether admins want a UI flow for this in v1.
7. **Item 7 in the feedback was empty.** The original feedback list had a trailing "7." with no content. Flagging here so the team can fill it in.

---

## Files To Be Modified (concrete list)

### Backend — migrations
- `alembic/versions/{new}_create_organizations_table.py` (NEW — Migration 0)
- `alembic/versions/{new}_add_org_id_to_tasks.py` (NEW — Migration 1)
- `alembic/versions/{new}_add_org_id_to_api_keys.py` (NEW — Migration 2)
- `alembic/versions/{new}_denorm_org_id_to_rule_results.py` (NEW — Migration 3)

### Backend — models / schemas
- `src/db_models/organization_models.py` (NEW)
- `src/db_models/task_models.py` (add `org_id` FK + relationship)
- `src/db_models/auth_models.py` (api_keys `org_id`)
- `src/db_models/inference_models.py` (feedback `task_id`, `org_id`)
- `src/db_models/rule_result_models.py` (denorm `task_id`, `org_id`)
- `src/db_models/agentic_annotation_models.py` (denorm `task_id`, `org_id`)
- `src/schemas/internal_schemas.py` (Organization, Task `org_id`, ApiKey `org_id`, User propagation)
- `src/schemas/enums.py:70` (extend permission frozensets with TENANT-USER; add ORG_WRITE / ORG_READ)

### Backend — auth + dependencies + utils
- `src/auth/multi_validator.py:25-74` (set `request.state.org_scope`)
- `src/dependencies.py` (new `get_org_scope()` dependency)
- `src/utils/constants.py:194` (add TENANT-USER role)
- `src/utils/users.py` (new decorators: `enforce_org_scope`, `enforce_body_org_scope`, `enforce_query_org_scope`)
- `src/utils/config.py` (add `ENABLE_PUBLIC_TENANT_SIGNUP` flag)

### Backend — repositories
- `src/repositories/organizations_repository.py` (NEW)
- `src/repositories/api_key_repository.py`
- `src/repositories/tasks_repository.py` (add `org_id` support + `get_tasks_by_org`)
- `src/repositories/inference_repository.py`
- `src/repositories/feedback_repository.py`
- `src/repositories/rule_result_repository.py`
- `src/repositories/telemetry_repository.py`
- `src/repositories/span_repository.py`
- `src/repositories/datasets_repository.py`
- `src/repositories/agentic_notebook_repository.py`
- `src/repositories/agentic_prompt_repository.py`
- `src/repositories/agentic_experiment_repository.py`
- `src/repositories/prompt_experiment_repository.py`
- `src/repositories/continuous_eval_repository.py`
- `src/repositories/chat_repository.py`
- `src/repositories/chatbot_repository.py`

### Backend — routers
- `src/routers/v2/organization_routes.py` (NEW — admin org management)
- `src/routers/v2/task_management_routes.py` (extend POST `/tasks` with `org_id`, `create_tenant_key`; add `/tenant/signup`)
- `src/routers/api_key_routes.py` (apply scope checks)
- `src/routers/v1/trace_api_routes.py` (POST `/traces` becomes admin-only; reads get Pattern C/D scope)
- Apply `@enforce_org_scope` to all `{task_id}` path endpoints in:
  - `src/routers/v2/task_management_routes.py`
  - `src/routers/v1/continuous_eval_routes.py`
  - `src/routers/v1/llm_eval_routes.py`
  - `src/routers/v2/validate_routes.py`
- Apply `@enforce_body_org_scope` to:
  - `src/routers/v1/legacy_span_routes.py` (POST /inferences)
  - `src/routers/v1/agentic_prompt_routes.py`
  - `src/routers/v1/agentic_experiment_routes.py`
  - `src/routers/v1/agentic_notebook_routes.py`
  - `src/routers/v1/prompt_experiment_routes.py`
  - `src/routers/v1/agent_polling_routes.py`
  - `src/routers/v1/chatbot_routes.py`
  - `src/routers/v1/chat_routes.py`
  - `src/routers/v2/chat_routes.py`
- Apply `@enforce_query_org_scope` to:
  - `src/routers/v1/trace_api_routes.py` (GET /traces, /traces/spans, /traces/sessions, /traces/users)
  - `src/routers/v1/legacy_span_routes.py` (GET /inferences)
  - `src/routers/v2/query_routes.py`
  - `src/routers/v2/feedback_routes.py`

### UI
- `ui/src/lib/auth.ts`
- `ui/src/contexts/AuthContext.tsx`
- Task switcher / nav guard component (file location TBD)

### Tests
- `tests/integration/test_multi_tenant_isolation.py` (NEW — covers all integration test cases above)
- `tests/integration/test_org_management.py` (NEW — admin org CRUD)
- `tests/unit/test_enforce_org_scope.py` (NEW)
- `tests/unit/test_org_repository.py` (NEW)
- `tests/coverage/test_route_scope_coverage.py` (NEW — the fuzz test)

### Docs
- `docs/MULTI_TENANCY_DESIGN.md` (this document)
- `CHANGELOG.md` (new entry)

---

## What This Doc Is Not Doing

Calling these out so they don't get lost:

- Not adding Postgres RLS. (Future v2 hardening.)
- Not adding per-tenant rate limits. (Just an IP rate limit on signup.)
- Not adding tenant-aware audit logging. (Future work.)
- Not changing the JWT/Keycloak admin user flow. (Untouched.)
- Not touching documents/embeddings. (Tenant keys 403 in v1.)
- Not building a tenant-admin tier between admin and tenant. (Could be added in v2 by introducing a new role; the org boundary makes it natural — a "tenant-admin" could mint keys within their own org.)
- **Not allowing tenant trace uploads.** `POST /api/v1/traces` is admin-only in v1 (decision 14). Re-enabling for tenants requires solving both the explicit-task_id-in-protobuf vector and the service-name-fallback vector. Either build the strict-reject + disable-fallback path from earlier revisions, or design an explicit per-org trace ingest token. Deferred to v2.
- **Not validating `feedback.user_id` / `inference.user_id` body fields.** Within-tenant only — not a cross-org breach — so deferred. Affected endpoints: `POST /api/v2/feedback/{inference_id}`, `POST /api/v2/validate_prompt`, `POST /api/v2/tasks/{task_id}/validate_response/{inference_id}`.
- **Not implementing BYOK (bring-your-own-keys) model providers.** Deferred to v2 — same endpoints will start returning org-scoped providers in addition to globals.
- **Not implementing org-scoped default rules or org-scoped configuration.** Defaults remain global in v1. If per-org defaults become a requirement, that's a v2 schema change.
- **Not auto-creating user-facing orgs for existing customer deployments.** All existing tasks land in the synthetic `default` org. Customers can introduce additional orgs at their own pace; until they do, single-tenant behavior is preserved.
