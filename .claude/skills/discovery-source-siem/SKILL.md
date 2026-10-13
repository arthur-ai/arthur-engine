---
name: discovery-source-siem
description: The SIEM source-class contract for Shadow Agent Discovery (a customer-written query over logs in Splunk, Elastic Security, Microsoft Sentinel, Google SecOps, etc. returns one row per agent). Use once a vendor is classified `siem`, or when reviewing or changing a SIEM connector under ml-engine/src/ml_engine/discovery/siem/ or a customer's discovery query. It says what a SIEM row and record must carry, how to connect over TLS, how lookback and Test Connection behave, what to copy, and which tests prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# SIEM source class

This skill owns what is true of every **SIEM** source in the engine (`ml-engine/`). Platform and UI steps are covered by Arthur's internal discovery integration process skill. It is the best-trodden class: the process skill's connector templates are derived from the Elastic connector, so render those (or copy Elastic directly) rather than writing from scratch.

## 1. What a SIEM source is

A SIEM source runs **the customer's query** (KQL, SPL, ES|QL, ...) over logs the customer already ships, inside a lookback window, and turns each returned row into a record. Arthur does not decide what an agent is here; the query does. So detection is **inferred**, and the connector's job is to run the query faithfully, check the columns, and refuse anything that would silently change its meaning.

Pick `siem` when the vendor's API executes a query over stored events. Gateway or proxy logs that already land in a SIEM are SIEM sources too; a direct gateway API is `discovery-source-gateway`.

## 2. The row and record contract

The query must project exactly the `DiscoveryOutputRecord` columns: required `external_id`, `name`, `last_seen` (non-blank); optional `llm_models`, `tools`, `sub_agents`, `data_sources`, `runs_on`, `platform`. Any other column is **unmapped and fails the contract** (`discovery_output_contract.check_columns`). That includes `host_name`, `os_version` and `service_names`, which is why the SIEM `OBSERVABLE_FIELDS` ceiling is unreachable today: do not promise those fields to a customer.

| Part | Rule | Where it is enforced |
|---|---|---|
| Columns | `require_contract_columns(columns, subject)` **before** building any record; missing or extra columns raise `OutputContractError` (`not_configured` / `output_contract`) | `discovery/siem/records.py` |
| Records | Built only by `records_from_rows(rows, vendor=, instance=, query=, logger=, scope=None)`; bad rows are counted and skipped, values never logged | `discovery/siem/records.py` |
| Creation source | `SIEMAgentCreationSource`: `DETECTION=INFERRED`, `VISIBILITY_CEILING=LIMITED` | arthur-common |
| `address.instance` | The SIEM host from the **parsed** URL: lowercase host, port only if not 443, path kept; never the netloc (it would carry `user:pass@`) | Elastic `_instance` |
| `address.scope` | Optional; pass `None` unless the vendor has a workspace/index notion the customer chose | convention |
| `address.resource_id` | The row's `external_id` | `records_from_rows` |
| `address.query` | The query text exactly as run | `records_from_rows` |
| `runs_on` / `platform` | Only if the query projects them | contract |

## 3. Connection and credentials

- Fields (the Platform catalog entry; model it on Elastic Security's): `<url_field>` non-sensitive https URL; one secret (`api_key` / `auth_token`) sensitive; optional `ca_certificate` (string) and `tls_verification` (enum `full|ca_only|off`, default `full`).
- In the catalog entry, mark `<url_field>` as must-be-https and mark the vendor as one where `ca_only` requires a `ca_certificate`.
- `SENSITIVE_FIELDS: ClassVar[frozenset[str]]` on the connector names the secret keys. Standalone mode refuses a connector without it (`tests/unit/standalone/test_discovery_config.py:test_every_registered_connector_declares_its_secrets`), and its contents must equal the catalog entry's secret fields. Nothing in this repo checks that equality; the process skill's cross-repo invariant check does.
- Engine: `https://` only, then `discovery/address.py:address_problem(url)` (rejects userinfo, never echoes the URL); TLS through `discovery/siem/tls.py` (`parse_tls_verification`, `tls_session`, `normalize_pem`; the UI strips PEM newlines); `allow_redirects=False` on **every** call that carries the credential; `(connect, read)` timeouts like Elastic's `(10.0, 90.0)`, summing under 120 s.
- Least privilege: a read-only search role scoped to the indexes the query needs; name it in the docs section.
- Query language guard: refuse a config whose language is not the vendor's (`DiscoveryConfigurationError`); refuse DSL/JSON where the vendor accepts a text language (Elastic refuses Query DSL).

## 4. Lookback, paging, caps

- **Lookback goes beside the query, never into it.** Splunk `earliest_time=-{h}h`; Elastic a request `filter` on `@timestamp`. `lookback_hours <= 0` means all time. Never rewrite or append to the customer's query text (except the documented `search` prefix Splunk requires).
- One call that returns everything: copy Elastic (no cursor; yield in chunks of 500). Async job / cursor: copy Splunk (create, poll, page by `result_count`, delete the job in `finally`, ask the stop check on every poll, retry only `GET`/`DELETE`).
- Report completeness (row cap hit, partial results, zero rows) on the job logger **before the first yield**. A capped result has no outcome field yet; log a warning.
- Implement `AcceptsStopCheck.stop_when(should_stop)` when you poll or page. It is structural (`job_executors/discovery_scan.py`; do not import the Protocol): the check is handed in before `scan`, you ask it between vendor calls and `return` cleanly. Test Connection's 120 s deadline (`PREVIEW_DEADLINE_SECONDS` in `job_executors/discovery_source_test_executor.py`) relies on it.

## 5. Errors and Test Connection

The shared error model, which both the scan and Test Connection read:

| Situation | Raise | Scan `failure_code` / Test Connection category |
|---|---|---|
| Missing field, `http://` URL, bad URL, bad TLS mode, CA that won't load, wrong query language, vendor 400 that is the query's fault | `DiscoveryConfigurationError` (a `ValueError`) | `not_configured` / `configuration` |
| Output columns miss or exceed the contract | `OutputContractError` (via `require_contract_columns`) | `not_configured` / `output_contract` |
| Vendor answered non-2xx | `<Vendor>Error(msg, status_code=n)` | 401 `authentication_failed` / `authentication`; 403 `permission_denied` / `authorization`; else `provider_error` / `vendor_error` |
| 200 whose body is not the vendor's (proxy login page, HTML) | `<Vendor>Error(..., status_code=200)` | `provider_error` / `vendor_error` |
| TLS handshake refused | `DiscoveryConfigurationError(...) from exc` | `not_configured` / `configuration` |
| Host unreachable or timed out | the same type: `raise type(exc)(msg) from exc` | `provider_error` / `network` or `timeout` |

Error text names the field and the fix, never the value; never log vendor row values (Elastic `_redacted` strips quoted spans from warnings). SIEM-specific:

- A vendor 400 that is the query's fault is `DiscoveryConfigurationError`, raised **outside** the `except` block (no `__cause__`/`__context__`) and with no `HTTP nnn` in its text: Test Connection's `_status_of` reads the outermost message.
- TLS handshake refused is `DiscoveryConfigurationError(...) from exc` (Elastic). Do not copy Splunk's `SplunkError` wrapping of SSL failures; it reports `provider_error` on a scan.
- A CA that will not load is `DiscoveryConfigurationError(...) from None` (`tls_session` does it); never chain it to `ssl.SSLError`, which is an `OSError` and reads as network.
- Unreachable host: re-raise the same type (`raise type(exc)(msg) from exc`) so `ConnectTimeout` stays unreachable and `ReadTimeout` stays reachable.
- Test Connection shows the column check and preview rows: a query that returns zero rows with the right columns is a pass with a warning; wrong columns fail as `output_contract`.

## 6. What to copy and render (arthur-engine `ml-engine/`)

Verified on 2026-10-12 against arthur-engine `dev` `4de52ab4` and arthur-common `main` `600a527f`. Paths drift: if a file named here is missing, find the symbol, then update this line. The process skill's cross-repo invariant check is the guard that the engine and Platform halves agree.

Copy `ml-engine/src/ml_engine/discovery/siem/elastic_security/` (#2405; one call returns everything) or `siem/splunk/` (#2404; async job and paging), or render the process skill's client, connector and test templates (Elastic shape). Files touched:

- `discovery/siem/<vendor>/{__init__,client,connector}.py`.
- The registry: in `discovery/__init__.py:source_connectors()` import `VENDOR as <X>_VENDOR` and the connector class, add the dict entry, add both names to `__all__`.
- `tests/unit/discovery/test_<vendor>_connector.py`.
- The standalone docs section in `docs/standalone-discovery.md` (`query_language: <lang>`, a sample query, the field table).

A new query language also needs a new query-language value in the Platform catalog, the engine language guard, and an `arthur-client` bump (the Platform's published Python client; standalone mode validates the language against it).

Ship a **sample query** with the docs section that projects exactly the contract columns, and use it in the test as the "right columns" case.

## 7. Checklist

- [ ] Columns checked before records; records only via `records_from_rows`; no row values in logs.
- [ ] Lookback beside the query; `<= 0` is all time; query text untouched.
- [ ] https + `address_problem` + `tls_session`; `allow_redirects=False` everywhere the secret goes.
- [ ] Query 400 → config error with no status/chain/`HTTP`; TLS → config error; unreachable keeps its type.
- [ ] Completeness logged before the first yield; `AcceptsStopCheck` if polling or paging.
- [ ] `SENSITIVE_FIELDS` == the catalog's secret fields.
- [ ] Platform catalog entry: class siem, the vendor's query language, the URL field must be https, `ca_only` requires a CA certificate, availability preview.

## 8. Tests that prove it

The Elastic test file is the canon (`tests/unit/discovery/test_elastic_security_connector.py`): registration; request shape (query untouched, lookback beside it, auth header, `allow_redirects=False`, timeout sum < 120); rows to records by column name; provenance address; instance normalisation (443, case, path, IPv6); `check_batch` passes; unmapped and missing columns fail `NOT_CONFIGURED`; zero rows with right/wrong columns; batching; cap/partial/zero warnings before the first batch; stop-before-call sends nothing; config refusals (missing, http, malformed URL, userinfo, wrong language, bad TLS mode, bad CA); TLS modes incl. through a proxy; 401/403 status and hint; 400 query error shape; unreachable keeps its type; secrets never logged; malformed 200; captured live bodies inline.

## 9. Proving it end to end

Follow the process skill's local end-to-end recipe: configure the source in the UI with the sample query, Test Connection shows the column check and preview rows, a scan completes, and the Agents tab lists the records with the SIEM mark.
