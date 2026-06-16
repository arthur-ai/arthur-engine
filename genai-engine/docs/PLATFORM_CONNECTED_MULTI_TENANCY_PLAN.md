# GenAI Engine — Platform-Connected Multi-Tenancy: Technical Plan

> **Status:** Research / design proposal (for adversarial review)
> **Date:** 2026-06-16
> **Source material:** Notion "2026 Engine Architecture Convo" (Convos 1–3), Fireflies transcripts
> `01KT7C5884KREC51V5NAFAS4R9` (Convo 1), `01KTCHXCADTZXRRCBDQ8B6HVWH` (Convo 2),
> `01KTS4893H7K9XE852CPRBS05J` (Convo 3), and direct code investigation of
> `genai-engine/` and `ml-engine/`.
> **Companion doc:** [`MULTI_TENANCY_DESIGN.md`](MULTI_TENANCY_DESIGN.md) (the shipped v1 org model this plan builds on).

---

## 0. How to read this document

This is a *research plan*, not an implementation spec. Every factual claim about the
current system has been checked against the code and is tagged:

- ✅ **Validated** — confirmed in this repo, with file references.
- ⚠️ **Partially true / overstated** — the meeting notes assert something the code only
  partly supports. These are the dangerous ones; read them carefully.
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
(`MULTI_TENANCY_DESIGN.md`, migrations `2026_05_19_*`). Concretely, ✅ validated in code:

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
already-multi-tenant engine to the platform's identity and authorization, make the org scope
a *set* instead of a *scalar*, and rework the ML-engine job path for cross-org fan-out."**

### 1.3 The taxonomy this plan assumes (from Convos 2–3)

| Control Plane (platform) | GenAI Engine | Notes |
|---|---|---|
| Project | **Engine Organization** | The connector that stores the org's API key lives on the project. Convo 3 settled on **project ↔ org** (not workspace ↔ org). |
| Application (née model) | **Task** | Mapping already held in the platform today; no AuthZ on applications directly — authZ is inherited through the project. |
| Workspace | (implicit boundary) | Workspace-level role grants reach all of the org's tasks. |

Authorization is done **by proxy**: the engine never syncs task-level ACLs to SpiceDB. The
platform answers "which engine org IDs can this user reach?" and the engine filters its own
data by those org IDs. The only engine state the platform needs to know about is **orgs**
(and the project↔org / application↔task mappings).

---

## 2. Current State — Validated Findings

### 2.1 Engine authentication: the "fork" is real but thinner than the notes imply

`src/auth/multi_validator.py:25` (`MultiMethodValidator.validate_api_multi_auth`) has **two**
branches, not three:

1. **API key** → `api_key_validator_client.validate(...)`; on success sets
   `request.state.org_scope = user.org_scope` (the key's `org_id`).
2. **JWT fallback** → `jwk_client.validate(token)`; on success sets `org_scope = None`
   (**always admin/cross-org**), per the in-code comment: *"JWT users are always cross-org
   admins in v1 — org_scope stays None."*

The JWT validator (`src/auth/jwk_client.py:21`) uses `PyJWKClient` against a **single JWKS
URI** built from the engine's *own* Keycloak config (`GENAI_ENGINE_INGRESS_URI` /
`KEYCLOAK_HOST_URI` + `KEYCLOAK_REALM`, see `src/utils/utils.py:get_auth_metadata_uri` and
`src/dependencies.py:206`). It validates the signature with `verify_signature: True` but
**`verify_aud: False` and does not inspect the `iss` (issuer) claim at all.**

⚠️ **This contradicts three statements in the Notion doc / Convo 3:**

- *"The engine already has a token validation fork… third handler that checks if the token's
  issuer matches the platform's Keycloak."* — There is **no issuer check today** and **no
  third handler**. The JWT branch is a single generic RS256/JWKS validator pointed at one
  configured Keycloak. The "issuer fork" is **work to build**, not work that exists.
- *"The engine environment variable `PLATFORM_URL` already drives where it trusts tokens
  from."* — **There is no `PLATFORM_URL` in the engine today.** Token trust is driven by the
  engine's own Keycloak env vars. (Convo 2's "issuer-fork code already exists" claim is the
  origin of this; it appears to be a half-memory of the legacy SHIELD Keycloak wiring.)
- *"Platform already proxies the Keycloak metadata endpoint (Ian confirmed live)."* — ❓ This
  is a **platform-side** capability; cannot be verified in this repo. It is plausible and the
  plan assumes it, but it is unvalidated here.

**Why this matters (security):** today JWT auth = full admin. If we simply point the existing
JWT branch at the platform's Keycloak, **every platform user instantly becomes a cross-org
admin on the engine.** The authZ round-trip (Section 4) is therefore not optional polish — it
is a prerequisite to trusting platform tokens at all.

### 2.2 Org scope is a scalar threaded everywhere — the "~60 functions" claim is accurate

✅ Validated. The scope is a single `Optional[UUID]`:

- Set on `request.state.org_scope` in `multi_validator.py`.
- Read by `get_org_scope(request) -> Optional[UUID]` (`src/dependencies.py:331`).
- Enforced by `@enforce_org_scope` (path, 60 endpoints) and `@enforce_query_org_scope`
  (query, 11 endpoints) in `src/utils/users.py`, plus ~35 repository `get_X_by_id(…,
  org_scope)` methods (Pattern C) that filter `WHERE org_id == org_scope`.
- `None` means "admin/cross-org" (filter skipped). It is **also** what an unauthenticated
  request looks like — `get_org_scope` itself warns about this ambiguity; it is only safe when
  paired with the auth dependency.

The filters are **scattered, not centralized** — every repo method inlines its own
`if org_scope is not None: q = q.filter(... == org_scope)`. There is no single choke point.

**Feasibility of scalar → set (`org_id IN (...)`):** mechanically straightforward per call
site, but there is no central helper to change, so it is a **wide** edit (the v1 doc counted
60 + 11 + ~35 ≈ 106 touch points). The denormalized `org_id` columns make the `IN` filter
efficient. Convo 3 explicitly weighed this ("we now have to go back and edit all the code we
changed… a couple hundred functions") — that estimate is roughly right in order of magnitude.

### 2.3 Resource URLs mostly do not carry the org — the "share link" problem is real

✅ Validated. List/create endpoints are task-scoped (`/api/v1/tasks/{task_id}/…`) but by-id
fetches are bare resource IDs: `GET /api/v1/continuous_evals/{eval_id}`,
`/prompt_experiments/{experiment_id}`, `/inferences/{inference_id}`, etc. **You cannot derive
the org from such a URL without first querying the resource** — and that query 404s unless the
caller's org scope already matches (Convo 3's circular-dependency discussion). This is the
crux of the org-selector-vs-unified-view decision in Section 5.

### 2.4 API keys & org-creation endpoint

✅ Validated. `DatabaseApiKey` (`src/db_models/auth_models.py:20`) has nullable `org_id`;
keys are bcrypt-hashed, base64 `id:secret` format. `NULL` org_id = admin (cross-org). The
only org-creation path is the **public** `POST /api/v2/tenant/signup`, gated by
`GENAI_ENGINE_DEMO_MODE` (returns 404 when off). The doc's "org creation is public, needs
gating for platform-connected engines" is correct.

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
- The `Job` object **already carries `project_id` and `data_plane_id`** (confirmed via
  `tests/.../mock_data_generator.py`). Some specs (e.g. `DiscoverAgentsJobSpec`) already carry
  `workspace_id`. `post_submit_jobs_batch(project_id=…)` and `put_agents(workspace_id=…)`
  already pass scope explicitly.
- Connectors are fetched by **`connector_id` alone** via
  `ConnectorsV1Api.get_sensitive_connector(connector_id)` — the platform is trusted to scope
  by the authenticated client. The `ShieldConnector` / `EngineInternalConnector` pull the
  genai-engine API key + endpoint from connector fields or from
  `GENAI_ENGINE_INTERNAL_API_KEY` env.

So the Convo-3 job plan (cross-org queue → read project_id off job → token-exchange for a
workspace-scoped token → fetch the project's connector → use its engine API key) is
**directionally feasible with the current shape**, and `project_id` is already in place. The
two genuinely new pieces are (a) the **cross-org dequeue** and (b) the **token exchange**,
both of which are platform + `arthur_client` work. ❓

---

## 3. Target Architecture (end state)

```
                         ┌─────────────────────────── Control Plane (platform repo — NOT in this workspace) ──┐
   Browser (SSO) ──────► │  Keycloak (authN)   SpiceDB (authZ)   /jobs (cross-org)   token-exchange endpoint   │
        │                │  proxies Keycloak metadata/JWKS       "which engine orgs can this user reach?"      │
        │ bearer (KC)    └───────▲───────────────────────────────────────▲───────────────────────────────────┘
        ▼                        │ backend-to-backend authZ call          │ client-creds + token exchange
┌───────────────────────┐       │ (org-id list)                          │
│   GenAI Engine          │◄─────┘                                        │
│   - 3rd auth handler:   │                                       ┌───────┴────────────┐
│     issuer == platform? │                                       │   ML Engine        │
│   - org_scope: SET      │  uses per-org API key (connector)     │   (cross-org poll, │
│   - filters: org_id IN  │◄──────────────────────────────────────│    token exchange) │
└───────────────────────┘                                        └────────────────────┘
```

Three engine-side capabilities are added:

- **A3 — Platform-token authN:** a third handler in `MultiMethodValidator` that recognizes
  the platform's issuer and validates against the platform-served JWKS.
- **AZ — Platform-driven authZ:** after authN, the engine asks the platform for the set of
  engine org IDs this user can reach and sets `request.state.org_scope` to that **set**.
- **Set-scoped data access:** every filter becomes `org_id IN (scope_set)`; admin = unbounded.

---

## 4. Workstream A — Engine accepts platform tokens (authN) + platform-driven authZ

### 4.1 Third auth handler (authN)

Add a third branch in `MultiMethodValidator.validate_api_multi_auth`
(`src/auth/multi_validator.py`) **before** falling through to the legacy JWT branch:

1. Decode the token *without* verification to read `iss`.
2. If `iss` matches the configured **platform** issuer (new `PLATFORM_URL` /
   `PLATFORM_ISSUER` env), validate the signature against the platform's JWKS (fetched from
   the platform's proxied metadata endpoint), with `verify_aud` configured to the engine's
   client/audience.
3. On success, **do not** set `org_scope = None`. Hand off to the authZ resolver (4.2).

Implementation notes / pitfalls:
- The existing `JWKClient` is a single-URI `PyJWKClient`. Generalize to **issuer-keyed**
  resolution (a small registry: issuer → `PyJWKClient`), so the legacy engine-Keycloak path
  and the platform path coexist. Keep `verify_aud: False` only if we cannot pin an audience;
  prefer pinning.
- Gate the whole platform path behind `PLATFORM_URL` being set — when unset, behavior is
  byte-for-byte today's (preserves standalone / API-key-only installs, a hard requirement
  from Convo 2).
- **Do not repurpose** the legacy SHIELD JWT branch silently; leave it for self-hosted
  Keycloak and add the platform branch alongside. Mixing them risks trusting the wrong issuer.

### 4.2 Platform-driven authZ (the org-id round trip)

After a platform token authenticates, the engine makes a **backend-to-backend** call to a new
platform endpoint — *"which engine org IDs can this user access?"* — driven by SpiceDB, and
sets `request.state.org_scope` to that **set of UUIDs**. This is the decision reached in
Convo 3 (rejecting both "embed orgs in the token" — Keycloak can't be amended at mint time and
JWTs blow past cookie limits at ~100–130 UUIDs, the V3 failure — and "sync engine state into
Keycloak groups").

Engine-side work:
- New client module (e.g. `src/clients/platform_authz_client.py`) that calls the platform
  authZ endpoint using a **service credential** (not the user's browser token — must be
  unspoofable, per Convo 3). Cache per-(user, short TTL) to avoid a round trip on every
  request; invalidate on org changes.
- `request.state.org_scope` becomes `set[UUID] | None`. `None` stays "admin/unbounded."

❓ **Platform dependencies (not in this repo, must be built there):**
- The endpoint itself ("list engine org IDs for user"), backed by SpiceDB.
- SpiceDB schema registering **engine orgs as children of projects/workspaces**.
- The platform proxying Keycloak JWKS/metadata (claimed live; verify).

### 4.3 The scalar → set refactor

Convert `org_scope` from `Optional[UUID]` to `Optional[set[UUID]]` end-to-end. To make ~106
touch points safe and reviewable:

1. **Introduce a central helper first** — e.g. `apply_org_filter(query, column, org_scope)`
   that handles `None` (no filter), single, and set. Today there is no such helper; adding one
   shrinks the blast radius and gives the fuzz test (below) something to assert against.
2. Migrate `get_org_scope`, `@enforce_org_scope`, `@enforce_query_org_scope`, and the ~35
   Pattern-C repo methods to the helper / set semantics.
3. **Keep the API-key path producing a singleton set** (`{api_key.org_id}`) so single-tenant
   behavior is unchanged and the two auth paths converge on one representation.
4. Extend the existing **fuzz/coverage test** (`MULTI_TENANCY_DESIGN.md` §12) to assert no
   task-scoped repo method filters by a bare scalar anymore.

This refactor is what enables the **unified, no-selector view** (Section 5). It is the single
biggest chunk of engine work in the plan.

---

## 5. Workstream C — UI / SSO and the "unified view vs. org selector" decision

This is **unresolved in the meetings** and is the most important product decision in the plan.
Two coherent end states (Convo 3 oscillates between them):

### Option C1 — Org selector (simpler)
Keep `org_scope` effectively single; on login the UI calls the platform for the user's orgs,
shows a selector, persists the choice (cookie/local state), and sends the chosen org with each
request. **Problem (the share-link trap, validated in §2.3):** a deep link to a resource in
org B fails for a user currently scoped to org A, because by-id endpoints 404 before the org
can be discovered. Mitigations discussed — embed org in every resource path (huge refactor,
rejected), org as query param on redirects (doesn't survive copy-paste links), or a public
"resolve org for resource id" endpoint (information-leak concern). None is clean.

### Option C2 — Unified view, no selector (better UX, more work)
Make `org_scope` a **set** (Workstream A.3) and filter `org_id IN (...)`. Links "just work"
because the user's whole set is always in scope; no selector, no per-resource org resolution.
This is the Palantir/Foundry experience Zach wants and **eliminates the share-link problem
entirely**. Cost: the full scalar→set refactor + aggregate endpoints now return cross-org
results (need an `org_id` discriminator on responses — the v1 doc already added `org_id` to
task payloads, so the pattern exists).

**Recommendation:** **C2.** The share-link problem has no clean solution under C1, and C2 is
the only option that satisfies the stated "unified experience" goal. The refactor cost is real
but bounded and is the same work that makes platform authZ (4.3) coherent. Treat the selector
as a *fallback* if C2 slips, not the target.

UI specifics (`genai-engine/ui/`): the v1 doc already wired `GET /users/me` +
`AuthContext`. For SSO we additionally need: the engine as a **Keycloak client** (redirect to
platform login when unauthenticated), token stored in auth-module memory with silent refresh
(not localStorage — Convo 3), and the admin/tenant render branch driven by the (now possibly
multi-org) scope.

---

## 6. Workstream D — ML engine cross-org jobs

Per Convo 2/3, with §2.5 validation:

1. **Cross-org job queue / dequeue.** Change the platform `/jobs` API so a suitably-scoped ML
   engine can dequeue across workspaces/orgs (today `post_dequeue_job(data_plane_id)` is
   single-data-plane). The ML engine gets a **cross-org Keycloak client**. ❓ platform work.
2. **Job carries `project_id`.** Already present on `Job`. Ensure every relevant `JobSpec`
   propagates it (some carry `workspace_id` today). Minor ml-engine change.
3. **Token exchange per job.** On dequeue, the ML engine exchanges its cross-org credential
   for a **workspace/org-scoped** token to actually execute (fetch connector, upload metrics).
   ❓ Requires platform token-exchange endpoint **and** `arthur_client` support — neither is
   visible in this repo.
4. **Connector holds the engine org API key.** When a project is linked to an engine org, a
   connector is auto-created storing an API key scoped to that engine org. The job uses
   `get_sensitive_connector(connector_id)` (already the pattern) to get the key, then talks to
   the correct engine org. The plan's "store the API key on the connector" maps cleanly onto
   the existing `ShieldConnector` field mechanism.

**Note the authZ asymmetry Ian raised (Convo 3, unresolved):** the ML engine runs jobs with
the **org-level API key** (sees *all* tasks in the org), while a human user may be authorized
for only a *subset* of that org's tasks (via project grants). If we ever do sub-org (project →
subset-of-tasks) granularity, the job runner and the UI will disagree about what's visible.
The meetings punted on this ("use org/task as the grain; fine-grained is too much state to
sync"). **This plan adopts org-as-grain** and explicitly defers project-level task subsetting
to v2 — see §10.4.

---

## 7. Workstream E — Onboarding & ownership proof

### 7.1 New, platform-connected-from-birth engines
When `PLATFORM_URL` is set:
- Org creation in the engine **must** be accompanied by creating a platform project (which
  registers the engine org in SpiceDB). The engine calls the platform with the user's bearer
  token to create the project. ❓ platform endpoint.
- The currently-**public** `tenant/signup` path must be **gated** (it cannot mint orgs
  un-authenticated once the engine is platform-governed). Reuse `GENAI_ENGINE_DEMO_MODE`-style
  flagging but require auth when platform-connected.

### 7.2 Existing standalone engines connecting later
- **Ownership proof = admin key.** A single-tenant engine's admin key (org_id NULL,
  cross-org) is something *no SaaS tenant could ever hold*, so the platform accepts it as proof
  the connector owns the whole engine. ✅ The admin-key concept exists and this heuristic is
  sound. Edge case: a multi-tenant standalone engine where the connecting party only owns *one*
  org must instead prove ownership with that **org's** API key (not an admin key) — the plan
  must handle both ("admin key → onboard all orgs into a default workspace, one project per
  org" vs "org key → onboard that one org").
- After onboarding, authZ flows through SpiceDB; API-key mode still works for backward compat.

---

## 8. Phasing & Sequencing

Ordered to keep each phase shippable and standalone-safe (no behavior change until
`PLATFORM_URL` is set).

| Phase | Scope | Depends on | Risk |
|---|---|---|---|
| **P0** | Central `apply_org_filter` helper + fuzz test; refactor existing scalar filters to route through it (no behavior change). | — | Low — pure refactor on shipped v1. |
| **P1** | `org_scope` scalar → `set` end-to-end; API-key path emits singleton set. | P0 | Med — wide but mechanical. |
| **P2** | Third auth handler (platform issuer) behind `PLATFORM_URL`; issuer-keyed JWKS. | — (parallel) | Med — **security-critical**; must land with P3. |
| **P3** | Platform authZ client + org-id round trip → sets `org_scope` set. Engine NOT trusting platform tokens until this is in. | P1, P2, **platform endpoint** ❓ | High — cross-repo. |
| **P4** | UI SSO (engine as KC client, in-memory token, unified view). | P3 | Med. |
| **P5** | ML engine cross-org dequeue + token exchange + connector. | **platform + arthur_client** ❓ | High — cross-repo. |
| **P6** | Onboarding flows (new + standalone migration), gate public org creation. | P3, platform | Med. |

P0–P1 are **entirely in this repo** and de-risk everything else; they are the right place to
start regardless of platform readiness. P2 without P3 is a **security hole** (every platform
user = admin) and the two must ship together.

---

## 9. Assumptions Ledger (what the meetings asserted vs. what the code says)

| # | Assumption in doc/convos | Verdict | Reality |
|---|---|---|---|
| 1 | "Issuer-fork / third handler already exists." | ⚠️ Overstated | Only API-key + one generic JWT branch exist; **no issuer check, no third handler.** Must be built. (`multi_validator.py`, `jwk_client.py`) |
| 2 | "`PLATFORM_URL` already drives token trust." | ⚠️ False today | No such env var; trust is the engine's own Keycloak. New var to add. |
| 3 | "Platform proxies Keycloak JWKS/metadata (live)." | ❓ Unverifiable | Platform repo not present. Plausible; verify before relying. |
| 4 | "~60 router functions inject single org." | ✅ Validated | 60 path + 11 query + ~35 repo ≈ 106 touch points, scalar `org_scope`. |
| 5 | "Scalar→list refactor is doable but a big lift." | ✅ Validated | True; no central helper today (add one first). |
| 6 | "Org creation endpoints are public, need gating." | ✅ Validated | `tenant/signup` is `@public_endpoint`, flag-gated. |
| 7 | "Admin key proves single-tenant ownership." | ✅ Sound | `org_id NULL` = cross-org admin; reasonable proof heuristic. Handle multi-tenant-standalone edge. |
| 8 | "Engine already multi-tenant; orgs/tasks mapping held." | ✅ Validated | v1 shipped May 2026. |
| 9 | "ML engine token-exchange per job." | ❓ Partly | Job has `project_id`; client-creds auth exists; **explicit token exchange not present** — needs `arthur_client` + platform support. |
| 10 | "JWT users today are scoped." | ⚠️ Opposite | JWT users are **admin/cross-org** (`org_scope=None`). Trusting platform tokens naively = privilege escalation. |
| 11 | "Resources are task-centric, org derivable from URL." | ⚠️ Mostly false | By-id endpoints carry a bare resource id, **not** task/org — the share-link problem. |
| 12 | "Pull models into shared inference service for unit economics." | ❓ Out of scope here | Real and necessary for the $200/mo target, but a separate effort; this plan is auth/tenancy only. |

---

## 10. Weak Spots, Open Questions & Risks (the adversarial review)

### 10.1 Trusting platform tokens before authZ exists = privilege escalation (highest risk)
Because the JWT path currently yields admin scope (Assumption 10), Phase 2 must **never** ship
without Phase 3. A platform token that authenticates but isn't yet scoped must be treated as
**zero** access, not admin. Recommend: the third handler sets a sentinel
(`org_scope = frozenset()` / "authenticated-but-unscoped") that the authZ resolver *must*
replace; any handler seeing the sentinel returns 403.

### 10.2 The share-link / cross-org navigation problem has no clean answer under a selector
Validated in §2.3. If product insists on an org selector (C1), we inherit an unsolved
problem. The plan recommends C2 (unified set scope) precisely to make it disappear. **Decision
needed.**

### 10.3 Backend-to-backend authZ latency & caching
A SpiceDB round trip per request is too slow; embedding orgs in the token is rejected (size).
The middle path (cache the user's org set with short TTL) needs an **invalidation story** when
a user's project access changes, or users see stale orgs. Unspecified in the meetings.

### 10.4 Org-as-grain vs. project→subset-of-tasks (the unresolved Convo 3 thread)
The taxonomy says *project ↔ subset of an org's tasks*, but the engine grain is *org* and the
ML engine runs as the org key (sees all tasks). True project-level task subsetting would
require either (a) syncing task-level state to SpiceDB (explicitly rejected) or (b) a
user-scoped task filter layered on top of the org key for *human* reads while jobs stay
org-scoped. The plan **defers this to v2** and ships org-as-grain. If product needs
project-level isolation at launch, this is a much bigger lift than the notes imply.

### 10.5 "Unregistered agents" / tasks created directly in the engine
Both convos liked the "task created in engine → appears as unregistered agent → user
registers it into a project" workflow, but the data model has no "unregistered/unmapped task"
concept today, and §10.4's authZ-by-proxy means an unregistered task has *no* project to
authorize against. Needs a defined default (land in a personal/default project? hidden until
registered?). Unspecified.

### 10.6 ML engine multiplexing & on-prem reachability
A single SaaS ML engine serving many GenAI tenants works for SaaS, but **cannot reach an
on-prem GenAI engine behind a firewall** (outbound-only design). The "one cross-org ML engine"
model needs an explicit carve-out for dedicated/on-prem engines. Convo 2 flagged this as
"need to sit with it"; still open.

### 10.7 Token exchange is an `arthur_client` + platform dependency
§2.5 / Assumption 9: the exchange is not in this repo. If `arthur_client` doesn't support
RFC-8693-style exchange, that's net-new library work on the critical path for P5.

### 10.8 Connector auto-creation & key lifecycle
"Auto-create a connector storing the org API key when linking project↔org" implies the engine
mints an org-scoped API key and hands it to the platform to store. Key **rotation/revocation**
across two systems (engine `api_keys` table ↔ platform connector secret) is unspecified and is
a classic source of "works until the key rotates" outages.

### 10.9 Unit-economics math depends on the inference split, not this plan
The 30–40-paying-tenant crossover (Convo 1) assumes models are pulled into a shared inference
service. None of the auth/tenancy work here moves the cost curve. Be explicit with stakeholders
that "platform-connected multi-tenancy" ≠ "cheaper engine"; the latter is the inference-service
project.

### 10.10 What could not be validated (platform repo absent)
Everything tagged ❓: the platform authZ endpoint, SpiceDB schema for engine orgs, JWKS
proxying, cross-org `/jobs`, and token exchange. **Roughly half the architecture lives in the
control-plane repo and is unvalidated here.** Recommend a companion review against that repo
before committing to estimates for P3/P5/P6.

---

## 11. Recommended Next Steps

1. **Start P0–P1 now** (central org-filter helper + scalar→set) — in-repo, de-risks the rest,
   independent of platform readiness.
2. **Confirm the three platform assumptions** (#1–3, JWKS proxy, authZ endpoint, token
   exchange) against the control-plane repo before estimating P3/P5.
3. **Make the C1-vs-C2 product call** (selector vs unified view) — recommend C2.
4. **Decide org-as-grain vs. project subsetting for launch** (§10.4) — recommend org-as-grain
   for v1, defer subsetting.
5. **Run this plan through an independent large-model adversarial review** (as Zach/Ian noted),
   focusing on §10.1 (privilege escalation) and §10.3 (authZ caching/invalidation).
