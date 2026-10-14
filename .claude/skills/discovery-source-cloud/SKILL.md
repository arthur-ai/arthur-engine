---
name: discovery-source-cloud
description: The Cloud source-class contract for Shadow Agent Discovery (a provider's list API enumerates deployed agents or apps, e.g. GCP Vertex Agent Engine, AWS Bedrock AgentCore, Azure AI Foundry, Vercel). Use once a vendor is classified `cloud`, or when reviewing or changing a cloud connector under ml-engine/src/ml_engine/discovery/cloud/. It says what a cloud record must carry, how to connect, how lookback and Test Connection behave, what to copy, and which tests prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Cloud source class

This skill owns what is true of every **cloud** source in the engine (`ml-engine/`). Platform and UI steps are covered by Arthur's internal discovery integration process skill. Re-read the code named here before copying it; symbols are stable, line numbers are not.

## 1. What a cloud source is

A cloud source asks a provider's **inventory** API "which agents are deployed in this account?" and turns each one into a record. It sees what exists, not what ran: no traffic, no hosts, no query. Pick `cloud` when the vendor exposes a list/describe API for agent or app resources inside a customer account.

| If the vendor... | Class |
|---|---|
| lists deployed agents/apps in an account (Vertex reasoning engines, Bedrock agents, Foundry projects, Vercel projects) | **cloud** |
| answers a customer-written query over logs | `discovery-source-siem` |
| reports per-device inventory from an MDM | `discovery-source-endpoint` |
| proxies LLM traffic and reports callers (LiteLLM, Kong, Cloudflare AI Gateway) | `discovery-source-gateway` |

## 2. The record contract (arthur-common `CloudAgentCreationSource`)

| Part | Rule | Where it is enforced |
|---|---|---|
| Creation source | `CloudAgentCreationSource(vendor=VENDOR, address=..., observations=...)`. Class facts are fixed: `DETECTION=OBSERVED`, `VISIBILITY_CEILING=LIMITED`, `OBSERVABLE_FIELDS={version, service_names, host_group}` | `agent_governance_schemas.py` |
| `address.instance` | The account: GCP project id, AWS account id, Azure subscription, Vercel team id. Stable and lowercase-normalised if the vendor is case-insensitive | convention |
| `address.scope` | **Required.** The region (`us-central1`, `us-east-1`); `"global"` when the vendor has none (Vercel). Constructing without it raises `ValidationError` | `_region_is_part_of_the_address` validator |
| `address.resource_id` | The vendor's id for the agent (engine id, agent id, project id) | convention |
| `address.query` | Absent. Cloud sources enumerate, they do not search | class docstring |
| `external_id` | The vendor's **globally unique** resource name, verbatim (Vertex: `projects/<n>/locations/<r>/reasoningEngines/<id>`). When the vendor has none, compose one from stable ids and document the format in the connector docstring and the docs section (Azure AI Foundry: `azure://{ARM project resource id}/agents/{agent id}`). Never a display name | `DiscoveryOutputRecord` (non-blank) |
| `name` | Display name, else the id | non-blank |
| `last_seen` | The resource's `update_time`, else `create_time`. A resource with neither is **skipped with a warning**, never stamped with `now()` (that would fake freshness) | Vertex `record_for` |
| `runs_on` | Set only when `RunsOn` has the provider (`aws`, `azure`, `gcp`). Otherwise leave it `None`; do not add an enum member for one vendor (arthur-common contract change) | `RunsOn` enum |
| `observations.service_names` | Only a value that is **unique across the customer's services** and equal to the `service.name` the vendor's own spans carry (see the trace-identity invariant below). Vertex stores its full resource path `projects/<n>/locations/<r>/reasoningEngines/<id>` to match the keys the older Vertex poller wrote. Real Vertex spans carry the bare engine id, so on `dev` `fa026cfe` an agent instrumented after discovery gets a second task. That was tested on a copy of a local GenAI Engine database on 2026-10-13; do not copy it. Never a short project/app name: GenAI Engine's resolver claims every service name a record carries, so a project called `web` would capture unrelated traces | Vertex sets it; Vercel #2433 omits it on purpose |
| `llm_models` | Only if the API states the model; never guess from names | optional column |


**Trace-identity invariant (every class).** Discovery's job is to find every agent. Each record becomes a GenAI Engine task with provenance, and traces are the customer's to send. They only land on the discovered task if the keys the record stores for joining equal what that vendor's own telemetry puts on a real span. Those keys are `observations.service_names`, matched against the span's `service.name`, and the address `resource_id`, matched against `cloud.resource_id` where the vendor sets it.
- **Check it against a captured real span**, not the docs. Pin the span's resource attributes in a test.
- **Mappings are immutable.** A wrong key permanently splits one agent into a discovered task and a second, traced task.
- **If the key must also match what an older integration stored**, carry both forms.
- **If you cannot capture a real span**, leave `service_names` unset and say so in the docstring and the PR.

## 3. Connection and credentials

- Fields (the Platform catalog entry; model it on GCP Vertex's): the account locator(s) (`project_id`, `account_id`, `team_id`) non-sensitive and required; region optional with a documented default; **one** credential, secret in the catalog and listed in the connector's `SENSITIVE_FIELDS`.
- `SENSITIVE_FIELDS: ClassVar[frozenset[str]]` on the connector names the credential keys. Standalone mode refuses a connector without it (`tests/unit/standalone/test_discovery_config.py:test_every_registered_connector_declares_its_secrets`), and its contents must equal the catalog entry's secret fields. Nothing in this repo checks that equality; the process skill's cross-repo invariant check does.
- **Never call content endpoints, even when the role allows them.** Some providers' narrowest role also reads conversations (Azure `Microsoft.CognitiveServices/accounts/AIServices/agents/read` is documented as "Read agents, threads, and messages"). Call only the agent list or describe calls (Foundry `/agents`), never threads, conversations, messages or responses, and pin that with a test that the fake session saw no other path.
- Least privilege: a read-only role on the inventory API only. Built-in "user" roles are often too wide (Foundry User grants `Microsoft.CognitiveServices/*` data actions and listkeys), so prefer Reader plus a custom role with only the agent read action (Vertex `aiplatform.reasoningEngines.list`; Vercel a Viewer-role team token). Name the role in the field's `description` and the docs section.
- Ambient credentials (ADC, instance roles) are opt-in by an engine env flag (Vertex `ARTHUR_ENGINE_GCP_VERTEX_ALLOW_ADC`), never the silent default.
- SDK vendors: build the SDK client from the pasted credential; validate the credential's shape before contact and raise `DiscoveryConfigurationError` naming the field.
- Two-plane vendors (Azure): one credential, but two token audiences (`management.azure.com` for ARM, `ai.azure.com` for the data plane), and a per-account data-plane host discovered through ARM. So there is no URL field, and no fixed host either; do not add an `https` URL field for it.
- HTTP vendors (no SDK, e.g. Vercel): fixed public host, so **no** URL field, no must-be-https field in the catalog and no TLS fields; `allow_redirects=False`; `(connect, read)` timeouts whose sum stays under 120 s; an `SSLError` is re-raised as the same type, not retried (it reads as a proxy/CA problem on the engine host).

## 4. Lookback, paging, batching

- **Lookback is ignored.** The list API is an inventory, not a log. Say so in a docstring and the standalone docs section, and pin it with a test (`test_the_lookback_is_not_applied`).
- Page with the SDK pager or the vendor cursor; stop on a repeated cursor and cap pages (Vercel: 100 pages). Retry only idempotent GETs through `discovery/retry.py`.
- Batch `BATCH_SIZE = 100` records per yield. When the record needs more than one call per resource (list then per-resource detail), you may collect first so completeness is logged before the first yield; say that trade-off in the docstring (a mid-scan failure then publishes nothing).
- Implement `AcceptsStopCheck.stop_when(should_stop)` whenever you page or make per-resource calls. It is structural (`job_executors/discovery_scan.py`; do not import the Protocol): the check is handed in before `scan`, and you ask it before every call and before each backoff sleep, then `return` cleanly. Test Connection's 120 s deadline (`PREVIEW_DEADLINE_SECONDS` in `job_executors/discovery_source_test_executor.py`) relies on it.

## 5. Errors and Test Connection

The shared error model, which both the scan and Test Connection read:

| Situation | Raise | Scan `failure_code` / Test Connection category |
|---|---|---|
| Config fault (missing field, malformed credential, unknown region) | `DiscoveryConfigurationError` (a `ValueError`) | `not_configured` / `configuration` |
| Vendor answered non-2xx | HTTP: `<Vendor>Error(msg, status_code=n)`. SDK: set `status_code` on the SDK exception and re-raise it unwrapped (Vertex `with_vendor_status`) | 401 `authentication_failed` / `authentication`; 403 `permission_denied` / `authorization`; else `provider_error` / `vendor_error` |
| 200 whose body is not the vendor's shape | `<Vendor>Error(..., status_code=200)` | `provider_error` / `vendor_error` |
| TLS handshake refused | `DiscoveryConfigurationError(...) from exc` | `not_configured` / `configuration` |
| Host unreachable or timed out | the same type: `raise type(exc)(msg) from exc` | `provider_error` / `network` or `timeout` |

Error text names the field and the fix, never the value. Cloud-specific rules:

- Config faults (missing locator, malformed key JSON, unknown region) raise **`DiscoveryConfigurationError`**, never a plain `ValueError`: a plain `ValueError` reads as `configuration` in Test Connection but as `provider_error` on a scan. (Vertex's missing `project_id` path still raises `ValueError`; do not copy that.)
- A 404 on the account locator is the user's config (`DiscoveryConfigurationError` naming the field, no status, no chain, no `HTTP nnn` in the text).
- Zero resources is a success with a job-log line, not an error. But a resource the control plane lists while its data plane cannot be reached is **partial**, not empty (Azure: a project with `publicNetworkAccess=Disabled` is listed by ARM and its agents call times out). Log which resources were unreachable before the first yield, and keep the records you did get.

## 6. What to copy (arthur-engine `ml-engine/`)

Verified on 2026-10-12 against arthur-engine `dev` `4de52ab4` and arthur-common `main` `600a527f`. Paths drift: if a file named here is missing, find the symbol, then update this line. The process skill's cross-repo invariant check is the guard that the engine and Platform halves agree.

| Vendor shape | Copy | Files |
|---|---|---|
| SDK list API | `ml-engine/src/ml_engine/discovery/cloud/gcp_vertex/connector.py` (#2395): injectable `lister`, `with_vendor_status`, `record_for` | `cloud/<vendor>/__init__.py`, `connector.py` |
| HTTP list API | record shape from `gcp_vertex`; HTTP client and error model from `siem/elastic_security/client.py` (`client_factory` seam); retries from `discovery/retry.py`. Vercel (arthur-engine #2433) is the worked example once merged | `cloud/<vendor>/__init__.py`, `client.py`, `connector.py` |

Then:

- Register in `discovery/__init__.py:source_connectors()`: import `VENDOR as <X>_VENDOR` and the connector class, add the dict entry, add both names to `__all__`. `tests/unit/job_executors/test_discover_agents_executor.py` checks the executor registry matches.
- `tests/unit/discovery/test_<vendor>_connector.py`.
- A `docs/standalone-discovery.md` section saying `query_language: none` and that lookback is ignored.
- Shared helpers are imported, never copied, even across classes (Vercel imports `endpoint/scope.py:parse_group_names` for its include list).

## 7. Checklist

- [ ] `external_id` is the vendor's globally unique name; `scope` always set; `runs_on` only from the existing enum.
- [ ] `service_names` set only if globally unique and equal to a captured span's `service.name` (or to both forms when an older integration's keys must also match), with a comment saying why (or why not).
- [ ] Records without a timestamp are skipped with a warning naming the resource id, not its contents.
- [ ] `SENSITIVE_FIELDS` == the catalog's secret fields; credential never logged; ambient credentials opt-in.
- [ ] Config faults are `DiscoveryConfigurationError`; vendor faults carry `status_code`.
- [ ] Lookback ignored and tested; `AcceptsStopCheck` implemented if paging or per-resource calls.
- [ ] Platform catalog entry: class cloud, query language none, availability preview until a live account was scanned.

## 8. Tests that prove it (`tests/unit/discovery/test_<vendor>_connector.py`)

Registration in `source_connectors()`; `record_for` builds `CloudAgentCreationSource` with instance/scope/resource_id; a resource without region yields `scope` from the documented default; a resource without timestamps is skipped and warned; `check_batch` passes on a yielded batch; lookback is not applied (the fake lister/session receives no time filter); paging follows the cursor and stops on a repeat; stop-before-call sends nothing; 401/403 carry `status_code`; a missing locator is `NOT_CONFIGURED`; malformed 200 is the vendor's error; the credential never appears in `caplog`. Pin captured live bodies inline when sandbox access exists; otherwise build bodies from the vendor's published SDK models and say so in the PR (Vercel did this), and keep availability preview. Trace identity: if the connector sets `service_names` or a trace-joining `resource_id`, a test pins a captured real span's resource attributes and asserts the record's keys equal them (`test_service_names_match_a_captured_<vendor>_span`).

## 9. Proving it end to end

Unit tests prove the connector; only a scan proves the class. When a local discovery stack is available, follow the process skill's local end-to-end recipe: configure the source in the UI, run Test Connection, run a scan, and check the Agents tab shows the records with the cloud mark and the region.
