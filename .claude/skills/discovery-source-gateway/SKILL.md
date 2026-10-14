---
name: discovery-source-gateway
description: States the Network & Gateway source-class contract for Shadow Agent Discovery, where an LLM gateway or proxy that callers route model traffic through reports which agents used which models (for example LiteLLM proxy, Kong Konnect, Cloudflare AI Gateway; self-hosted Kong Gateway is a SIEM query, see the Kong vendor file). Use when a vendor is classified `network_gateway`, when building or reviewing a gateway connector under ml-engine/src/ml_engine/discovery/network_gateway/, or when adding the class itself. Covers identity and record rules, connection and least privilege, lookback, errors, Test Connection and the tests that prove them.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Network & Gateway source class

The gates already refuse the mechanical mistakes: a connector missing from the registry or without `SENSITIVE_FIELDS` (`ml-engine/tests/unit/standalone/test_discovery_config.py`), an executor registry that disagrees with it (`ml-engine/tests/unit/job_executors/test_discover_agents_executor.py`), a record outside the output contract (`ml-engine/src/ml_engine/job_executors/discovery_output_contract.py`), and engine and Platform halves that disagree (the process skill's cross-repo invariant check). This skill is for what they cannot see: which identity a request proves, which rows are agents at all, whether the credential is least-privilege, and whether a record's keys still join next scan.

Read the source of truth rather than a restatement here:

- arthur-common `src/arthur_common/models/agent_governance_schemas.py`: the creation-source classes (class facts, validators, docstrings) and `SourceAddress`.
- `ml-engine/src/ml_engine/discovery/__init__.py:source_connectors()`: the registry.
- `ml-engine/src/ml_engine/job_executors/discovery_scan.py`: the scan Protocol, `AcceptsStopCheck`, `DiscoveryConfigurationError` and `failure_code`.
- `ml-engine/src/ml_engine/job_executors/discovery_source_test_executor.py`: how Test Connection classifies an exception, and its `PREVIEW_DEADLINE_SECONDS`.

Platform and UI steps belong to Arthur's internal discovery integration process skill.

## Vendors

- LiteLLM proxy: read [references/vendors/litellm.md](references/vendors/litellm.md) when building LiteLLM.
- Kong: read [references/vendors/kong.md](references/vendors/kong.md) when building Kong.
- Cloudflare AI Gateway: read [references/vendors/cloudflare.md](references/vendors/cloudflare.md) when building Cloudflare.
- OpenShell: read [references/vendors/openshell.md](references/vendors/openshell.md) when building OpenShell.

## Workflow

```
- [ ] 1. The class exists, or references/new-class.md is done first
- [ ] 2. The vendor is a gateway
- [ ] 3. Identity basis, external_id and fold rules decided for every row shape
- [ ] 4. Connection, least privilege, admin-only probe
- [ ] 5. Lookback, paging, completeness log
- [ ] 6. Errors and Test Connection
- [ ] 7. Tests: run, fix, repeat until green
- [ ] 8. A scan end to end
```

## 1. The class exists

```bash
grep -n 'NETWORK_GATEWAY' <arthur-common>/src/arthur_common/models/agent_governance_schemas.py
grep -n 'network_gateway' ml-engine/src/ml_engine/job_executors/fetch_discovered_agents_executor.py
```

No hit: read [references/new-class.md](references/new-class.md) first. The contract below is then a proposal the discovery owners approve before the arthur-common PR merges. The wire value is `network_gateway`: the Platform's coverage summary and the UI's coverage card already use it.

## 2. Is it a gateway

A vendor whose admin or usage API lists callers and their requests is `network_gateway`, with or without an agent registry (the registry is enrichment, never the identity grade). A gateway with no usage API, whose per-caller traffic exists only in logs or in the customer's SIEM, is `discovery-source-siem`: no new vendor or connector, just a documented query on an existing SIEM source, which must still follow §3's identity rules (namespaced external id, credential grouping, refused-request fold, provider-qualified models); one that lists deployed agents but sees no traffic is `discovery-source-cloud`.

## 3. Identity and the record

A gateway logs requests; grouping them into an agent is inferred. One record per **agent seen in the window** (a credential that sent nothing is not a record), graded by the strongest signal each request carries (`identity_basis`):

1. `registered_agent`: the request's agent id equals the agent its own credential is bound to. Grade by the credential's binding, never by the agent registry: a least-privilege key may not see the registry, and an empty registry answer does not mean there are no agents.
2. `claimed_agent`: any other agent id (from an unbound credential, a real agent's id sent from the wrong credential, an id the registry never issued).
3. `credential`: no agent id; grouped by credential.
4. `client_address`: no credential either.

| Part | Rule |
|---|---|
| `external_id` | The id for the record's basis (agent id, the gateway's credential id, client address), namespaced by gateway instance, e.g. `<vendor>:<instance>:<id>`, so records from two gateways or two sources never collide. External ids are permanent join keys in the GenAI Engine. Never the raw credential, never an alias (optional and reusable) |
| `name` | The agent's or credential's alias, else team alias + short id, else the id |
| `last_seen` | Newest request time in the window, refused requests included |
| `llm_models` | Distinct provider-qualified models actually served, sorted |
| `address.instance` | Gateway host from the parsed URL: lowercase host, port unless 443, path kept, never the netloc. One shared helper in the new `discovery/network_gateway/records.py` |
| `address.scope` | The team / workspace id when the gateway has one, else `None` |
| `address.resource_id` | The un-namespaced id the `external_id` is built from; `address.query` is absent |
| `observations` | `client_addresses`, `host_group` (team alias), `assigned_user` (only what the gateway attributes, never inferred). Check they survive the fetch: references/new-class.md §Fetch |
| `runs_on` / `platform` / `service_names` | Unset. A gateway does not know where the caller runs, and an alias is not a span's `service.name` |

Fold rules:

- A refused request (model not allowed, scope 403) joins its credential's record if one exists, never creates an agent of its own, and contributes `last_seen` but not models. Gateways may log such a request without its agent id.
- A request rejected because the caller's credential was invalid is not a caller: skip and count it.
- Rows that are calls to the gateway's own admin API are not agent traffic: skip and count them.

**Trace-identity invariant (every class).** A record becomes a GenAI Engine task; the customer's traces land on it only if the record's join keys (`observations.service_names` against the span's `service.name`, `address.resource_id` against `cloud.resource_id` where set) equal what the vendor's own telemetry puts on a real span. Check against a captured span, not the docs. A wrong key permanently splits one agent into two tasks. Without a captured span, leave `service_names` unset.

## 4. Connection and credentials

- Fields: `base_url` (must be https); one admin credential (sensitive); `ca_certificate` + `tls_verification` (`full|ca_only|off`), since gateways are often self-hosted behind private CAs, with the vendor marked as one where `ca_only` requires a CA certificate. A SaaS gateway on a fixed host takes an account id instead of `base_url` and TLS fields. `SENSITIVE_FIELDS` equals the catalog entry's secret fields.
- `https://` only, `discovery/address.py:address_problem`, `discovery/siem/tls.py:tls_session` (import it), `allow_redirects=False`, `(connect, read)` timeouts summing under 120 s.
- Least privilege: a read-only admin role, never the master key. Name it in the field `description` and the docs, and test that it can scan.
- **Probe an admin-only list first**, in the scan and in Test Connection, so a wrong role reads as `permission_denied` rather than `authentication_failed`: some gateways answer 401 to a valid non-admin credential on usage routes. A route that answers 200 for any valid credential cannot check the role.
- Read caller, team, model, time and status only; never request/response bodies or prompts. Never call a write route, even when the credential allows it. Enforcement through the gateway (blocking, guardrails, budgets) would be a separate feature with its own credential, customer opt-in and audit trail; each vendor reference lists that surface.

## 5. Lookback, paging, completeness

- Lookback is a window over traffic: `start = now - lookback_hours`, `end = now`, as the API's date filter. `lookback_hours <= 0` is everything retained: send the earliest date the API accepts and log that the window is the gateway's retention. Date formats, page sizes and caps come from the vendor's docs and are pinned in the connector's tests.
- Follow pages to the end, cap them, ask the stop check before each page (`AcceptsStopCheck` is structural; do not import it) and `return` cleanly. Retry idempotent GETs via `discovery/retry.py`.
- Records aggregate over all pages: collect, then yield `BATCH_SIZE` slices. Before the first batch, log requests read, records found, rows skipped by reason, and the capped total when the page cap was hit. A stop between pages yields the partial aggregate with a warning.
- Inventory enrichment (credential list, consumers) is optional; its 403 is a warning. Usage rows can land well after the request, so a Test Connection right after traffic may see none.

## 6. Errors and Test Connection

- Config faults (missing field, `http://`, bad TLS mode, a CA that will not load): `DiscoveryConfigurationError`; a CA-load failure is raised `from None`.
- Non-2xx, or a 200 that is not the usage shape: `<Vendor>Error(msg, status_code=n)` with a hint naming the least-privilege role.
- TLS handshake refused: `DiscoveryConfigurationError(...) from exc`. Unreachable or timed out: `raise type(exc)(msg) from exc`. Zero requests in the window is a success with a job-log line.
- Never put the vendor's auth error text in an exception or log: gateways echo masked credential fragments. Keep the type or code and add your own hint. Elastic's `_error_of` / `_reason_suffix` copy the vendor's reason into the exception; do not copy that part.

## 7. Files

Create `ml-engine/src/ml_engine/discovery/network_gateway/` with `__init__.py` (class docstring), `records.py` (shared row-to-record builder and instance helper) and `<vendor>/{__init__,client,connector}.py`. Add `network_gateway` to `_CREATION_SOURCE_TYPES` in `job_executors/fetch_discovered_agents_executor.py`, register in `source_connectors()`, write `tests/unit/discovery/test_<vendor>_connector.py` and a section in `ml-engine/docs/standalone-discovery.md`. Platform catalog entry: class `network_gateway`, query language none, availability preview.

## 8. Tests

Run `uv run pytest tests/unit/discovery/test_<vendor>_connector.py` from `ml-engine/`, fix, repeat. Cover: registration; request shape (date window, auth header, `allow_redirects=False`, timeout sum); paging to the end and the cap; aggregation (two requests by one credential: one record, both models, newest time); each identity basis, including a bound credential with no agent header; the fold rules; `external_id` namespacing; address; `check_batch` passes; zero traffic logs success; enrichment 403 warns; probe order turns a wrong role into 403; 401/403 carry `status_code`; malformed 200; http, userinfo and bad TLS mode refused; stop check before each page; credentials, masked fragments and bodies never in `caplog`. Pin captured live bodies inline.

- Build fixtures in the generated clients' shapes: enum members, not plain strings. `str()` and f-strings of a `(str, Enum)` member give its qualified name on Python 3.11+, so convert with `.value`.
- A test CA must carry keyUsage, or Python 3.13's strict X.509 check rejects it under `full`; use `ca_only` for a self-signed test CA.

## 9. End to end

Follow the process skill's local end-to-end recipe for the vendor: send traffic covering every identity basis (a bound credential, a claimed id from an unbound credential, a plain credential, one credential from two clients) plus a refused request; configure the source with the viewer credential; Test Connection; scan; check the Agents tab and that Network & Gateway is no longer a "No sensor" blind spot on the coverage grid.
