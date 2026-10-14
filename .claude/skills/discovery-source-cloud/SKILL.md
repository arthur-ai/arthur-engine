---
name: discovery-source-cloud
description: States the Cloud source-class contract for Shadow Agent Discovery, where a provider's list API enumerates deployed agents or apps in a customer account (for example GCP Vertex Agent Engine, AWS Bedrock AgentCore, Azure AI Foundry, Vercel). Use when a vendor is classified `cloud`, or when building, reviewing or changing a connector under ml-engine/src/ml_engine/discovery/cloud/. Covers the record rules, connection and least privilege, lookback, errors, Test Connection, what to copy and the tests that prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cloud source class

The gates already refuse the mechanical mistakes: a connector missing from the registry or without `SENSITIVE_FIELDS` (`ml-engine/tests/unit/standalone/test_discovery_config.py`), an executor registry that disagrees with it (`ml-engine/tests/unit/job_executors/test_discover_agents_executor.py`), a record outside the output contract (`ml-engine/src/ml_engine/job_executors/discovery_output_contract.py`), and engine and Platform halves that disagree (the process skill's cross-repo invariant check). This skill is for what they cannot see: whether an id is globally unique and stable, whether a join key matches a real span, whether the role is least-privilege, and which faults are the user's.

Read the source of truth rather than a restatement here:

- arthur-common `src/arthur_common/models/agent_governance_schemas.py`: `CloudAgentCreationSource` (class facts, the required-region validator), `SourceAddress`, `RunsOn`.
- `ml-engine/src/ml_engine/discovery/__init__.py:source_connectors()`: the registry.
- `ml-engine/src/ml_engine/job_executors/discovery_scan.py`: the scan Protocol, `AcceptsStopCheck`, `DiscoveryConfigurationError` and `failure_code`.
- `ml-engine/src/ml_engine/job_executors/discovery_source_test_executor.py`: how Test Connection classifies an exception, and its `PREVIEW_DEADLINE_SECONDS`.

Platform and UI steps belong to Arthur's internal discovery integration process skill.

## Vendors

- GCP Vertex Agent Engine: read [references/vendors/vertex.md](references/vendors/vertex.md) when building or changing Vertex.
- Vercel: read [references/vendors/vercel.md](references/vendors/vercel.md) when building Vercel.
- Azure AI Foundry: read [references/vendors/azure-ai-foundry.md](references/vendors/azure-ai-foundry.md) when building Foundry.
- AWS: read [references/vendors/aws.md](references/vendors/aws.md) when building an AWS source.

## Workflow

```
- [ ] 1. The vendor is cloud
- [ ] 2. Record fields decided: external_id, address, last_seen, service_names
- [ ] 3. Connection, one credential, least-privilege role, no content calls
- [ ] 4. Paging, stop check, batching; lookback ignored
- [ ] 5. Errors and Test Connection
- [ ] 6. Copy the closest connector, register it, document it
- [ ] 7. Tests: run, fix, repeat until green
- [ ] 8. A scan end to end
```

## 1. Is it cloud

A cloud source asks a provider's inventory API which agents are deployed in an account. It sees what exists, not what ran: no traffic, no hosts, no query. A customer-written query over logs is `discovery-source-siem`, per-device inventory from an MDM is `discovery-source-endpoint`, and a proxy that reports its callers is `discovery-source-gateway`.

## 2. The record

| Part | Rule |
|---|---|
| `external_id` | The vendor's globally unique resource name, verbatim. With none, compose one from stable ids and document the format in the connector docstring and docs. Never a display name |
| `address.instance` | The account (project, account, subscription, team id); lowercase if the vendor is case-insensitive |
| `address.scope` | The region; `"global"` when the vendor has none. Required by the class validator |
| `address.resource_id` | The vendor's id for the agent; `address.query` is absent |
| `name` | Display name, else the id |
| `last_seen` | The resource's update time, else create time. A resource with neither is skipped with a warning naming its id, never stamped with `now()` |
| `runs_on` | Only when `RunsOn` already has the provider; never add a member for one vendor |
| `llm_models` | Only if the API states the model; never guessed from names |
| `observations.service_names` | Only a value unique across the customer's services and equal to the `service.name` the vendor's own spans carry. Never a short project or app name: the GenAI Engine's resolver claims every service name a record carries, so a project called `web` would capture unrelated traces |

**Trace-identity invariant (every class).** A record becomes a GenAI Engine task; the customer's traces land on it only if the record's join keys (`observations.service_names` against the span's `service.name`, `address.resource_id` against `cloud.resource_id` where set) equal what the vendor's own telemetry puts on a real span. Check against a captured span, not the docs. A wrong key permanently splits one agent into two tasks. If the key must also match what an older integration stored, carry both forms. Without a captured span, leave `service_names` unset and say so in the docstring and the PR.

## 3. Connection and credentials

- Fields: the account locator(s), non-sensitive and required; region optional with a documented default; **one** credential, secret in the catalog and listed in `SENSITIVE_FIELDS`.
- Least privilege: read-only on the inventory API only. Built-in "user" roles are often wider than they look; prefer a reader role plus a custom role with only the agent-list action. Name it in the field `description` and the docs.
- **Never call content endpoints**, even when the role allows them: the narrowest agent-read role can also read conversations. Call only list or describe, and pin with a test that the fake session saw no other path.
- SDK vendors: build the client from the pasted credential, validating its shape before contact (`DiscoveryConfigurationError` naming the field). Ambient credentials (ADC, instance roles) are opt-in by an engine env flag, never the default.
- HTTP vendors on a fixed public host, or with a data-plane host discovered through the control plane: no URL field and no TLS fields; `allow_redirects=False`; `(connect, read)` timeouts summing under 120 s; an `SSLError` re-raised as the same type, not retried.

## 4. Lookback, paging, batching

- **Lookback is ignored**: the list API is an inventory, not a log. Say so in a docstring and the docs section, and pin it with a test (`test_the_lookback_is_not_applied`).
- Page with the SDK pager or the vendor cursor; stop on a repeated cursor; cap pages. Retry only idempotent GETs through `discovery/retry.py`.
- Yield `BATCH_SIZE = 100` records per batch. When a record needs a per-resource call, you may collect first so completeness is logged before the first yield; say the trade-off in the docstring.
- Implement `AcceptsStopCheck.stop_when` when you page or make per-resource calls (structural; do not import it): ask before every call and before each backoff sleep, then `return` cleanly.

## 5. Errors and Test Connection

- Config faults (missing locator, malformed credential, unknown region) raise `DiscoveryConfigurationError`, never a plain `ValueError`: a plain `ValueError` reads as configuration in Test Connection but as `provider_error` on a scan.
- A 404 on the account locator is the user's config: `DiscoveryConfigurationError` naming the field, no status, no chain, no `HTTP nnn` in the text.
- Non-2xx: HTTP clients raise `<Vendor>Error(msg, status_code=n)`; SDK clients set `status_code` on the SDK exception and re-raise it unwrapped. A 200 that is not the vendor's shape is `<Vendor>Error(..., status_code=200)`.
- TLS refused: `DiscoveryConfigurationError(...) from exc`. Unreachable: `raise type(exc)(msg) from exc`. Error text names the field and the fix, never the value.
- Zero resources is a success with a job-log line. A resource the control plane lists but whose data plane cannot be reached is **partial**, not empty: log which were unreachable before the first yield and keep the records you got.

## 6. What to copy

- SDK list API: `ml-engine/src/ml_engine/discovery/cloud/gcp_vertex/connector.py` (#2395): injectable `lister`, `with_vendor_status`, `record_for`.
- HTTP list API: the record shape from `gcp_vertex`; the HTTP client and error model from `discovery/siem/elastic_security/client.py`; retries from `discovery/retry.py`.

Then register in `source_connectors()`, add `tests/unit/discovery/test_<vendor>_connector.py`, and a section in `ml-engine/docs/standalone-discovery.md` saying `query_language: none` and that lookback is ignored. Import shared helpers, even across classes; never copy them. Platform catalog entry: class cloud, query language none, availability preview until a live account was scanned.

## 7. Tests

Run `uv run pytest tests/unit/discovery/test_<vendor>_connector.py` from `ml-engine/`, fix, repeat. Cover: registration; `record_for` builds the address; a resource without region gets the documented default; a resource without timestamps is skipped and warned; `check_batch` passes; lookback is not applied (the fake receives no time filter); paging follows the cursor and stops on a repeat; stop-before-call sends nothing; 401/403 carry `status_code`; a missing locator is `NOT_CONFIGURED`; malformed 200 is the vendor's error; only list/describe paths are called; the credential never appears in `caplog`. If the connector sets `service_names` or a joining `resource_id`, pin a captured span's resource attributes (`test_service_names_match_a_captured_<vendor>_span`). Pin captured live bodies inline; without sandbox access, build bodies from the vendor's published SDK models, say so in the PR, and keep availability preview.

- Build fixtures in the generated clients' shapes: enum members, not plain strings. `str()` and f-strings of a `(str, Enum)` member give its qualified name on Python 3.11+, so convert with `.value`.

## 8. End to end

Follow the process skill's local end-to-end recipe: configure the source in the UI, run Test Connection, scan, and check the Agents tab shows the records with the cloud mark and the region.
