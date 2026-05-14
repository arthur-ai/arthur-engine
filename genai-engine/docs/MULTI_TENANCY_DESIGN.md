# GenAI Engine — Multi-Tenant Tasks Design Doc

> **Status:** Draft for team review
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

## Endpoint-by-endpoint policy

Symbols: ✅ = allowed for tenant keys, ❌ = 403/404, 🪟 = allowed but filtered to their task.

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
| `GET /api/v1/model_providers` | ❌ | Leaks infra. |
| `GET /api/v1/model_providers/{p}/available_models` | ✅ | Read-only model registry. |
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
1. Add `@enforce_task_scope` decorator.
2. Apply to every endpoint that accepts a path `task_id` (the task-scoped endpoints).
3. Update repository methods to accept `task_scope` and inject filter when set.
4. Update list/search/usage endpoints to filter by `task_scope` when set.
5. Add `TENANT-USER` to the permission frozensets per the table above.
6. **Existing admin keys (task_id=NULL) continue to work unchanged.** Tests confirm this.

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
- `@enforce_task_scope` raises 404 when scope mismatches path.
- `permission_checker` correctly admits/rejects `TENANT-USER` per the updated frozensets.

### Integration tests
- Create two tasks (T1, T2) and tenant keys (K1→T1, K2→T2) and one admin key (A).
- **Cross-task read isolation:** K1 hits every task-scoped GET endpoint with `task_id=T2`. Expect 404 on every one.
- **Cross-task write isolation:** K1 tries to POST inferences, traces, rules, metrics for T2. Expect 404/403 on every one.
- **Cross-task enumeration:** K1 calls `GET /api/v2/tasks`, expects only T1 in the list. K1 calls `GET /api/v2/tasks/search`, expects only T1.
- **Admin still works:** A calls everything; expects unchanged behavior.
- **Aggregate filtering:** K1 calls `GET /api/v2/usage/tokens`; expects only T1's usage.
- **Admin-only blocks:** K1 calls `POST /auth/api_keys/`, `GET /users`, `GET /api/v2/configuration`, `POST /api/v2/default_rules`. Expect 403 each.
- **Tenant signup flow A:** A calls `POST /api/v2/tasks` with `create_tenant_key=true`; receives a new task + key. New key only sees that task.
- **Tenant signup flow B:** anonymous request to `/api/v2/tenant/signup` with feature flag off returns 404. With feature flag on, returns 201 + a new task + key. Subsequent calls share rate limit per IP.

### Fuzz / coverage test
A test that enumerates every FastAPI route in the app, identifies which take a `task_id` in path/query, and asserts each one has `@enforce_task_scope` applied. Failing assertion = a developer added an endpoint without scope enforcement.

```python
# Pseudocode
for route in app.routes:
    if "task_id" in route.path_params:
        assert has_decorator(route.endpoint, enforce_task_scope), \
            f"{route.path} takes task_id but is missing @enforce_task_scope"
```

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

### Backend
- `alembic/versions/{new}_add_task_id_to_api_keys.py` (new)
- `alembic/versions/{new}_denorm_task_id_to_rule_results.py` (new)
- `src/db_models/auth_models.py`
- `src/db_models/inference_models.py` (feedback `task_id`)
- `src/db_models/rule_result_models.py`
- `src/db_models/agentic_annotation_models.py`
- `src/schemas/internal_schemas.py`
- `src/auth/multi_validator.py:25-74`
- `src/dependencies.py`
- `src/utils/constants.py:194` (new role)
- `src/utils/users.py` (new `enforce_task_scope` decorator)
- `src/schemas/enums.py:70` (extend frozensets)
- `src/repositories/api_key_repository.py`
- `src/repositories/tasks_repository.py`
- `src/repositories/inference_repository.py`
- `src/repositories/rule_result_repository.py`
- `src/repositories/telemetry_repository.py`
- `src/routers/v2/task_management_routes.py` (extend POST `/tasks` + add `/tenant/signup`)
- `src/routers/api_key_routes.py` (apply scope checks)
- (Most other router files in `src/routers/v1/` and `src/routers/v2/` for `@enforce_task_scope`)

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
