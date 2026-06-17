# GenAI Engine — Platform-Connected Multi-Tenancy: Technical Plan

> **Status:** Research / design proposal
> **Date:** 2026-06-17
> **Companion doc:** [`MULTI_TENANCY_DESIGN.md`](MULTI_TENANCY_DESIGN.md) (the shipped v1 org model this plan builds on).

---

## 0. How to read this document

This is a *research plan*, not an implementation spec. Every factual claim about the
current system has been checked against the code and is tagged:

- ✅ **Validated** — confirmed in this repo, with file references.
- ⚠️ **Partially true / needs care** — directionally right but the code only partly supports it.
- ❓ **Unverifiable here** — depends on the platform / control-plane codebase, which is a
  **separate repository not available in this workspace**. Roughly half of the proposed
  architecture lives there and is therefore *unvalidated*.

---

## 1. Framing & Scope

### 1.1 What problem are we actually solving?

The business driver is **unit economics for a SaaS land-and-expand motion**: sign up free →
get a hosted engine in <60s → convert to Pro (~$200/mo) → Enterprise. The single requirement
that most constrains *engine architecture* is unit economics; "easy to adopt," "data
governance," and "land & expand" mostly drive platform/packaging, not the engine internals.

Two distinct technical bets follow:

1. **Multi-tenant inference / engine** (cost) — pull the expensive models out of the
   per-tenant engine into a shared, pooled inference service so a lightweight engine can run
   for **< $200/mo**. *This plan does not cover the inference-service split* — it is a
   separate, larger effort. Flagging it because the unit-economics math (crossover at ~30–40
   paying tenants) depends on it, not on the auth work below.
2. **Platform-connected engine** (adoption + governance) — a user clicks from the platform
   into the engine with **no separate API-key login (SSO)**, and sees only the resources they
   are authorized for, governed by the platform's Keycloak (authN) + SpiceDB (authZ). **This
   is what the plan below covers.**

### 1.2 What is already done (do not re-build)

The engine is **already multi-tenant at the org level** as of the v1 work
(`MULTI_TENANCY_DESIGN.md`, migrations `2026_05_19_*`). ✅ validated in code:

- `organizations` table (`src/db_models/organization_models.py:10`), seeded `default`
  (`…0001`) and `system` (`…0002`) orgs.
- `tasks.org_id` (NOT NULL) and `api_keys.org_id` (nullable; `NULL` = admin/cross-org)
  (`src/db_models/task_models.py:29`, `src/db_models/auth_models.py:34`).
- `org_id` denormalized onto the hot tables (rule results, feedback, spans, trace_metadata,
  annotations) for single-hop tenant filtering.
- `TENANT-USER` role + four enforcement patterns (path / resource-id / query-param /
  admin-only) across **60 path endpoints, 11 query endpoints, ~35 resource-id repo methods**.
- Public, feature-flagged signup at `POST /api/v2/tenant/signup`
  (`src/routers/v2/tenant_signup_routes.py`), gated by `GENAI_ENGINE_DEMO_MODE`.

**So the right framing is not "make the engine multi-tenant." It is "connect the
already-multi-tenant engine to the platform's identity and authorization, build a real auth
solution (Keycloak-based SSO), turn org scope from a *scalar* into a *set* so the UI is a
single unified view, and rework the ML-engine job path for cross-org fan-out."**

### 1.3 The taxonomy

| Control Plane (platform) | GenAI Engine | Notes |
|---|---|---|
| **Project** | **Engine Organization** | 1:1. The connector that stores the org's API key lives on the project. |
| **Application** (née model) | **Task** | Mapping already held in the platform today; no AuthZ on applications directly — authZ is inherited through the project. |
| Workspace | (implicit boundary) | Workspace-level role grants reach all of the org's tasks. |

Authorization is done **by proxy**: the engine never syncs task-level ACLs to SpiceDB. The
question *"which engine org IDs can this user reach?"* reduces to *"which platform projects can
this user reach?"* (1:1 project↔org), answered by the platform from SpiceDB. The engine then
filters its own data by that set of org IDs. The only engine state the platform must know about
is **orgs** (via the project↔org and application↔task mappings it already holds).

### 1.4 Two scope boundaries

- **The engine UI stays in the engine.** It is not lifted into the platform; data planes do not
  become API-only. The engine keeps its own UI and becomes a Keycloak client so it can drive SSO
  itself.
- **SSO is the free/self-serviceable part; RBAC is the gated enterprise lever.** SSO is plain
  public OIDC spec — a self-hoster could wire it up themselves. The monetizable capability is
  **RBAC**, which only works once the engine is connected to the platform. Standalone / Docker /
  local installs keep working on admin API keys with **no RBAC**; connecting to the platform is
  what unlocks org-scoped RBAC.

---

## 2. Current State — Validated Findings

### 2.1 Authentication: we build a new Keycloak-based auth solution

We are **building the auth solution end-to-end**. The engine becomes a **Keycloak client** of
the platform's Keycloak, so it can drive SSO directly: a user clicking in from the platform is
transparently signed in (no API-key paste). The new auth entry point:

- Validates platform-minted Keycloak tokens (RS256 against the platform-served JWKS).
- Pins the engine's expected issuer + audience.
- Is enabled only when the engine is configured with a platform URL; when unset, the engine
  behaves as a standalone, API-key-only install (preserving the Docker/local path).
- **Fails closed** on the authZ handoff: a token that authenticates but has not yet been scoped
  to any org grants **zero** access — never cross-org/admin.

The **admin API-key path is retained** for standalone installs and service callers. Admin keys
(`org_id = NULL`) keep cross-org access; they are also what a self-hoster uses to *prove
ownership* when connecting to the platform.

❓ **Platform dependency (not in this repo):** the platform proxying Keycloak's JWKS/metadata so
the engine only needs the platform URL. Plausible; verify before relying.

### 2.2 Org scope is a scalar threaded everywhere — the "~60 functions" claim is accurate

✅ Validated. The authZ scope is a single `Optional[UUID]`:

- Read by `get_org_scope(request) -> Optional[UUID]` (`src/dependencies.py:331`).
- Enforced by `@enforce_org_scope` (path, 60 endpoints) and `@enforce_query_org_scope`
  (query, 11 endpoints) in `src/utils/users.py`, plus ~35 repository `get_X_by_id(…,
  org_scope)` methods (Pattern C) that filter `WHERE org_id == org_scope`.
- `None` means "admin/cross-org" (filter skipped).

The filters are **scattered, not centralized** — every repo method inlines its own
`if org_scope is not None: q = q.filter(... == org_scope)`. There is no single choke point.

**Feasibility of scalar → set (`org_id IN (...)`):** mechanically straightforward per call
site, but there is no central helper to change, so it is a **wide** edit (60 + 11 + ~35 ≈ 106
touch points). The denormalized `org_id` columns make the `IN` filter efficient. This refactor
is what enables the unified, single-pane UI (turning the request scope from one org into the
set of orgs the user can reach and filtering `org_id IN (...)`).

### 2.3 Resource URLs mostly do not carry the org

✅ Validated. List/create endpoints are task-scoped (`/api/v1/tasks/{task_id}/…`) but by-id
fetches are bare resource IDs: `GET /api/v1/continuous_evals/{eval_id}`,
`/prompt_experiments/{experiment_id}`, `/inferences/{inference_id}`, etc. You cannot derive the
org from such a URL without first querying the resource. Under a unified set-scope model this is
a non-issue — the user's full org set is always in scope, so any link they are authorized for
resolves directly without needing the org in the URL.

### 2.4 API keys & org-creation endpoint

✅ Validated. `DatabaseApiKey` (`src/db_models/auth_models.py:20`) has nullable `org_id`;
keys are bcrypt-hashed, base64 `id:secret` format. `NULL` org_id = admin (cross-org). The
only org-creation path is the **public** `POST /api/v2/tenant/signup`, gated by
`GENAI_ENGINE_DEMO_MODE` (returns 404 when off). When the engine is platform-connected, org
creation must be authenticated and must also create the platform project.

### 2.5 ML engine: single-data-plane Keycloak client, polling, project_id already present

✅ Validated in `ml-engine/`:

- `job_agent.py` is a **long-poller** (~0.25s loop) calling
  `JobsV1Api.post_dequeue_job(self.data_plane_id, …)`. It is bound to **one**
  `data_plane_id`, obtained at startup from `UsersV1Api.get_users_me().data_plane_id`.
- Auth is **OAuth2 client-credentials** via `ArthurClientCredentialsAPISession`
  (`ARTHUR_CLIENT_ID` / `ARTHUR_CLIENT_SECRET` / `ARTHUR_API_HOST`). One Keycloak client per
  ML-engine instance. Token acquisition is abstracted inside the `arthur_client` library — **no
  explicit token-exchange call is visible in this repo**; adding one depends on `arthur_client`
  support. ❓
- The `Job` object **already carries `project_id` and `data_plane_id`**. Some specs (e.g.
  `DiscoverAgentsJobSpec`) already carry `workspace_id`. `post_submit_jobs_batch(project_id=…)`
  and `put_agents(workspace_id=…)` already pass scope explicitly.
- Connectors are fetched by **`connector_id` alone** via
  `ConnectorsV1Api.get_sensitive_connector(connector_id)`. The `ShieldConnector` /
  `EngineInternalConnector` pull the genai-engine API key + endpoint from connector fields or
  from `GENAI_ENGINE_INTERNAL_API_KEY` env.

So the job plan (cross-org queue → read project_id off job → token-exchange for an
org-scoped token → fetch the project's connector → use its engine API key) is **directionally
feasible with the current shape**, and `project_id` is already in place. The two genuinely new
pieces are the **cross-org dequeue** and the **token exchange**, both platform + `arthur_client`
work. ❓

---

## 3. Changes Required

Each subsection is one change at a high level, followed by what has to happen for it to work.
These are not ordered or phased — they are the full set of moving parts. Items tagged ❓ live in
the platform / control-plane repo (not in this workspace) and are dependencies, not engine work.

### 3.1 New Keycloak auth client in the engine

Replace the engine's authentication entry point with a new Keycloak-client implementation so the
engine validates platform-minted tokens and can drive SSO.

- Register the engine as a Keycloak client of the platform's Keycloak.
- Validate incoming platform tokens: fetch the platform-served JWKS, verify the RS256 signature,
  and pin the expected issuer and audience.
- Drive the OIDC redirect/sign-in for browser flows so a user arriving from the platform is
  signed in transparently (no API-key paste). Hold tokens in the auth module's memory with
  silent refresh; do not use localStorage.
- Keep the admin / API-key validation path working for standalone and service callers.
- Gate the whole platform path behind a platform-URL config value; when it is unset the engine
  runs exactly as a standalone, API-key-only install.
- Fail closed: a token that authenticates but is not yet org-scoped (see 3.2) must grant zero
  access — never cross-org/admin.
- ❓ Platform must proxy Keycloak's JWKS/metadata so the engine only needs the platform URL.

### 3.2 Platform-driven authorization (resolve the user's engine orgs)

After authentication, the engine learns which engine orgs the caller may reach by asking the
platform, rather than reading scope off the token.

- Add an engine-side client that calls a new platform endpoint — "which projects (→ engine org
  IDs) can this user access?" — backend-to-backend using a service credential (never the user's
  browser token, so it can't be spoofed).
- Map the returned projects 1:1 to engine org IDs and set that as the caller's org scope for the
  request/session.
- Cache the result per user with a short TTL and define how the cache is invalidated when a
  user's project access changes.
- ❓ Platform must expose the authZ endpoint backed by SpiceDB, and register engine orgs in
  SpiceDB as children of projects/workspaces so the lookup has data to answer from.

### 3.3 Turn org scope from a single value into a set

Change the engine's org scope from one org ID to the set of org IDs the user can reach, so all
data access filters on membership in that set.

- Introduce a central helper (e.g. `apply_org_filter(query, column, org_scope)`) that handles
  `None` (admin / no filter), a single org, and a set of orgs.
- Migrate `get_org_scope`, the `@enforce_org_scope` and `@enforce_query_org_scope` decorators,
  and the ~35 resource-id repository methods to the set semantics and the helper (≈106 touch
  points total).
- Keep the API-key path emitting a singleton set so single-tenant behavior is unchanged and both
  auth paths converge on one representation.
- Extend the fuzz/coverage test so no task-scoped repository method can filter by a bare scalar
  anymore.

### 3.4 Unified engine UI (single pane, no selector)

Make the engine UI show everything the user is authorized for across all their orgs at once.

- Make the UI a Keycloak client: redirect to platform login when unauthenticated; keep the token
  in auth-module memory with silent refresh.
- Extend the existing `GET /users/me` + `AuthContext` plumbing to carry the user's set of orgs
  and drive the admin/tenant render branch.
- Add an `org_id` discriminator to list/aggregate response payloads (the v1 work already did this
  for tasks; extend it to the other list/aggregate endpoints) so the UI can group and label
  cross-org results.
- Do not introduce an org-switcher component.

### 3.5 Gate and re-home org creation when platform-connected

When the engine is connected to the platform, org creation must be authenticated and mirrored
into the platform.

- Require authentication on the org-creation path (today `POST /api/v2/tenant/signup` is public);
  it can no longer mint orgs anonymously once platform-governed.
- On org creation, call the platform (with the user's bearer token) to create the corresponding
  platform project, which registers the new engine org in SpiceDB.
- ❓ Platform must expose the project-creation endpoint that performs the SpiceDB registration.

### 3.6 Onboarding & ownership proof for existing standalone engines

Let an engine that has been running API-key-only connect to the platform and prove it owns its
orgs.

- On connect, require the engine's admin key as proof of ownership (an admin key implies a
  single-tenant engine, which no SaaS tenant could hold), and use it to link the engine to the
  workspace.
- Auto-create a default workspace and one project per existing engine org during onboarding.
- After onboarding, route RBAC through the platform/SpiceDB while keeping admin-key mode working
  for backward compatibility (without RBAC).
- ❓ Platform must accept the admin key as ownership proof and run the workspace/project
  bootstrap.

### 3.7 Cross-org ML engine jobs

Let one ML engine pick up and run jobs across many orgs instead of being bound to a single data
plane/workspace.

- ❓ Refactor the platform `/jobs` API to be cross-organization, and give the ML engine a
  cross-org Keycloak client with permission to read the cross-org queue (today
  `post_dequeue_job(data_plane_id)` is single-data-plane).
- Ensure every relevant `JobSpec` carries the `project_id` (the `Job` object already does).
- In the job runner, after dequeue: read the job's `project_id`, fetch that project's connector,
  and use the connector's org-scoped engine API key to talk to the correct GenAI engine org.
- Separately exchange the platform token for a workspace-scoped token to push results (metrics,
  etc.) back into the workspace that owns the project.
- ❓ Requires a platform token-exchange endpoint and `arthur_client` support for token exchange.

### 3.8 Engine ↔ platform Keycloak connectivity

Make sure the engine can actually reach the platform's Keycloak/JWKS at runtime, across network
boundaries, without standing up expensive private networking by default.

- Provide a connectivity path from the engine to the platform's proxied Keycloak metadata/JWKS
  endpoint over TLS.
- Avoid defaulting to private link / VPN (it costs extra); reserve dedicated private networking
  for customers whose security posture requires it.
- Produce an explicit infra design and cost review for cross-VPC reachability before the
  platform-token paths go live.
