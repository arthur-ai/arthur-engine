# GenAI Engine — Multi-Tenant Organizations

> **Status:** Design proposal
> **Author:** Ian McGraw
> **Date:** 2026-05-15

## Contents

1. [Overview](#1-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Tenant Model](#3-tenant-model)
4. [Schema Changes](#4-schema-changes)
5. [Tenant Provisioning](#5-tenant-provisioning)
6. [Authentication & Authorization](#6-authentication--authorization)
7. [Enforcement Patterns](#7-enforcement-patterns)
8. [Endpoint Policy](#8-endpoint-policy)
9. [UI Changes](#9-ui-changes)
10. [Backwards Compatibility](#10-backwards-compatibility)
11. [Implementation Plan](#11-implementation-plan)
12. [Verification](#12-verification)
13. [Future Work](#13-future-work)
14. [Open Questions](#14-open-questions)

---

## 1. Overview

GenAI Engine today is single-tenant: every API key sees every task. This document describes how the engine becomes multi-tenant.

**The change in one sentence:** introduce an `organization` entity that owns tasks and scope API keys to a single org, so a tenant key only reaches the tasks and resources within its org.

**What v1 ships:**

- An `organizations` table with two seeded rows: `default` and `system`
- `org_id` on `tasks`, on `api_keys`, and (denormalized) on the high-volume tables that today only reach an org via multi-hop joins
- A new `TENANT-USER` role plus five enforcement patterns that gate every endpoint touching task-scoped data
- A public signup endpoint, feature-flagged off by default, that creates `(org, task, api_key)` in a single transaction
- A new `GET /users/me` endpoint so the UI can discover its identity and org on login

**What stays the same:**

- Existing admin keys keep cross-org access (their `org_id` is `NULL`)
- Existing tasks migrate into the `default` org; tasks with `is_system_task=True` migrate into the `system` org
- No existing endpoint changes shape; no existing client SDK breaks
- Customer single-tenant deployments leave the feature flag off and behave exactly as today

**Threat model in one sentence:** a tenant API key with `org_scope = O1` cannot read, modify, or enumerate any resource belonging to any other org, regardless of which endpoint or pattern the resource lives behind.

Enforcement is API-layer only in v1. Postgres RLS is not used in this revision; see Future Work for the v2 hardening path.

---

## 2. Goals & Non-Goals

### Goals

1. **Organizations as the tenant boundary.** A new `organizations` entity owns tasks. Each task belongs to exactly one org. A tenant API key is scoped to one org and reaches every task within it.
2. **Org-scoped API keys.** A new nullable `api_keys.org_id` column. `NULL` preserves existing admin behavior (cross-org access); non-null is a tenant key.
3. **Tenant provisioning via public signup only.** A single endpoint, gated by a feature flag (default off), creates `(org, task, api_key)` in one transaction. No admin endpoints for org management or for minting keys.
4. **Tenants can manage their own tasks.** Create, delete, and unarchive via the existing `/api/v2/tasks` endpoints. No request body changes — caller identity determines org.
5. **API-layer enforcement.** Five patterns cover every code path that touches task-scoped data: path, body, resource-id, query-param, and admin-only.
6. **Transparent filtering.** List and aggregate endpoints stay shape-compatible. Tenant keys see scoped results; admin keys see everything; no SDK breaks.
7. **Minimal UI changes.** One new endpoint (`GET /users/me`) on login drives a conditional render branch for tenant mode (no admin nav, scoped task switcher).

### Non-Goals

- **User accounts for tenants.** No JWT signup, no Keycloak self-service, no email verification. The pasted API key is the entire identity.
- **Tenant trace uploads.** `POST /api/v1/traces` stays admin-only. The endpoint accepts opaque protobuf payloads with both an `arthur.task` attribute and a service-name fallback map; neither is safe to expose to tenants in v1. Tenants can still read traces in their org.
- **Bring-your-own-keys model providers.** Provider credentials stay system-wide and admin-only. Tenants read the existing `GET /api/v1/model_providers*` endpoints (the read responses contain no credentials).
- **Rate limits or quotas.** Not introduced in v1. The demo env can address abuse operationally if it becomes a concern.
- **Postgres Row-Level Security.** v1 is API-layer only. RLS as a v2 hardening pass is documented in Future Work.
- **New permission framework.** Extend the existing `PermissionLevelsEnum`; do not introduce a new authz system.
- **Documents and embeddings multi-tenancy.** Tenant keys receive 403 on `/documents/*` and embedding endpoints in v1. Owner-scoped today; the multi-tenant story requires schema work we're deferring.
- **Admin endpoints for org management.** Provisioning is exclusively via the public signup endpoint. Admins inspecting orgs query the database directly in v1.
- **Per-org default rules, model providers, or app configuration.** Defaults remain global. Per-org versions would be a v2 schema change.
- **Tenant-aware audit logging.** Existing audit logging is not extended to track org_scope in v1.

---

## 3. Tenant Model

### The hierarchy

```
organizations
    │
    │ 1 → many
    ▼
tasks  (each task belongs to exactly one org)
    │
    │ 1 → many
    ▼
resources  (inferences, traces, feedback, rule results, datasets,
            notebooks, prompts, experiments, conversations,
            annotations, ...)
```

Every task-scoped resource in the system reaches an org by following its `task_id` foreign key. The org is therefore reachable for every row that matters to multi-tenancy, either directly (for `tasks`) or transitively through `task_id` (for everything else).

### Two special organizations

Two orgs are seeded by migration and have semantics distinct from the orgs that get created later:

- **`default` org** — every task that existed before multi-tenancy migrates into this org. Tasks that admin keys create without a tenant context also land here. Single-tenant customer deployments effectively operate as "one user-facing org" — admins see the `default` org's tasks and don't need to think about orgs at all.
- **`system` org** — internal tasks (`tasks.is_system_task = True`) migrate into this org. Tenants can never reach the `system` org by any path because no tenant API key is ever issued with `org_id = system_org.id`. Admins see system tasks via cross-org access just as today.

No other special orgs exist. All other orgs are created exclusively by the public signup flow (section 5).

### API keys

An API key carries an optional `org_id`. The semantics:

| `org_id` value | Caller type | Access |
|---|---|---|
| `NULL` | Admin | Cross-org; sees everything (existing behavior) |
| Non-NULL (matches some org) | Tenant | Scoped to that one org's tasks and resources |

This is the only authorization difference between an admin and a tenant. Both pass through the same auth path; the `org_id` column is what determines scope.

### Multi-task per org

A single org can contain many tasks. A tenant key sees and can act on every task in its org. The expected pattern on the demo environment is "one user, one org, starts with one task, can create more as needed." Nothing in the model precludes an org with many tasks shared across multiple keys — that's a v2 capability if we ever issue multiple keys per org.

### How a request resolves an org

When any endpoint receives a request that touches task-scoped data, the engine identifies the affected task (from URL path, request body, query string, or resource ID lookup) and resolves it to a single `org_id` via the `tasks.org_id` foreign key. That `org_id` is compared to the caller's `org_scope` (the `org_id` on their API key). A mismatch returns 404. Section 7 details the five patterns by which a task is identified across the endpoint surface.

---

## 4. Schema Changes

Four Alembic migrations, applied in order. All are designed to run safely against a live database: nullable columns are added first, backfilled from existing data, then constrained to NOT NULL.

### Migration 0 — Create `organizations` table; seed `default` and `system` orgs

```sql
CREATE TABLE organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX idx_organizations_name      ON organizations(name);
CREATE UNIQUE INDEX idx_organizations_is_system ON organizations(is_system) WHERE is_system = TRUE;

INSERT INTO organizations (name, is_system) VALUES ('default', FALSE);
INSERT INTO organizations (name, is_system) VALUES ('system',  TRUE);
```

The partial unique index on `is_system` enforces "at most one system org." The `default` org has no special flag — it's a regular org used as the fallback target for admin-created tasks and for the migration backfill in step 1.

### Migration 1 — Add `org_id` to `tasks`; backfill; enforce NOT NULL

```sql
-- Step 1: add nullable
ALTER TABLE tasks ADD COLUMN org_id UUID REFERENCES organizations(id);

-- Step 2: backfill
UPDATE tasks
   SET org_id = (SELECT id FROM organizations WHERE name = 'system')
 WHERE is_system_task = TRUE;

UPDATE tasks
   SET org_id = (SELECT id FROM organizations WHERE name = 'default')
 WHERE org_id IS NULL;

-- Step 3: enforce NOT NULL
ALTER TABLE tasks ALTER COLUMN org_id SET NOT NULL;

CREATE INDEX idx_tasks_org_id ON tasks(org_id);
```

Two-phase nullable-then-NOT-NULL keeps the migration safe to apply while the engine is live. Rows existing during the migration window get backfilled before the constraint is added.

### Migration 2 — Add `org_id` to `api_keys` (nullable)

```sql
ALTER TABLE api_keys
  ADD COLUMN org_id UUID NULL REFERENCES organizations(id);

CREATE INDEX idx_api_keys_org_id ON api_keys(org_id) WHERE org_id IS NOT NULL;
```

All existing keys remain `NULL` after this migration — admin behavior is preserved. Tenant keys minted by the signup flow (section 5) carry a non-null `org_id`.

### Migration 3 — Denormalize `org_id` onto high-volume task-scoped tables

The following tables today reach `task_id` via 1-3 hop joins. Multi-tenancy enforcement needs a direct filter on org membership, so we denormalize `org_id` onto each of them. We do **not** also denormalize `task_id`: existing per-task queries already work via single-hop joins to the parent tables, and adding both columns doubles write cost without solving a tenant-isolation problem (see Future Work for the full rationale).

| Table | Today reaches `task_id` via | Backfill source |
|---|---|---|
| `inference_feedback` | `inferences.task_id` (1 hop) | `inferences.task_id → tasks.org_id` |
| `prompt_rule_results` | `inference_prompts → inferences.task_id` (2 hop) | same chain |
| `response_rule_results` | `inference_responses → inferences.task_id` (2 hop) | same chain |
| `rule_result_details` | via prompt/response rule_result (3 hop) | same chain |
| `agentic_annotations` | `trace_metadata.task_id` (1 hop) | `trace_metadata.task_id → tasks.org_id` |
| `hallucination_claims`, `pii_entities`, `keyword_entities`, `regex_entities`, `toxicity_scores` | same as `rule_result_details` (3 hop) | same chain |

For each table, the migration follows the same shape:

```sql
ALTER TABLE <table> ADD COLUMN org_id UUID REFERENCES organizations(id);
-- backfill with the appropriate join chain to tasks.org_id
UPDATE <table> SET org_id = ... FROM ... WHERE ...;
ALTER TABLE <table> ALTER COLUMN org_id SET NOT NULL;
CREATE INDEX idx_<table>_org_id ON <table>(org_id);
```

The `SET NOT NULL` after backfill is intentional: if any row's parent chain is broken (orphan data), the migration fails loudly rather than silently allowing unmatchable rows.

On future inserts, the originating repository method passes `org_id` explicitly alongside `task_id`. App-level discipline rather than triggers; the write path for these tables already flows through a small number of well-defined repositories.

Estimated migration time on a typical customer database is under 5 minutes for tables with <10M rows. High-volume deployments should use `CREATE INDEX CONCURRENTLY` and chunked backfill; either is straightforward to add to the migration if needed.

### Tables left unchanged

Tables that already have `task_id` natively get no schema change. The `task_id → tasks.org_id` join is one hop from `inferences`, `traces`, `trace_metadata`, `datasets`, `experiments`, `notebooks`, `prompts`, `chat_conversations`, etc. Fast enough that denormalization would add cost without measurable benefit. If a future hot path demonstrates the join is the bottleneck, the same denormalization pattern can be applied as a follow-up.

---

## 5. Tenant Provisioning

A single endpoint, gated by a feature flag, is the only way to create a new org and an org-scoped API key. There are no admin endpoints for org management in v1.

### Endpoint

```
POST /api/v2/tenant/signup       (no auth required)
```

### Feature flag

The endpoint exists in every deployment but only responds when `ENABLE_PUBLIC_TENANT_SIGNUP` is `true` in `src/utils/config.py`. Default: `false`. With the flag off, the endpoint returns 404 — clients cannot distinguish "feature unavailable" from "endpoint doesn't exist," which is the desired behavior on production customer deployments.

### Request and response

The request body is empty. The endpoint generates all identifiers server-side.

```
POST /api/v2/tenant/signup
Body: (none)

201 Created
{
  "org_id":    "uuid",
  "task_id":   "uuid",
  "task_name": "demo-a3f9b2c1",
  "api_key":   "<one-time visible Bearer token>"
}
```

The `api_key` value is the only place a tenant ever sees the raw token. After this response, the database stores only its bcrypt hash. The client must capture it or lose access.

### Server-side transaction

The signup flow runs in a single database transaction so partial state can never appear:

```
BEGIN TRANSACTION
  1. INSERT organizations (name = "demo-{short_uuid}", is_system = false)
  2. INSERT tasks (name = "demo-{short_uuid}", org_id = new_org.id)
  3. Apply default rules to the new task (existing logic)
  4. INSERT api_keys (
        key_hash = bcrypt(random_token),
        roles    = [TENANT-USER],
        org_id   = new_org.id
     )
COMMIT
```

If any step fails (constraint violation, DB error), the entire transaction rolls back — no orphan org or unattached key is left behind.

### Implementation notes

- Reuse `tasks_repository.create_task()` and `api_key_repository.create_api_key()`. Add a new `organizations_repository.create_organization()`.
- The org name and task name share the same 8-char hex suffix for readability (`demo-a3f9b2c1`). Suffix is generated via `secrets.token_hex(4)`. Collision probability is negligible; the unique constraint on `organizations.name` catches collisions and the handler retries once.
- Default rule application reuses the existing logic from `POST /api/v2/tasks` so a freshly signed-up tenant inherits the same default rules a regular task would.

### What the tenant does next

After signup, the tenant:

1. Captures the `api_key` from the response.
2. Pastes it into the genai-engine UI's existing login form, or sends it as `Authorization: Bearer <token>` on API calls.
3. Has full access to their one initial task (default rules applied). Can create more tasks within their org via `POST /api/v2/tasks` (section 8 covers the policy). Cannot reach any other org's data.

---

## 6. Authentication & Authorization

### Authentication flow

Authentication today resolves a Bearer token to a `User` object via the existing `MultiMethodValidator`. The flow is unchanged in v1; only the data carried alongside the user changes.

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
    │                       returns ApiKey(id, roles, org_id)   ◄── org_id NEW
    │
    └─── JWT path ───────► Keycloak / JWKS → User(roles)        (org_scope = None)
    │
    ▼
request.state.user_id  = user.id
request.state.org_scope = api_key.org_id   (None for JWT users)
    │
    ▼
@permission_checker(...)       (existing — role frozenset check)
@enforce_org_scope(...)        (NEW — see section 7)
    │
    ▼
Route handler
```

Two things change:

1. `api_key_repository.lookup_by_id_and_hash()` returns the new `org_id` column on the key.
2. `multi_validator.py` sets `request.state.org_scope` from `api_key.org_id`. JWT callers always have `org_scope = None`.

### Admin vs tenant

The single test that distinguishes a tenant from an admin is `request.state.org_scope`:

- `None` → admin or operator (JWT or admin API key). Cross-org access. Existing role checks proceed unchanged.
- Non-`None` → tenant. The role is `TENANT-USER` and the enforcement decorators in section 7 apply.

### New role: `TENANT-USER`

Add `TENANT_USER = "TENANT-USER"` to the role enum at `src/utils/constants.py:194`. Tenant keys are minted with `roles = ["TENANT-USER"]` (single role). The existing seven roles continue to work for admin and operator users.

### Permission frozenset additions

In `src/schemas/enums.py:70`, extend `PermissionLevelsEnum` to include `TENANT-USER` on the read/write actions tenants are allowed to perform within their org:

```python
TASK_READ           = frozenset([ORG_ADMIN, ORG_AUDITOR, TASK_ADMIN, TENANT_USER])
TASK_WRITE          = frozenset([ORG_ADMIN, TASK_ADMIN, TENANT_USER])    # create/delete/unarchive own org's tasks
INFERENCE_READ      = frozenset([..., TENANT_USER])
INFERENCE_WRITE     = frozenset([..., TENANT_USER])
FEEDBACK_WRITE      = frozenset([..., TENANT_USER])
DEFAULT_RULES_READ  = frozenset([..., TENANT_USER])                      # tenants need to see what defaults apply
USAGE_READ          = frozenset([..., TENANT_USER])                      # filtered to their org by section 7
MODEL_PROVIDER_READ = frozenset([..., TENANT_USER])                      # response models contain no credentials
```

`TENANT-USER` is deliberately **not** added to:

```
TRACES_WRITE          (POST /api/v1/traces stays admin-only; see section 8)
API_KEY_*             (tenants cannot mint or read keys)
USER_*                (no user-management surface for tenants)
MODEL_PROVIDER_WRITE  (provider credentials are admin-only)
DEFAULT_RULES_WRITE   (defaults are global)
APP_CONFIG_*
ROTATE_SECRETS
PASSWORD_RESET
```

### Identity introspection: `GET /users/me`

The UI needs to know who it's authenticated as on login. The existing `/users/permissions/check` endpoint is a per-permission probe and does not return identity. A new endpoint fills the gap:

```
GET /users/me                  (authenticated; any role)

200 OK
{
  "user_id":   "uuid-or-keycloak-sub",
  "roles":     ["TENANT-USER"],
  "org_scope": "uuid" | null,
  "org": {
    "id":   "uuid",
    "name": "demo-a3f9b2c1"
  } | null
}
```

- Admin callers see `org_scope = null` and `org = null`.
- Tenant callers see both populated.
- Decorated `@public_endpoint` (same pattern as `/users/permissions/check`); the handler raises 401 if `current_user is None` but does not apply a role frozenset check.

The UI caches the response in `AuthContext` and uses it to pick its render branch (section 9).

### Code changes touched by this section

- `src/db_models/auth_models.py` — `api_keys.org_id: Mapped[str | None]` FK to `organizations.id`.
- `src/db_models/organization_models.py` (new) — `Organization` ORM model.
- `src/schemas/internal_schemas.py` — `ApiKey` pydantic model gets `org_id: UUID | None`; `User.get_user_representation()` propagates it; new `Organization` schema; new `MeResponse` schema.
- `src/auth/multi_validator.py:25-74` — set `request.state.org_scope` alongside `user_id`.
- `src/dependencies.py` — new dependency `get_org_scope(request) -> UUID | None`.
- `src/utils/constants.py:194` — add `TENANT-USER` to the role enum.
- `src/schemas/enums.py:70` — extend frozensets per the list above.
- `src/repositories/api_key_repository.py` — `create_api_key()` accepts an `org_id` parameter (used by the signup flow in section 5).
- `src/repositories/organizations_repository.py` (new) — `create_organization`, `get_organization_by_id`, `get_organization_by_name`.
- `src/routers/user_routes.py` — add the `/me` handler.

---

## 7. Enforcement Patterns

Every endpoint that touches task-scoped data falls into one of five enforcement patterns, depending on how the affected task is identified in the request. The first four resolve a task ID to its `org_id` and compare against `request.state.org_scope`. The fifth is admin-only — never reachable by tenant keys.

### Pattern A — Path task_id

The endpoint takes `{task_id}` in its URL path. Example: `POST /api/v2/tasks/{task_id}/rules`.

Enforced by a decorator that resolves the path's task to its org and compares:

```python
def enforce_org_scope(path_param: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs["request"]
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)   # admin passthrough
            task_id = kwargs.get(path_param)
            task = tasks_repo.get_task_by_id(task_id)
            if task is None or str(task.org_id) != str(scope):
                raise HTTPException(404, "Task not found")
            request.state.cached_task = task          # cache for the handler
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

The resolved task is cached on `request.state` so handler-side repository calls don't re-fetch it. Mismatch returns 404 (not 403) to prevent enumeration.

### Pattern B — Body task_id

The endpoint accepts a `task_id` field in its request body. Example: `POST /api/v1/inferences` with body `{"task_id": "...", ...}`.

A decorator pulls the field off the parsed Pydantic body and applies the same resolution:

```python
def enforce_body_org_scope(body_field: str = "task_id"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs["request"]
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)
            body = next((v for v in kwargs.values() if hasattr(v, body_field)), None)
            body_task_id = getattr(body, body_field, None)
            if body_task_id is None:
                raise HTTPException(400, f"{body_field} required in body")
            task = tasks_repo.get_task_by_id(body_task_id)
            if task is None or str(task.org_id) != str(scope):
                raise HTTPException(404, "Task not found")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

Same 404-on-mismatch behavior.

### Pattern C — Resource-id-scoped (repository-level filter)

The endpoint takes a non-task resource ID in its path: `/inferences/{inference_id}`, `/agentic-prompts/{prompt_id}`, `/datasets/{dataset_id}`, etc. The task is reachable only via the resource's foreign keys.

No decorator. Every `get_X_by_id(...)` repository method that fetches a task-scoped resource accepts an optional `org_scope` parameter and applies the filter directly.

For tables that already have a denormalized `org_id` (section 4, Migration 3), the filter is one line:

```python
def get_feedback(self, feedback_id: str, org_scope: UUID | None = None):
    q = self.db_session.query(DatabaseFeedback).filter(DatabaseFeedback.id == feedback_id)
    if org_scope is not None:
        q = q.filter(DatabaseFeedback.org_id == str(org_scope))
    return q.first()
```

For tables without the denormalized column, the filter joins through `tasks`:

```python
def get_inference(self, inference_id: str, org_scope: UUID | None = None):
    q = self.db_session.query(DatabaseInference).filter(DatabaseInference.id == inference_id)
    if org_scope is not None:
        q = q.join(DatabaseTask, DatabaseTask.id == DatabaseInference.task_id) \
             .filter(DatabaseTask.org_id == str(org_scope))
    return q.first()
```

The handler always passes `org_scope=request.state.org_scope`. The query returns `None` when the row is missing OR when it belongs to a different org. The handler 404s on `None`. Admin keys (`org_scope=None`) skip the filter entirely.

This pattern lives in the repository instead of a decorator because handlers for resource-id endpoints almost always need to read the resource anyway. A decorator would have to fetch the resource separately and the handler would fetch it again. Pushing the filter into the existing fetch keeps it to one query.

### Pattern D — Query-param task_ids

The endpoint accepts a `task_ids` query parameter for filtering. Example: `GET /api/v2/inferences/query?task_ids=...`.

A decorator intersects the supplied task_ids with the caller's org:

```python
def enforce_query_org_scope(query_param: str = "task_ids"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs["request"]
            scope = request.state.org_scope
            if scope is None:
                return await func(*args, **kwargs)
            user_task_ids = kwargs.get(query_param) or []
            if not user_task_ids:
                # no filter supplied — expand to all tasks in caller's org
                kwargs[query_param] = [str(t.id) for t in tasks_repo.list_tasks_by_org(scope)]
            else:
                # filter supplied — every id must resolve to a task in caller's org
                tasks = tasks_repo.get_tasks_by_ids(user_task_ids)
                missing = set(user_task_ids) - {str(t.id) for t in tasks}
                outside = [t for t in tasks if str(t.org_id) != str(scope)]
                if missing or outside:
                    raise HTTPException(403, "task_ids include items outside caller's org")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

Mismatched IDs return 403 (not 404) because the caller explicitly named them — there is no enumeration concern to hide.

### Pattern E — Admin-only

Endpoints that operate on platform-level resources or system-wide configuration: `POST /api/v1/traces`, `POST /api/v2/default_rules`, `PUT /api/v1/model_providers/{p}`, `POST /api/v1/secrets/rotation`, `POST /users`, `DELETE /auth/api_keys/{id}`, `POST /api/v2/configuration`, etc.

No decorator change. These endpoints are gated by `@permission_checker` against frozensets that deliberately exclude `TENANT-USER` (section 6). Tenant keys hit `permission_checker` first and receive 403 before any handler logic runs.

### Failure mode summary

| Pattern | Match | Mismatch |
|---|---|---|
| A — Path | proceed | 404 |
| B — Body | proceed | 404 (400 if field missing) |
| C — Resource ID | proceed | 404 (row appears not to exist) |
| D — Query | proceed | 403 (caller explicitly named the IDs) |
| E — Admin-only | n/a | 403 from `permission_checker` |

404 is used wherever a tenant might enumerate; 403 is used where the caller explicitly named the disallowed resource.

### Why the patterns live where they do

- Decorators (A, B, D) work at the FastAPI dependency layer and check inputs that haven't reached the database yet. Cheap, declarative, easy to apply uniformly.
- Repository-level filter (C) works inside the data-access layer because the natural shape of a resource-id endpoint is "fetch the resource, then act on it." Filtering during fetch costs nothing extra and avoids the decorator double-fetch.
- Permission-checker exclusion (E) is the existing role frozenset mechanism, untouched.

A FastAPI app traversal test (section 12) asserts that every route that takes a `task_id` in path, body, or query has the corresponding decorator applied. New endpoints that forget the decorator fail the test.

---

## 8. Endpoint Policy

Symbols: ✅ allowed for tenant keys · ❌ 403 or 404 · 🪟 allowed but filtered to caller's org.

### One example per pattern

**Pattern A — Path task_id.** Example: `POST /api/v2/tasks/{task_id}/rules`. Decorated `@enforce_org_scope`. Tenant succeeds if the path's task is in their org; 404 otherwise. Every `/tasks/{task_id}/*` endpoint in v2 plus every `{task_id}` path in v1 (continuous_eval, llm_eval, validate) follows this pattern.

**Pattern B — Body task_id.** Example: `POST /api/v1/inferences` with body `{"task_id": "...", ...}`. Decorated `@enforce_body_org_scope`. Tenant succeeds if `body.task_id` is in their org; 404 otherwise. Used by ~10 POST endpoints across v1 (inferences, agentic-prompts, agentic-experiments, agentic-notebooks, prompt_experiments, agent_polling, chatbots, chat) and v2 chat.

**Pattern C — Resource-id-scoped.** Example: `GET /api/v1/inferences/{inference_id}`. Repository method `inference_repository.get_inference(id, org_scope)` filters at fetch time. Tenant gets the row only if its task belongs to their org; 404 otherwise. Used by ~35 endpoints across trace/span/session lookups, inference + feedback by-id, agentic prompt/experiment/notebook by-id, continuous eval by-id, prompt experiments by-id, chat conversations by-id, chatbots by-id, dataset by-id.

**Pattern D — Query-param task_ids.** Example: `GET /api/v2/inferences/query?task_ids=...`. Decorated `@enforce_query_org_scope`. No `task_ids` → decorator injects all of the caller's org's task IDs. With `task_ids` supplied, every value must resolve to a task in the caller's org or the request 403s. Used by `GET /api/v1/traces`, `/traces/spans`, `/traces/sessions`, `/traces/users`, `/inferences`, `/api/v2/inferences/query`, `/api/v2/feedback/query`.

**Pattern E — Admin-only.** Example: `POST /api/v1/traces`. Permission frozenset (`TRACES_WRITE`) excludes `TENANT-USER`. Tenant receives 403 from `permission_checker` before any handler logic runs.

### Per-area summary

| Area | Tenant access |
|---|---|
| Public utility (`/health`, `/docs`, `/openapi.json`, `/api/v2/display-settings`, `/api/v2/csp_report`, OAuth flow) | ✅ public |
| Task lifecycle on caller's own tasks (`POST /api/v2/tasks`, `GET/DELETE /api/v2/tasks/{id}`, unarchive) | ✅ in caller's org |
| Task list / search (`GET /api/v2/tasks`, `POST /api/v2/tasks/search`) | 🪟 filtered to caller's org |
| Task-scoped rules + metrics (`/api/v2/tasks/{task_id}/rules/*`, `/metrics/*`) | ✅ in caller's org (Pattern A) |
| Inference writes (`POST /api/v1/inferences`, validate endpoints) | ✅ in caller's org (Pattern B) |
| Inference / feedback / rule-result reads by ID | ✅ in caller's org (Pattern C) |
| Trace / span / session / annotation **reads** | ✅ in caller's org (Patterns C and D) |
| **Trace uploads** (`POST /api/v1/traces`) | ❌ admin-only (Pattern E) |
| Agentic resources (prompts, experiments, notebooks; CRUD) | ✅ in caller's org (Patterns B and C) |
| Continuous eval CRUD | ✅ in caller's org (Patterns A and C) |
| Chat (conversations, messages, regenerate) | ✅ in caller's org (Patterns B and C) |
| Default rules — read | ✅ (globals visible to tenants) |
| Default rules — write (`POST/DELETE /api/v2/default_rules`) | ❌ admin-only |
| Rules search (`POST /api/v2/rules/search`) | 🪟 defaults + caller's org rules |
| Usage / metrics (`GET /api/v2/usage/tokens`) | 🪟 filtered to caller's org |
| Model providers — read (`GET /api/v1/model_providers*`) | ✅ no credentials in response |
| Model providers — write (`PUT/DELETE /api/v1/model_providers/{p}`, `POST /api/v1/secrets/rotation`) | ❌ admin-only |
| System configuration (`GET/POST /api/v2/configuration`, `POST /api/chat/default_task`) | ❌ admin-only |
| API key management (`/auth/api_keys/*`) | ❌ admin-only |
| User management (`/users` CRUD, `/reset_password`) | ❌ admin-only |
| Documents and embeddings (`/documents/*`, embedding endpoints) | ❌ admin-only in v1 |
| Identity introspection (`GET /users/me`) | ✅ any authenticated caller (returns own scope) |
| Tenant signup (`POST /api/v2/tenant/signup`) | ✅ public, feature-flag-gated |

### Notable specifics

- **`POST /api/v1/traces` is the only newly admin-restricted endpoint.** Today it accepts any caller with `TRACES_WRITE`; v1 narrows that frozenset to exclude `TENANT-USER`. Existing admin clients are unaffected.
- **`POST /api/v2/tasks` is now tenant-accessible.** Body shape is unchanged. The handler reads `request.state.org_scope` to decide where the new task lands: admin → `default` org, tenant → caller's org. The body cannot specify a different org; that path doesn't exist.
- **`POST /api/v2/feedback/{inference_id}` is Pattern C, not Pattern A.** The path takes `inference_id`, not `task_id`. The inference is resolved through the repository's `org_scope` filter before the feedback row is written. A tenant cannot plant feedback on another org's inference because the inference fetch returns `None` for them and the handler 404s.
- **Aggregate endpoints stay shape-compatible.** `GET /api/v2/tasks` and `GET /api/v2/tasks/search` return the same response shape; tenants just see a smaller list. No SDK breaks.
- **`GET /users/permissions/check` is unchanged** — it's a permission probe, not identity introspection. The new `GET /users/me` covers the identity use case.

---

## 9. UI Changes

The genai-engine UI today (`arthur-engine/genai-engine/ui/`) authenticates by pasting an API key into a login form. The form stores the token in `localStorage` and attaches it as `Authorization: Bearer <token>` on every subsequent API call. This flow stays the same in v1.

Two changes are needed.

### 1. Discover identity on login

After the user submits an API key, the UI calls `GET /users/me` (section 6) to get the caller's identity, role, and `org_scope`:

```json
{
  "user_id":   "uuid-or-keycloak-sub",
  "roles":     ["TENANT-USER"],
  "org_scope": "uuid" | null,
  "org": { "id": "uuid", "name": "demo-a3f9b2c1" } | null
}
```

The UI stores this on `AuthContext` alongside the token. Existing code that reads `AuthContext` for the token keeps working; new code reads `roles`, `orgScope`, and `org`.

### 2. Conditional render branch

A single check at the top of the app's route guard:

```typescript
const isTenant = roles.includes("TENANT-USER") && orgScope !== null;
```

If `isTenant` is true, the UI renders the tenant branch. Otherwise (admin key or JWT user), the UI renders the existing admin view unchanged. Concretely:

| Component | Admin branch (today's UI) | Tenant branch |
|---|---|---|
| Top nav: Users | shown | hidden |
| Top nav: Model providers config | shown | hidden |
| Top nav: Default rules (write) | shown | hidden |
| Top nav: System configuration | shown | hidden |
| Top nav: API keys management | shown | hidden |
| Task switcher | all tasks | tasks in caller's org only (via server-filtered `GET /tasks`) |
| Task dashboard | unchanged | unchanged |
| Default rules viewer | unchanged | unchanged (read-only) |
| Model registry dropdown | populated from `GET /model_providers*` | same response, same dropdown |
| Login form | unchanged | unchanged |

Read-only data views (task data, traces, inferences, feedback, rule results) continue to work without UI changes. The server filters the underlying API responses by org; the UI just receives a smaller dataset for tenant calls.

### Files changed

- `ui/src/lib/auth.ts` — after the existing `login(token)` flow validates the token, call `GET /users/me` and store the response.
- `ui/src/contexts/AuthContext.tsx` — extend the context shape with `roles`, `orgScope`, and `org`.
- `ui/src/components/Layout.tsx` (or the equivalent top-level route guard) — read `isTenant` from context and conditionally render the admin nav items.
- `ui/src/components/TaskSwitcher.tsx` (or equivalent) — no code change needed because the `GET /tasks` API already returns the filtered list; the dropdown receives org-scoped tasks naturally.

### What stays the same

The UI does not need to know about orgs as a first-class concept in v1. There's no org switcher, no org-management screen, no org metadata in resource views. The org boundary is invisible to the tenant user — from their perspective, they log in with a key and see "their" tasks. From an admin's perspective, the UI is identical to today (their `org_scope` is `null` and the `isTenant` branch is never taken).

---

## 10. Backwards Compatibility

The intent is that single-tenant customer deployments operate exactly as today after the migrations apply. Concrete guarantees:

1. **Existing API keys preserve admin behavior.** Migration 2 adds `api_keys.org_id` as nullable. All existing keys remain `org_id = NULL`. The auth code paths for `org_scope is None` are identical to today.
2. **Existing tasks remain reachable to admin keys.** Migration 1 backfills `tasks.org_id`: tasks with `is_system_task=True` → `system` org, all others → `default` org. Admin keys (cross-org) see every task as before.
3. **No existing endpoint changes shape.** No new required request fields, no new required response fields, no renamed properties.
4. **No existing client SDK breaks.** Aggregate endpoints (`GET /api/v2/tasks`, search endpoints, query endpoints) stay shape-compatible. Tenant clients see a scoped subset; admin clients see everything.
5. **Existing role frozensets are not narrowed.** `TENANT-USER` is added to relevant frozensets; existing roles are not removed from any frozenset. Existing operator and admin users keep all their permissions.
6. **Feature flag off by default.** `ENABLE_PUBLIC_TENANT_SIGNUP=false` means customer deployments never expose the signup endpoint unless explicitly enabled. Multi-tenant behavior on a customer deployment is opt-in.
7. **`POST /api/v1/traces` remains accessible to every admin client.** The endpoint narrows `TRACES_WRITE` to exclude `TENANT-USER`. Admin clients (the only callers that exist today, given no tenant keys have been issued yet) are unaffected.

### Risk areas

Places where a v1 mistake could silently leak across orgs. Each has a mitigation; the fuzz test in section 12 enforces the structural ones.

- **A repository method that doesn't accept `org_scope` could silently return cross-org data to a tenant key.** Mitigation: code review checklist for new repository methods on task-scoped tables, plus the repository coverage test (section 12) that asserts every `get_X_by_id` method on a task-scoped repository accepts an `org_scope` parameter.
- **A new endpoint added in the future might forget the corresponding decorator.** Mitigation: the FastAPI route traversal test (section 12) asserts that every route accepting a `task_id` in path, body, or query has the corresponding `@enforce_*_org_scope` decorator applied.
- **The task → org lookup in every decorator adds a DB hit per request.** Mitigation: the decorator caches the resolved task on `request.state.cached_task` so handler-side repo calls don't re-fetch. The lookup is a single-row query on the `tasks` table with a primary-key index — sub-millisecond on a warm DB.

### What admins notice after the migrations apply

Effectively nothing on a deployment with the feature flag off. A new `org_id` column appears on `tasks`, `api_keys`, and the denormalized hot tables if they inspect the database. The `organizations` table exists with two rows (`default` and `system`). No API behavior changes for admin callers.

### What admins notice after enabling the feature flag

The `POST /api/v2/tenant/signup` endpoint starts responding 201 instead of 404. A new org is created for each signup. Admins inspecting the database see the new orgs accumulating in `organizations`. No effect on existing data or on the admin's own access.

---

## 11. Implementation Plan

Five phases. Phases 1 and 2 introduce no user-visible change — the system is still single-tenant from any caller's perspective after they complete. Phase 3 enables tenant provisioning. Phase 4 applies the UI render branch. Phase 5 verifies.

### Phase 1 — Schema + auth plumbing

No behavior change. Adds the data model and the auth-context plumbing without changing any endpoint's behavior.

1. Migration 0: create `organizations` table; seed `default` + `system` orgs.
2. Migration 1: add `org_id` to `tasks`; backfill (system tasks → system org, others → default org); enforce NOT NULL.
3. Migration 2: add `org_id` to `api_keys` (nullable).
4. Migration 3: denormalize `org_id` onto rule-result, feedback, annotation tables. Backfill in-migration.
5. Add `DatabaseOrganization` model; new `organizations_repository.py`.
6. Add `org_id` to `Task` and `ApiKey` pydantic schemas; propagate via `User.get_user_representation()`. Add new `Organization` and `MeResponse` schemas.
7. Update `multi_validator.py` to set `request.state.org_scope` from `api_key.org_id`.
8. Add `get_org_scope()` dependency in `src/dependencies.py`.
9. Add `TENANT-USER` role to `src/utils/constants.py`. (Not yet added to any frozenset; that comes in Phase 2.)
10. Add `GET /users/me` handler in `src/routers/user_routes.py`.
11. Verify all existing tests pass without modification before merging Phase 1.

**Estimated effort:** ~3-4 days human / ~1-2 hours CC.

### Phase 2 — Enforcement

Wires the five patterns into the endpoint surface. Still no user-visible behavior change for admin callers; tenant keys do not exist yet because the signup flow ships in Phase 3.

1. Implement decorators in `src/utils/users.py` alongside the existing `permission_checker`:
   - `@enforce_org_scope` (path, Pattern A)
   - `@enforce_body_org_scope` (body, Pattern B)
   - `@enforce_query_org_scope` (query, Pattern D)
2. Apply Pattern A decorator to every endpoint with `{task_id}` in the URL path: task_management, continuous_eval, llm_eval, validate, and similar v1 routes.
3. Apply Pattern B decorator to the ~10 body-task_id endpoints from the audit (inferences, agentic-prompts, agentic-experiments, agentic-notebooks, prompt_experiments, agent_polling, chatbots, chat).
4. Apply Pattern D decorator to the 7 query-param `task_ids` endpoints.
5. Update repository methods (Pattern C) to accept `org_scope`:
   - `inference_repository.get_inference`
   - `span_repository.get_trace_by_id`, `get_span_by_id`, `get_session_by_id`, `compute_span_metrics`
   - `feedback_repository.create_feedback` (resource lookup before write)
   - `datasets_repository._get_db_dataset` and all callers
   - `agentic_notebook_repository._get_db_notebook` and all callers
   - `agentic_prompt_repository._get_db_prompt` and all callers
   - `agentic_experiment_repository._get_db_experiment` and all callers
   - `prompt_experiment_repository._get_db_experiment` and all callers
   - `continuous_eval_repository.get_eval_by_id` plus run lookups
   - `chat_repository.get_conversation_by_id` and message/regenerate paths
   - `chatbot_repository.get_chatbot_by_id`
   - `annotation_repository.get_annotation_by_id`
   - `tasks_repository.get_task_by_id` plus new `list_tasks_by_org`, `get_tasks_by_ids`
6. Extend `PermissionLevelsEnum` frozensets (section 6) to include `TENANT-USER`.
7. Narrow `TRACES_WRITE` to exclude `TENANT-USER` (admin-only trace uploads).
8. `POST /api/v2/tasks` handler: read `request.state.org_scope`; admin → `default` org, tenant → caller's org.

**Estimated effort:** ~7-10 days human / ~5-7 hours CC. The bulk of the work is touching repositories and applying decorators across the existing endpoint surface.

### Phase 3 — Tenant provisioning

Adds the public signup endpoint and the feature flag.

1. New `POST /api/v2/tenant/signup` endpoint at `src/routers/v2/task_management_routes.py` (or a new `tenant_routes.py` for clarity).
2. Add `ENABLE_PUBLIC_TENANT_SIGNUP` boolean to `src/utils/config.py`, default `False`.
3. Handler runs the four-step transaction (create org, create task, apply default rules, create API key) inside a single `db_session` transaction. Reuses the existing `tasks_repository.create_task()` and `api_key_repository.create_api_key()` plus the new `organizations_repository.create_organization()`.

**Estimated effort:** ~1-2 days human / ~30 min CC.

### Phase 4 — UI changes

1. `ui/src/lib/auth.ts` — after successful token validation, call `GET /users/me`. Cache the response.
2. `ui/src/contexts/AuthContext.tsx` — extend with `roles`, `orgScope`, `org`.
3. Top-level route guard component — read `isTenant` from context and hide admin nav items in tenant mode.
4. No changes needed to task switcher, dashboards, or data views (the API already filters by org).

**Estimated effort:** ~2 days human / ~1 hour CC.

### Phase 5 — Verification

1. Unit + integration tests per section 12.
2. Fuzz / coverage test asserting every applicable route has the right decorator.
3. CHANGELOG entry.
4. Customer-facing release note: "multi-tenant features opt-in via the new signup endpoint + feature flag; existing keys and tasks are unaffected."

**Estimated effort:** ~3-4 days human / ~2-3 hours CC.

### Total estimate

Roughly **16-22 days human / 10-14 hours CC** for v1. The repository work in Phase 2 dominates because the audit surfaced ~35 resource-id-scoped endpoints + 10 body-task_id endpoints + 7 query-param endpoints, each needing wiring.

---

## 12. Verification

Three layers of testing: unit tests cover individual pieces, integration tests cover end-to-end isolation, a fuzz / coverage test catches future drift.

### Unit tests

- Migrations produce the expected schema (use the existing Alembic test harness):
  - Migration 0: `organizations` table exists; `default` and `system` orgs present; partial unique index prevents a second system org.
  - Migration 1: `tasks.org_id` is NOT NULL; system tasks point at the system org; all others at the default org.
  - Migration 2: `api_keys.org_id` is nullable; all existing keys have NULL.
  - Migration 3: each denormalized table has `org_id` NOT NULL; backfilled values match the join chain.
- `MultiMethodValidator` sets `request.state.org_scope` correctly for API key, JWT, and admin paths.
- `@enforce_org_scope` raises 404 when the path's task belongs to a different org; passes when it matches; passes through for admin.
- `@enforce_body_org_scope` raises 404 on mismatch, 400 when the field is missing, passes through for admin.
- `@enforce_query_org_scope` raises 403 when `task_ids` contains anything outside scope; expands the filter to all-org-tasks when `task_ids` is empty; passes through for admin.
- Repository methods (Pattern C): `get_X(id, org_scope=O2)` returns `None` for a row whose task is in `O1`. With `org_scope=None`, the row is returned regardless.
- `permission_checker` admits/rejects `TENANT-USER` per the updated frozensets, including the negative case for `TRACES_WRITE`.
- `GET /users/me` returns the correct shape for admin keys (org_scope null), tenant keys (org_scope populated), and JWT users.

### Integration tests

Seed two orgs (O1, O2), each with two tasks (O1 → {T1a, T1b}, O2 → {T2a, T2b}). Mint tenant keys K1 → O1, K2 → O2. Use admin key A. Seed each task with one inference, feedback row, trace, span, annotation, dataset, notebook, prompt, experiment, and conversation.

- **Multi-task within org:** K1 reads both T1a and T1b. Both succeed; K1 sees every resource type across both tasks.
- **Pattern A — Path scope:** K1 hits every `/tasks/{task_id}/*` endpoint with `task_id = T2a`. Every response is 404.
- **Pattern B — Body scope:** K1 POSTs to every body-task_id endpoint with `body.task_id = T2a`. Every response is 404. With `body.task_id = T1a`, every response is the normal success code.
- **Pattern C — Resource ID scope:** K1 calls every resource-id-scoped GET/PATCH/DELETE with a T2a-owned resource ID. Every response is 404. **Feedback planting:** K1 POSTs `/api/v2/feedback/{T2a_inference_id}` — expect 404, verify no feedback row written.
- **Pattern D — Query-param scope:** K1 calls every `task_ids`-accepting endpoint with `?task_ids=T2a`. Every response is 403. With no `task_ids`, every response transparently filters to {T1a, T1b}. With `?task_ids=T1a,T1b`, normal 200.
- **Trace uploads blocked for tenants:** K1 POSTs `/api/v1/traces` with any payload. Expect 403. A (admin) posts the same payload — expect the existing 201 path.
- **`POST /api/v2/tasks` routing:** K1 creates a task with the existing body shape. Verify the task lands in O1. A (admin) creates a task with the same body. Verify the task lands in the `default` org.
- **Cross-org enumeration:** K1 calls `GET /api/v2/tasks`, expects {T1a, T1b}. K1 calls `GET /api/v2/tasks/search`, expects the same.
- **Admin still works:** A calls every endpoint above; expects unchanged behavior (full visibility, no filtering).
- **Aggregate filtering:** K1 calls `GET /api/v2/usage/tokens`; expects token usage summed across O1's tasks only.
- **Admin-only blocks (Pattern E):** K1 calls `POST /api/v1/traces`, `POST /auth/api_keys/`, `GET /users`, `GET /api/v2/configuration`, `POST /api/v2/default_rules`, `POST /api/chat/default_task`, `PUT /api/v1/model_providers/anthropic`, `POST /api/v1/secrets/rotation`. Every response is 403.
- **Model provider reads (allowed):** K1 calls `GET /api/v1/model_providers`. Expect 200 with `[{provider, enabled}]` per provider. K1 calls `GET /api/v1/model_providers/anthropic/available_models`. Expect 200 with `{provider, available_models}`. Verify no credential fields in either response.
- **System org isolation:** K1 attempts to read any task in the `system` org via every pattern. Every response is 404. A (admin) can read system tasks.
- **API key tampering:** K1 calls `DELETE /auth/api_keys/deactivate/{A_key_id}`. Expect 403.
- **`GET /users/me`:** K1 returns `roles=["TENANT-USER"]`, `org_scope=O1`, `org=O1`'s record. A returns `roles=admin set`, `org_scope=null`, `org=null`.
- **Tenant signup (flag off):** anonymous `POST /api/v2/tenant/signup` returns 404.
- **Tenant signup (flag on):** anonymous `POST /api/v2/tenant/signup` returns 201 with `(org_id, task_id, task_name, api_key)`. The returned key, used as a Bearer token, has `org_scope` set to the new org and can access the new task.
- **Default org backfill:** an existing pre-migration task now has `org_id = default_org.id`. A task with `is_system_task=True` has `org_id = system_org.id`. Admin sees both; a fresh tenant key cannot reach either.

### Fuzz / coverage test

A test that enumerates every FastAPI route and asserts the right enforcement is wired up. A failed assertion = a developer added a route without scope enforcement.

```python
# Pseudocode
for route in app.routes:
    handler = route.endpoint
    # Pattern A
    if "task_id" in route.path_params:
        assert has_decorator(handler, enforce_org_scope), \
            f"{route.path} has {{task_id}} in path but is missing @enforce_org_scope"
    # Pattern B
    body_model = inspect_body_model(handler)
    if body_model is not None and "task_id" in body_model.__fields__:
        assert has_decorator(handler, enforce_body_org_scope), \
            f"{route.path} body has task_id but is missing @enforce_body_org_scope"
    # Pattern D
    if "task_ids" in inspect_query_params(handler):
        assert has_decorator(handler, enforce_query_org_scope), \
            f"{route.path} accepts task_ids query but is missing @enforce_query_org_scope"
```

Pattern C is harder to assert generically. A complementary repository coverage test asserts every method on a task-scoped repository that takes a resource-id parameter also accepts `org_scope: UUID | None = None`. Easier to enforce via code review than fully automated.

### Manual smoke test

1. Run engine in single-tenant mode (default config). Existing admin key sees all tasks in default + system orgs.
2. Set `ENABLE_PUBLIC_TENANT_SIGNUP=true`. `curl POST /api/v2/tenant/signup` returns a fresh `(org, task, api_key)`.
3. Paste the tenant key into the UI's login form. Confirm the UI loads with admin nav hidden and the task switcher showing only the new task.
4. Hit an admin endpoint with the tenant key. Confirm 403.
5. Send an inference via the tenant key. Confirm it lands in the tenant's task.
6. Try to upload traces via the tenant key. Confirm 403.
7. Create a second task via `POST /api/v2/tasks` with the tenant key. Confirm it lands in the tenant's org. Confirm the task switcher now shows both.
8. Sign up a second tenant. Confirm cross-org isolation (each tenant sees only its own tasks).

### Performance baseline

- Tenant key auth path adds one extra column read (`org_id`) per request. Negligible.
- Decorators A, B, D add a task-by-id (or tasks-by-ids) lookup. Cached on `request.state` so handler-side repo calls don't re-fetch. Single-row primary-key query — sub-millisecond on a warm DB.
- Repository filter (C) adds `WHERE org_id = X` or a one-hop join through `tasks`. Indexed columns; query plan shapes are unchanged.
- Public signup transaction: budget under 500ms end-to-end.

---

## 13. Future Work

Items deferred from v1, with rationale and rough effort.

### v2 capabilities

- **Postgres Row-Level Security (RLS).** v1 enforces at the API layer only. A v2 hardening pass would add RLS policies on every task-scoped table so the database refuses cross-org rows even if a handler forgets to filter. Implementation: a per-request `SET LOCAL app.org_scope = ...` in session middleware, plus `CREATE POLICY ... USING (org_id = current_setting('app.org_scope'))` on each table. Requires migrating connection handling to set the variable on every checkout. Effort: ~1 week.
- **Bring-Your-Own-Keys (BYOK) model providers.** Tenants configure their own provider credentials per-org. Schema: add `org_id UUID NULL` to `model_providers` and `secret_storage`. Endpoint behavior: `GET /api/v1/model_providers` returns globals merged with the caller's org-scoped providers. New writes via `POST /api/v2/organizations/{org_id}/model_providers`. Forward-compatible with v1's response shape — no breaking change. Effort: ~1-2 weeks.
- **Tenant trace uploads.** `POST /api/v1/traces` is admin-only in v1. Re-enabling for tenants requires solving both the `arthur.task` attribute path (validate against caller's org) and the service-name fallback (per-org mappings). Options: a separate `POST /api/v2/tenant/traces` endpoint that takes only an org-scoped task_id, or tighten the resolver to validate the resolved task's org against `org_scope`. Effort: ~3-5 days.
- **Per-org default rules and configuration.** v1 keeps default rules and app configuration global. v2 could scope them: `default_rules` gets an `org_id NULL` column (NULL = applies to all orgs), and per-org configuration lives in a new table. Effort: ~1 week, plus a careful migration of existing default rules into the "applies to all" case.
- **Multi-key per org.** v1's signup flow mints one key per org. v2 could allow multiple keys per org (each independently revocable) by exposing a key-management surface to tenants (`POST /api/v2/tenant/api_keys` minting another key for the caller's org). Effort: ~2-3 days plus UI work.
- **Tenant-admin role.** A new role between admin and `TENANT-USER` that can mint keys within their own org but cannot read across orgs. Useful for customer multi-user demo accounts. Schema-wise easy (another role plus frozenset entries). Effort: ~2-3 days.
- **Documents and embeddings multi-tenancy.** Currently 403 for tenants. v2 would add `org_id` to `documents` (cascade to `embeddings`), then enable tenant access via Pattern C. The blocker isn't org scoping — it's the document model's existing owner-scoped semantics, which need a coherent migration to org-scoped semantics. Effort: ~1-2 weeks.
- **Tenant-aware audit logging.** Track `org_scope` on audit events so admins can investigate per-org activity. v1 doesn't touch audit. Effort depends on existing audit infrastructure; ~3-5 days if logging is straightforward to extend.
- **Admin endpoints for org management.** v1 has no admin CRUD for orgs (provisioning is exclusively the public signup). If admins ever want to inspect, rename, or delete orgs via the API instead of the DB, add `GET/PATCH/DELETE /api/v2/organizations*`. Effort: ~1-2 days.

### Why `org_id` only (not also `task_id`) on the denormalized tables

The hot tables (rule_results, feedback, annotations, etc.) get a denormalized `org_id` in Migration 3 but not a denormalized `task_id`. Alternatives considered at the time of writing v1:

- **Both columns**: fastest filtering on either dimension, but doubles write cost and storage. The benefit only matters if per-task queries on these specific tables become a hot path; existing per-task queries already work via 1-hop joins to parent tables (`inferences`, `trace_metadata`) which already have `task_id`.
- **Only `task_id`** (no `org_id`): solves existing per-task queries but requires a join to `tasks` for every Pattern C tenant check, which is what we're avoiding.
- **Neither (joins for both)**: today's state. The audit identified the multi-hop joins as a security footgun (easy to forget the org check).

`org_id` only is the minimum needed for tenant isolation. If a future workload demonstrates that fast per-task queries on these tables are a bottleneck, adding `task_id` is a single-column migration with the same shape as Migration 3.

---

## 14. Open Questions

Items that need a team decision before or during implementation. None gate the design — they're choices best made at review or implementation time.

1. **Should `org_id` appear in `GET /api/v2/tasks*` responses for tenant callers?** After Migration 1, every task carries `org_id` and the existing response models will pick it up automatically. A tenant's response will include their own org's id on every task. Not a cross-org leak (they only ever see their own org), but it's a new field in the response shape. Options: (a) include unconditionally — simplest; (b) include for admin only — keeps the tenant API surface minimal; (c) include as a nested `org: {id, name}` for readability. Default in this doc is (a).

2. **Org name format configurability.** The signup handler generates `demo-{8-char-hex}` with a hardcoded prefix. Should the prefix be a config option per deployment? Useful if a non-demo deployment ever wants to use the same signup flow with a different label. Default in this doc: hardcoded `demo-` prefix; revisit if needed.

3. **Service-name → task_id mapping under multi-tenancy.** Today the `service_name_task_mappings` table is instance-wide and unrelated to orgs. v1 doesn't change it because `POST /api/v1/traces` is admin-only and mappings only matter for the admin trace-ingestion path. When v2 enables tenant trace uploads, mappings need to become org-scoped (or use a different mechanism). Flagging so we don't accidentally introduce per-tenant trace ingest without addressing this.

4. **Org-name collision retry policy.** The signup handler retries once on `organizations.name` unique-constraint violation. With an 8-char hex suffix (2^32 possibilities), per-signup collision probability is effectively zero even at scale. One retry is plenty in practice. Flagged in case the team prefers a different strategy or a configurable retry budget.
