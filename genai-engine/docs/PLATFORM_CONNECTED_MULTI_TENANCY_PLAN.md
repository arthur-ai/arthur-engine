# GenAI Engine — Platform-Connected Multi-Tenancy: Technical Plan

> **Status:** Research / design proposal (for adversarial review)
> **Date:** 2026-06-17
> **Source material:** Notion "2026 Engine Architecture Convo" (Convos 1–3), Fireflies transcripts
> `01KT7C5884KREC51V5NAFAS4R9` (Convo 1 — business), `01KTCHXCADTZXRRCBDQ8B6HVWH` (Convo 2 —
> architecture), `01KTS4893H7K9XE852CPRBS05J` (Convo 3 — finalizing),
> `01KVB01Y95AT79MXSY1V5BX7EX` (Zach↔Nori 1:1, 2026-06-17), and direct code investigation of
> `genai-engine/` and `ml-engine/`.
> **Companion doc:** [`MULTI_TENANCY_DESIGN.md`](MULTI_TENANCY_DESIGN.md) (the shipped v1 org model this plan builds on).

---

## 0. How to read this document

This is a *research plan*, not an implementation spec. Every factual claim about the
current system has been checked against the code and is tagged:

- ✅ **Validated** — confirmed in this repo, with file references.
- ⚠️ **Partially true / needs care** — the meeting notes assert something the code only
  partly supports.
- ❓ **Unverifiable here** — depends on the platform / control-plane codebase, which is a
  **separate repository not available in this workspace**. Roughly half of the proposed
  architecture lives there and is therefore *unvalidated*.

Section 9 (Assumptions Ledger) and Section 10 (Weak Spots & Open Questions) are the
adversarial-review payload Ian asked for at the end of Convo 3.

---

## 1. Framing & Scope

### 1.1 What problem are we actually solving?

The business driver (Convo 1) is **unit economics for a SaaS land-and-expand motion**:
sign up free → get a hosted engine in <60s → convert to Pro (~$200/mo) → Enterprise. The
single requirement that most constrains *engine architecture* is unit economics; "easy to
adopt," "data governance," and "land & expand" mostly drive platform/packaging, not the
engine internals.

Two distinct technical bets came out of that:

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

The engine is **already multi-tenant at the org level** as of the May 2026 v1 work
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

### 1.3 The taxonomy (locked in Convo 3 and re-confirmed in the Nori 1:1)

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

### 1.4 Two scope boundaries that the Nori 1:1 nailed down

- **The engine UI stays in the engine.** An earlier idea (Convo 2) was to lift the engine UI
  into the platform and make data planes API-only. That is **off the table** — *"the engine's
  not moving."* The engine keeps its own UI and becomes a Keycloak client so it can drive SSO
  itself.
- **SSO is the free/self-serviceable part; RBAC is the gated enterprise lever.** SSO is plain
  public OIDC spec — a self-hoster could wire it up themselves. The monetizable capability is
  **RBAC**, which only works once the engine is connected to the platform. Standalone / Docker
  / local installs keep working on admin API keys with **no RBAC**; connecting to the platform
  is what unlocks org-scoped RBAC.

---

## 2. Current State — Validated Findings

### 2.1 Authentication: we build a new Keycloak-based auth solution

We are **building the auth solution end-to-end**, not inheriting one. The engine becomes a
**Keycloak client** of the platform's Keycloak, so it can drive SSO directly: a user clicking
in from the platform is transparently signed in (no API-key paste). The new auth entry point:

- Validates platform-minted Keycloak tokens (RS256 against the platform-served JWKS).
- Pins the engine's expected issuer + audience.
- Is enabled only when the engine is configured with a platform URL; when unset, the engine
  behaves as a standalone, API-key-only install (preserving the Docker/local path — a hard
  requirement from Convo 2 and re-confirmed with Nori).
- **Fails closed** on the authZ handoff (see §4.2): a token that authenticates but has not yet
  been scoped to any org grants **zero** access — never cross-org/admin.

The **admin API-key path is retained** for standalone installs and service callers. Admin keys
(`org_id = NULL`) keep cross-org access; they are also what a self-hoster uses to *prove
ownership* when connecting to the platform (§7.2).

❓ **Platform dependency (not in this repo):** the platform proxying Keycloak's JWKS/metadata so
the engine only needs the platform URL (Ian indicated this is live in Convo 3). Plausible;
verify before relying.

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
touch points). The denormalized `org_id` columns make the `IN` filter efficient. This is
exactly the refactor Convo 3 weighed ("we now have to go back and edit all the code we
changed… a couple hundred functions") — that estimate is right in order of magnitude. **This
refactor is what enables the unified, single-pane UI (Section 5).**

### 2.3 Resource URLs mostly do not carry the org

✅ Validated. List/create endpoints are task-scoped (`/api/v1/tasks/{task_id}/…`) but by-id
fetches are bare resource IDs: `GET /api/v1/continuous_evals/{eval_id}`,
`/prompt_experiments/{experiment_id}`, `/inferences/{inference_id}`, etc. You cannot derive the
org from such a URL without first querying the resource. Under the unified set-scope model
(Section 5) this is a non-issue — the user's full org set is always in scope, so any link they
are authorized for resolves directly without needing the org in the URL.

### 2.4 API keys & org-creation endpoint

✅ Validated. `DatabaseApiKey` (`src/db_models/auth_models.py:20`) has nullable `org_id`;
keys are bcrypt-hashed, base64 `id:secret` format. `NULL` org_id = admin (cross-org). The
only org-creation path is the **public** `POST /api/v2/tenant/signup`, gated by
`GENAI_ENGINE_DEMO_MODE` (returns 404 when off). When the engine is platform-connected, org
creation must be authenticated and must also create the platform project (§7.1).

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
pieces are (a) the **cross-org dequeue** and (b) the **token exchange**, both platform +
`arthur_client` work. ❓

---

## 3. Target Architecture (end state)

```
                         ┌─────────────────── Control Plane (platform repo — NOT in this workspace) ──┐
   Browser (SSO) ──────► │  Keycloak (authN)   SpiceDB (authZ)   /jobs (cross-org)   token-exchange    │
        │                │  proxies Keycloak JWKS/metadata       "which projects → engine orgs can      │
        │ bearer (KC)    │                                        this user reach?"                      │
        ▼                └───────▲───────────────────────────────────────▲────────────────────────────┘
┌───────────────────────┐       │ backend-to-backend authZ call          │ client-creds + token exchange
│   GenAI Engine          │◄─────┘ (engine org-id set)                    │
│   - NEW Keycloak client │                                       ┌───────┴────────────┐
│     (SSO, validates     │  per-org API key (from connector)     │   ML Engine        │
│      platform tokens)   │◄──────────────────────────────────────│   (cross-org poll, │
│   - org_scope: SET      │                                       │    token exchange) │
│   - filters: org_id IN  │                                       └────────────────────┘
└───────────────────────┘
```

Three engine-side capabilities are added:

- **AuthN — new Keycloak client:** the engine validates platform-minted tokens and drives SSO.
- **AuthZ — platform-driven org set:** after authN, the engine asks the platform for the set of
  engine org IDs this user can reach (derived from project access) and sets the request scope to
  that **set**.
- **Set-scoped data access:** every filter becomes `org_id IN (scope_set)`; admin = unbounded.

---

## 4. Workstream A — New Keycloak auth client (authN) + platform-driven authZ

### 4.1 New auth client (authN)

Build a new auth handler that makes the engine a **Keycloak client** of the platform:

1. Reads the token, validates the signature against the platform's JWKS (fetched from the
   platform's proxied metadata endpoint), and pins issuer + audience.
2. For browser flows, drives the OIDC redirect/sign-in so a user arriving from the platform is
   transparently authenticated (no API-key paste). Tokens live in the auth module's memory with
   silent refresh — **not** localStorage (Convo 3).
3. On success, hands off to the authZ resolver (4.2) to obtain the caller's org set. **Until
   the resolver returns, the request is unscoped and gets zero access** (fail closed).
4. Gated behind the platform-URL config; unset = standalone API-key-only behavior.

The API-key validation path is preserved for standalone/service callers.

### 4.2 Platform-driven authZ (the org-id round trip)

After a platform token authenticates, the engine makes a **backend-to-backend** call to a
platform endpoint — *"which projects (→ engine org IDs) can this user access?"* — driven by
SpiceDB, and sets the request scope to that **set of UUIDs**. This is the decision reached in
Convo 3 and restated in the Nori 1:1: scope is resolved by querying the platform for the user's
project access and mapping 1:1 to engine orgs. (Embedding the org list in the token was
rejected — Keycloak can't be amended at mint time and JWTs blow past cookie limits at ~100–130
UUIDs, the V3 failure.)

Engine-side work:
- New client module (e.g. `src/clients/platform_authz_client.py`) calling the platform authZ
  endpoint with a **service credential** (not the user's browser token — must be unspoofable,
  per Convo 3). Cache per-(user, short TTL); define an invalidation story for when project
  access changes (§10.3).
- The request scope becomes `set[UUID] | None`. `None` stays "admin/unbounded."

❓ **Platform dependencies (must be built there):** the authZ endpoint backed by SpiceDB; the
SpiceDB schema registering engine orgs as children of projects/workspaces; JWKS proxying.

### 4.3 The scalar → set refactor

Convert the org scope from `Optional[UUID]` to `Optional[set[UUID]]` end-to-end:

1. **Introduce a central helper first** — `apply_org_filter(query, column, org_scope)` handling
   `None` (no filter), single, and set. Today there is no such helper; adding one shrinks the
   blast radius and gives the fuzz test something to assert against.
2. Migrate `get_org_scope`, `@enforce_org_scope`, `@enforce_query_org_scope`, and the ~35
   Pattern-C repo methods to the helper / set semantics.
3. **Keep the API-key path producing a singleton set** (`{api_key.org_id}`) so single-tenant
   behavior is unchanged and both auth paths converge on one representation.
4. Extend the existing fuzz/coverage test (`MULTI_TENANCY_DESIGN.md` §12) to assert no
   task-scoped repo method filters by a bare scalar anymore.

This is the single biggest chunk of engine work and is the prerequisite for the unified UI.

---

## 5. Workstream C — Unified UI / SSO (single pane, no selector)

**Decision (locked):** the engine UI is a **single unified view**. A logged-in user sees
everything they are authorized for across all their orgs at once — no org switcher, no
per-context bouncing. This is delivered by making the request scope a **set** (Workstream A.3)
and filtering `org_id IN (...)`.

Consequences:
- Deep links "just work" — the user's whole org set is always in scope, so any resource they
  are authorized for resolves directly (this is what makes §2.3 a non-issue).
- Aggregate/list endpoints return cross-org results; responses need an `org_id` discriminator so
  the UI can group/label. The v1 work already added `org_id` to task payloads, so the pattern
  exists — extend it to the other list/aggregate responses.

UI specifics (`genai-engine/ui/`): the engine becomes a Keycloak client (redirect to platform
login when unauthenticated); token kept in auth-module memory with silent refresh. The v1
`GET /users/me` + `AuthContext` plumbing is extended to carry the **set** of orgs (and the
admin/tenant render branch). No selector component is introduced.

---

## 6. Workstream D — ML engine cross-org jobs

Per Convos 2–3 and the Nori 1:1, with §2.5 validation:

1. **Cross-org job queue / dequeue.** Refactor the platform `/jobs` API so a suitably-scoped ML
   engine can dequeue across workspaces/orgs (today `post_dequeue_job(data_plane_id)` is
   single-data-plane). The ML engine gets a **cross-org Keycloak client** with permission to
   read the cross-org queue. ❓ platform work.
2. **Job carries `project_id`.** Already present on `Job`. Ensure every relevant `JobSpec`
   propagates it. Minor ml-engine change.
3. **Token exchange per job, via the connector.** On dequeue, the job runner reads the job's
   `project_id`, fetches that project's **connector** (each project has its own), and uses the
   connector's **org-scoped engine API key** to talk to the correct GenAI engine org. It
   **separately** exchanges its platform token for a workspace-scoped token to push results
   (metrics, etc.) back into the workspace that owns the project. ❓ Requires a platform
   token-exchange endpoint and `arthur_client` support — neither is visible in this repo.

**AuthZ asymmetry to keep in mind:** the ML engine runs jobs with the **org-level API key**
(sees *all* tasks in the org), while a human user's UI view is scoped to the orgs they can
reach. This plan adopts **org-as-grain** (no sub-org/per-project task subsetting); see §10.4.

---

## 7. Workstream E — Onboarding & ownership proof

### 7.1 New, platform-connected-from-birth engines
When the engine is platform-connected:
- Org creation in the engine **must** create a platform project (which registers the engine org
  in SpiceDB). The engine calls the platform with the user's bearer token to create it. ❓
  platform endpoint.
- The currently-**public** `tenant/signup` path must be **authenticated/gated** once the engine
  is platform-governed — it cannot mint orgs anonymously.

### 7.2 Existing standalone engines connecting later
- **Ownership proof = admin key.** A single-tenant engine's admin key (`org_id NULL`,
  cross-org) is something no SaaS tenant could ever hold, so the platform accepts it as proof
  the connector owns the whole engine — *"as part of connecting the engine they'll have to say
  this is the admin key for my engine, and that will allow them to link their engine to their
  workspace."* ✅ The admin-key concept exists and the heuristic is sound. Onboarding then
  auto-creates a default workspace + one project per existing engine org.
- After onboarding, RBAC flows through the platform/SpiceDB; admin-key mode still works for
  backward compat (just without RBAC).

---

## 8. Phasing & Sequencing

Ordered to keep each phase shippable and standalone-safe (no behavior change until the engine
is configured as platform-connected).

| Phase | Scope | Depends on | Risk |
|---|---|---|---|
| **P0** | Central `apply_org_filter` helper + fuzz test; refactor existing scalar filters through it (no behavior change). | — | Low — pure refactor on shipped v1. |
| **P1** | Org scope scalar → `set` end-to-end; API-key path emits singleton set. | P0 | Med — wide but mechanical. |
| **P2** | New Keycloak auth client (engine becomes KC client; validates platform tokens; fail-closed). | — (parallel) | Med — security-critical; lands with P3. |
| **P3** | Platform authZ client + project→org round trip → sets the org set. Engine does not trust platform tokens for access until this is in. | P1, P2, **platform endpoint** ❓ | High — cross-repo. |
| **P4** | Unified UI / SSO (engine as KC client, in-memory token, single-pane set-scoped view). | P3 | Med. |
| **P5** | ML engine cross-org dequeue + per-job token exchange via connector. | **platform + arthur_client** ❓ | High — cross-repo. |
| **P6** | Onboarding flows (new + standalone migration), gate org creation. | P3, platform | Med. |

P0–P1 are **entirely in this repo** and de-risk everything else; start there regardless of
platform readiness. P2 and P3 ship together — an authenticated-but-unscoped token must mean
zero access, never admin.

---

## 9. Assumptions Ledger (meetings vs. code)

| # | Assumption | Verdict | Reality |
|---|---|---|---|
| 1 | "~60 router functions inject single org." | ✅ Validated | 60 path + 11 query + ~35 repo ≈ 106 touch points, scalar org scope, scattered (no central helper). |
| 2 | "Engine UI stays in the engine (not lifted to platform)." | ✅ Confirmed (Nori 1:1) | *"The engine's not moving."* Engine keeps its UI and becomes a KC client. |
| 3 | "Project ↔ engine org is 1:1; tasks = applications." | ✅ Confirmed (Convo 3 + Nori 1:1) | Drives the authZ-by-proxy model; matches the v1 org/task data model. |
| 4 | "SSO is self-serviceable; RBAC is the gated lever." | ✅ Confirmed (Nori 1:1) | Standalone keeps admin-key login w/o RBAC; connecting unlocks org-scoped RBAC. |
| 5 | "Org creation endpoint is public; needs gating when connected." | ✅ Validated | `tenant/signup` is `@public_endpoint`, flag-gated. |
| 6 | "Admin key proves single-tenant ownership on connect." | ✅ Sound | `org_id NULL` = cross-org admin; reasonable proof heuristic. |
| 7 | "Engine already multi-tenant; orgs/tasks mapping held." | ✅ Validated | v1 shipped May 2026. |
| 8 | "ML engine does token-exchange per job, via the connector." | ❓ Partly | Job has `project_id`; client-creds auth + connector-by-id fetch exist; **explicit token exchange not present** — needs `arthur_client` + platform support. |
| 9 | "Platform proxies Keycloak JWKS/metadata (live)." | ❓ Unverifiable | Platform repo not present. Plausible; verify before relying. |
| 10 | "Resources are task-centric, org derivable from URL." | ⚠️ Mostly false, but moot | By-id endpoints carry a bare resource id; the unified set-scope model makes this irrelevant. |
| 11 | "Pull models into shared inference service for unit economics." | ❓ Out of scope here | Real and necessary for the $200/mo target, but a separate effort; this plan is auth/tenancy only. |

---

## 10. Weak Spots, Open Questions & Risks (the adversarial review)

### 10.1 Fail-closed is a hard design requirement, not a nicety
The new auth client must guarantee that a token which authenticates but has not yet been scoped
by the authZ resolver grants **zero** access — never cross-org/admin. Concretely: the
authenticated-but-unscoped state should be an explicit sentinel (e.g. empty set) that every
handler treats as 403, and P2 must never ship to a trusting state without P3. This is the
highest-severity correctness risk in the plan.

### 10.2 Backend-to-backend authZ latency & cache invalidation
A SpiceDB round trip per request is too slow; embedding orgs in the token is rejected (size).
The middle path (cache the user's org set with a short TTL) needs a defined **invalidation
story** when a user's project access changes — otherwise users see stale orgs (added or
removed). Unspecified in the meetings; needs a decision (event-driven invalidation vs. short
TTL vs. both).

### 10.3 Org-as-grain vs. project→subset-of-tasks
The taxonomy says *project ↔ a subset of an org's tasks*, but the engine grain is *org* and the
ML engine runs as the org key (sees all tasks). True project-level task subsetting would require
either syncing task-level state to SpiceDB (explicitly rejected) or layering a user-scoped task
filter on top of the org key for human reads while jobs stay org-scoped. **This plan ships
org-as-grain and defers subsetting to v2.** If product needs project-level isolation at launch,
it is a much bigger lift than the notes imply.

### 10.4 "Unregistered agents" / tasks created directly in the engine
Both convos liked the "task created in engine → appears as unregistered agent → user registers
it into a project" workflow, but there is no "unregistered/unmapped task" concept in the data
model today, and authZ-by-proxy means an unregistered task has no project to authorize against.
Needs a defined default (personal/default project? hidden until registered?). Unspecified.

### 10.5 Cross-VPC Keycloak connectivity — infra cost is a real constraint
The GenAI engine must reach the platform's Keycloak, likely **cross-VPC**. Zach floated a
private link; Nori flagged that **private link / VPN cost extra** and Zach backed off
(*"then no, we probably don't do that"*). So the connectivity approach is **open and
cost-sensitive** — prefer routing over the public proxied-metadata endpoint (TLS) rather than
dedicated private networking, unless a customer's posture forces otherwise. Needs an explicit
infra design + cost review before P3/P4.

### 10.6 ML engine multiplexing & on-prem reachability
A single SaaS ML engine serving many GenAI tenants works for SaaS but **cannot reach an on-prem
GenAI engine behind a firewall** (outbound-only design). The "one cross-org ML engine" model
needs an explicit carve-out for dedicated/on-prem engines. Still open.

### 10.7 Token exchange is an `arthur_client` + platform dependency
§2.5 / Assumption 8: the exchange is not in this repo. If `arthur_client` doesn't support
RFC-8693-style exchange, that's net-new library work on the critical path for P5.

### 10.8 Connector auto-creation & key lifecycle
Linking a project↔org auto-creates a connector storing the org's API key. **Rotation/revocation**
across two systems (engine `api_keys` table ↔ platform connector secret) is unspecified and is a
classic "works until the key rotates" outage source.

### 10.9 Unit-economics math depends on the inference split, not this plan
The 30–40-paying-tenant crossover (Convo 1) assumes models are pulled into a shared inference
service. None of the auth/tenancy work here moves the cost curve. Be explicit with stakeholders:
"platform-connected multi-tenancy" ≠ "cheaper engine"; the latter is the inference-service
project.

### 10.10 What could not be validated (platform repo absent)
Everything tagged ❓: the platform authZ endpoint, SpiceDB schema for engine orgs, JWKS proxying,
cross-org `/jobs`, and token exchange. **Roughly half the architecture lives in the
control-plane repo and is unvalidated here.** Recommend a companion review against that repo
before committing estimates for P3/P5/P6.

---

## 11. Recommended Next Steps

1. **Start P0–P1 now** (central org-filter helper + scalar→set) — in-repo, de-risks the rest,
   independent of platform readiness.
2. **Confirm the platform assumptions** (#8, #9, plus the authZ endpoint and token exchange)
   against the control-plane repo before estimating P3/P5.
3. **Design the cross-VPC Keycloak connectivity** with cost in mind (§10.5) — default to the
   public proxied-metadata path, not private link.
4. **Decide the authZ cache-invalidation strategy** (§10.2).
5. **Confirm org-as-grain for launch** (§10.3); defer project-level task subsetting to v2.
6. **Run this plan through an independent large-model adversarial review** (as Zach/Ian noted),
   focusing on §10.1 (fail-closed) and §10.2 (authZ caching/invalidation).
