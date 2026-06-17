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
