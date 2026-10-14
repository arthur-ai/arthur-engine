---
name: discovery-source-siem
description: States the SIEM source-class contract for Shadow Agent Discovery, where a customer-written query over logs in Splunk, Elastic Security, Microsoft Sentinel, Google SecOps or similar returns one row per agent. Use when a vendor is classified `siem`, or when building, reviewing or changing a connector under ml-engine/src/ml_engine/discovery/siem/ or a customer's discovery query. Covers the row and record rules, TLS, lookback, errors, Test Connection, what to copy and the tests that prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# SIEM source class

The gates already refuse the mechanical mistakes: a connector missing from the registry or without `SENSITIVE_FIELDS` (`ml-engine/tests/unit/standalone/test_discovery_config.py`), an executor registry that disagrees with it (`ml-engine/tests/unit/job_executors/test_discover_agents_executor.py`), a record outside the output contract (`ml-engine/src/ml_engine/job_executors/discovery_output_contract.py`), and engine and Platform halves that disagree (the process skill's cross-repo invariant check). This skill is for what they cannot see: whether the connector runs the customer's query faithfully, keeps lookback beside it, trusts the right certificate, and classifies the query's own faults as config.

Read the source of truth rather than a restatement here:

- arthur-common `src/arthur_common/models/agent_governance_schemas.py`: `SIEMAgentCreationSource` and `SourceAddress`.
- `ml-engine/src/ml_engine/discovery/siem/records.py`: `require_contract_columns` and `records_from_rows`, the only way rows become records.
- `ml-engine/src/ml_engine/discovery/siem/tls.py`: the three TLS modes and `tls_session`.
- `ml-engine/src/ml_engine/discovery/__init__.py:source_connectors()`: the registry.
- `ml-engine/src/ml_engine/job_executors/discovery_scan.py`: the scan Protocol, `AcceptsStopCheck`, `DiscoveryConfigurationError` and `failure_code`.
- `ml-engine/src/ml_engine/job_executors/discovery_source_test_executor.py`: how Test Connection classifies an exception (`_status_of`), and its `PREVIEW_DEADLINE_SECONDS`.

Platform and UI steps belong to Arthur's internal discovery integration process skill.

## Reference connectors

- One call returns everything: copy `ml-engine/src/ml_engine/discovery/siem/elastic_security/` (#2405). Read [references/vendors/elastic-security.md](references/vendors/elastic-security.md) when building or changing Elastic.
- Async job with paging: copy `ml-engine/src/ml_engine/discovery/siem/splunk/` (#2404). Read [references/vendors/splunk.md](references/vendors/splunk.md) when building or changing Splunk.

The process skill's client, connector and test templates are rendered from the Elastic shape.

## Workflow

```
- [ ] 1. The vendor is siem
- [ ] 2. Columns checked before records; records only via records_from_rows
- [ ] 3. Connection: https, address_problem, tls_session, query-language guard
- [ ] 4. Lookback beside the query; paging; completeness before the first yield
- [ ] 5. Errors and Test Connection
- [ ] 6. Register, document with a sample query
- [ ] 7. Tests: run, fix, repeat until green
- [ ] 8. A scan end to end
```

## 1. Is it siem

A SIEM source runs **the customer's query** over logs they already ship, inside a lookback window, and turns each row into a record. The query decides what an agent is, so detection is inferred, and the connector's job is to run it faithfully and refuse anything that would change its meaning. Pick `siem` when the vendor's API executes a query over stored events; gateway logs that land in a SIEM are SIEM sources too. A new log shape on an existing SIEM vendor needs no new vendor, catalog entry or connector: ship a sample query, a test that runs it against a captured result, and a docs section.

## 2. Rows and records

- The query projects exactly the `DiscoveryOutputRecord` columns. Any other column fails the contract, including `host_name`, `os_version` and `service_names`, so the class's `OBSERVABLE_FIELDS` ceiling is unreachable today: never promise those fields to a customer.
- Call `require_contract_columns` **before** building any record; build records only with `records_from_rows`. Bad rows are counted and skipped; values are never logged.
- `address.instance`: the SIEM host from the **parsed** URL: lowercase host, port only if not 443, path kept; never the netloc (it would carry `user:pass@`). `address.scope`: `None` unless the customer chose a workspace or index the vendor scopes by. `address.query`: the query text as the connector runs it (after its whitespace trimming, e.g. Elastic's `esql_text`).
- List columns (`llm_models`, `tools`, `sub_agents`, `data_sources`) are lists of objects in the contract, which no text query language returns. `records_from_rows` wraps a string or a multivalue of strings into `{"name": ...}` (`{"url": ...}` for `data_sources`); always test a sample query that returns `llm_models`, or a whole result can silently become zero records.
- When the logs are a gateway's, the query follows the gateway skill's identity rules: an external id namespaced by a fixed gateway label the customer never changes, one record per credential (or agent id), provider-qualified models, and never a request header or key column (gateway logs can carry API keys in clear).

**Trace-identity invariant (every class).** A record becomes a GenAI Engine task; the customer's traces land on it only if the record's join keys (`observations.service_names` against the span's `service.name`, `address.resource_id` against `cloud.resource_id` where set) equal what the vendor's own telemetry puts on a real span. SIEM records carry no service names; keep it so unless a captured span proves a key. A wrong key permanently splits one agent into two tasks.

## 3. Connection and credentials

- Fields: a non-sensitive https URL; one secret; optional `ca_certificate` and `tls_verification` (`full|ca_only|off`, default `full`). In the catalog, mark the URL must-be-https and the vendor as one where `ca_only` requires a CA certificate. `SENSITIVE_FIELDS` equals the catalog's secret fields.
- `https://` only, then `discovery/address.py:address_problem`; TLS through `tls_session`, with `normalize_pem` for pasted certificates; `allow_redirects=False` on **every** call that carries the credential; `(connect, read)` timeouts summing under 120 s.
- Least privilege: a read-only search role scoped to the indexes the query needs; name it in the docs.
- Refuse a config whose query language is not the vendor's, and refuse a JSON DSL where the vendor accepts a text language: `DiscoveryConfigurationError`.

## 4. Lookback, paging, caps

- **Lookback goes beside the query, never into it**: the vendor's time parameter or a request filter. `lookback_hours <= 0` means all time. Never rewrite the customer's query, except a prefix the vendor documents as required.
- Report completeness (row cap hit, partial results, zero rows) on the job logger **before the first yield**; a capped result logs a warning.
- Implement `AcceptsStopCheck.stop_when` when you poll or page (structural; do not import it): ask between vendor calls and `return` cleanly.

## 5. Errors and Test Connection

- Config faults (missing field, `http://`, bad URL, bad TLS mode, wrong query language): `DiscoveryConfigurationError`.
- A vendor 400 that is the query's fault is `DiscoveryConfigurationError` raised **outside** the `except` block (no `__cause__` or `__context__`) with no `HTTP nnn` in its text: `_status_of` reads the outermost message.
- Columns that miss or exceed the contract: `OutputContractError` via `require_contract_columns`.
- Non-2xx, or a 200 that is not the vendor's (a proxy login page): `<Vendor>Error(msg, status_code=n)`.
- TLS handshake refused: `DiscoveryConfigurationError(...) from exc`. A CA that will not load: `from None` (`tls_session` does it), since `ssl.SSLError` is an `OSError` and reads as network.
- Unreachable: `raise type(exc)(msg) from exc`, so a connect timeout stays unreachable and a read timeout stays reachable.
- Test Connection shows the column check and preview rows: zero rows with the right columns passes with a warning; wrong columns fail as `output_contract`.
- Error text names the field and the fix, never the value; never log row values.

## 6. Files

`discovery/siem/<vendor>/{__init__,client,connector}.py`, registered in `source_connectors()`; `tests/unit/discovery/test_<vendor>_connector.py`; a section in `ml-engine/docs/standalone-discovery.md` (`query_language: <lang>`, the field table, and a **sample query** projecting exactly the contract columns, which the tests use as the right-columns case). A SIEM vendor is not done until its docs section has a working sample query. A new query language also needs a value in the Platform catalog, the engine's language guard and an `arthur-client` bump (standalone mode validates the language against it). Platform catalog entry: class siem, the vendor's language, availability preview.

## 7. Tests

Run `uv run pytest tests/unit/discovery/test_<vendor>_connector.py` from `ml-engine/`, fix, repeat. `tests/unit/discovery/test_elastic_security_connector.py` is the canon: registration; request shape (query untouched, lookback beside it, auth header, `allow_redirects=False`, timeout sum); rows to records by column name; address; instance normalisation (443, case, path, IPv6); `check_batch` passes; unmapped and missing columns fail `NOT_CONFIGURED`; zero rows with right and wrong columns; batching; completeness warnings before the first batch; stop-before-call sends nothing; config refusals; TLS modes, including through a proxy; 401/403 status and hint; the 400 query-error shape; unreachable keeps its type; secrets never logged; malformed 200; captured live bodies inline.

- Build fixtures in the generated clients' shapes: enum members, not plain strings. `str()` and f-strings of a `(str, Enum)` member give its qualified name on Python 3.11+, so convert with `.value`.
- A test CA must carry keyUsage, or Python 3.13's strict X.509 check rejects it under `full`; use `ca_only` for a self-signed test CA.

## 8. End to end

Follow the process skill's local end-to-end recipe: configure the source with the sample query, Test Connection shows the column check and preview rows, a scan completes, and the Agents tab lists the records with the SIEM mark.
