# Standalone Agent Discovery

The ML Engine can run as a single-container agent discovery runner: it scans the
discovery sources named in a config file on an interval and sends every agent it finds
to a SIEM or webhook. In this mode it talks to no Arthur Platform and no GenAI Engine.

- [Turning it on](#turning-it-on)
- [The config file](#the-config-file)
  - [Supplying secrets](#supplying-secrets)
  - [Sources](#sources)
  - [Destination](#destination)
- [What the destination receives](#what-the-destination-receives)
- [Running it](#running-it)
- [How scans are scheduled](#how-scans-are-scheduled)

## Turning it on

Set `ML_ENGINE_DISCOVERY_CONFIG` to the config file's path. That is the whole switch:

| `ML_ENGINE_DISCOVERY_CONFIG` | What the engine does |
|---|---|
| unset or empty | Polls the Arthur Platform for jobs, as it always has |
| set, file has `enabled: true` (the default) | Runs standalone discovery from the file |
| set, file has `enabled: false` | Polls the Arthur Platform; the rest of the file is not read |

A file that cannot be used stops the container at startup with a message naming what is
wrong. It never falls back to the Platform, and no error message quotes a value from the
file.

## The config file

```yaml
version: 1
enabled: true

schedule:
  interval: 6h              # 90s, 15m, 6h, 1d, or a number of seconds; at least 1m
  run_on_start: true        # scan once at startup instead of waiting one interval
  max_concurrent_scans: 2   # (source, config) pairs scanned at once
  scan_timeout: 6h          # default 6h, at least 1m; a longer run gives up its slot

sources:
  - name: vertex-prod
    vendor: gcp_vertex
    fields:
      - {key: project_id, value: my-gcp-project}
      - {key: location, value: us-central1}
      - {key: service_account_key, value: {file: secrets/gcp-key.json}}
    configs:
      - name: agent-engines
        query: ""
        query_language: none
        lookback_window_seconds: 86400

destination:
  type: splunk_hec
  url: https://splunk.example.com:8088/services/collector/event
  token: ${SPLUNK_HEC_TOKEN}
  index: ai_inventory

emit_scan_outcomes: true    # also send each scan's outcome to the destination
```

A complete, commented example lives in
[`deployment/docker-compose/ml-engine-standalone-discovery/discovery.example.yaml`](../../deployment/docker-compose/ml-engine-standalone-discovery/discovery.example.yaml).

Unknown keys at the top level, in `schedule` and in `destination` are refused, so a
misspelt key there fails at startup instead of being ignored. Sources use the Platform's
own types, which ignore unknown keys the way the Platform does; a misspelt required key
still fails, because the real one is then missing.

### Supplying secrets

Two ways to keep a value out of the file itself:

- **`${NAME}`** anywhere in a string is replaced with the environment variable `NAME`.
  An unset variable stops startup with its name. Substitution happens after the YAML is
  parsed, so a value full of quotes or newlines (a JSON key) cannot break the file.
- **`{file: path}`** in place of a source field's `value`, a config's `query`, or a
  destination secret reads that file. A relative path is relative to the config file's
  directory. Secrets are trimmed of surrounding whitespace; a query is kept exactly.
  File contents are never `${...}`-substituted.

Files are read as UTF-8. A destination secret that is empty after trimming is refused at
startup — including one from a variable that is set but blank, as Docker Compose sets a
variable an env file lists with no value.

Source fields hold credentials in plain strings, so make the config file and anything it
reads readable only by the engine. The image runs as UID `65532`.

### Sources

A source is written in the same shape the Arthur Platform uses for one: a
`PostDiscoverySource` (`name`, `vendor`, and `fields` as key/value pairs) with a list of
`configs`, each a `DiscoverySourceConfigSpec` (`name`, `query`, `query_language`,
`lookback_window_seconds`). A config takes its source's vendor and ID; setting either on
a config is refused.

Each (source, config) pair is one scan. Source names must be unique, and so must config
names within a source. The engine checks the vendor has a connector and which of its
fields are secret; everything else about the fields is checked by the connector, and a
problem there fails the first scan with the reason in its outcome.

`lookback_window_seconds` is rounded up to whole hours. For a source that reads a window
of activity, nothing is kept between scans, so a window shorter than the interval misses
whatever happens in the gap; the engine warns at startup when one is. A window of `0` asks
a connector that supports it to enumerate everything. A source that lists an inventory
instead, like `gcp_vertex`, does not apply the window at all.

#### `gcp_vertex` — Vertex AI Agent Engine

Lists the Agent Engines in one project and region.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `project_id` | no | yes | The project **ID**, not its number |
| `location` | no | no | Region; defaults to `us-central1` |
| `service_account_key` | yes | no | A service account JSON key. Without one, the engine uses Application Default Credentials only if `ARTHUR_ENGINE_GCP_VERTEX_ALLOW_ADC=true` is set |

The service account needs permission to list Agent Engines
(`aiplatform.reasoningEngines.list`, e.g. `roles/aiplatform.viewer`). Use
`query: ""` and `query_language: none`.

The lookback window is not applied: Google's list API is an inventory, so every scan
reports every engine in the region whatever `lookback_window_seconds` says, and a short
window misses nothing.

#### `jamf_pro` — Jamf Pro (managed Macs)

Reads the agent inventory Arthur's endpoint collector writes to each Mac.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `base_url` | no | yes | Must be `https://` |
| `client_id` | yes | yes | Jamf API client |
| `client_secret` | yes | yes | Jamf API client |
| `include_groups` | no | no | Comma-separated computer group names to limit the scan to |
| `exclude_groups` | no | no | Comma-separated computer group names to leave out |

`query` is the agent catalog YAML; leave it `""` to use the one the engine ships with.
Use `query_language: none`. Jamf scans stop early on shutdown and report as cancelled.

#### `splunk_enterprise` — Splunk Enterprise

Runs the config's SPL as a search job over the lookback window.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `base_url` | no | yes | The management port, e.g. `https://splunk.example.com:8089`; must be `https://` |
| `auth_token` | yes | yes | A Splunk authentication token |
| `ca_certificate` | no | no | PEM; trusted in addition to the system CAs |
| `tls_verification` | no | no | `full` (default), `ca_only` (issuer only, against `ca_certificate` — for Splunk's default certificate), or `off` |

Use `query_language: spl`. The query names its output columns itself (`table` /
`rename`): every row needs `external_id`, `name` and `last_seen`, and may carry the other
columns of the discovery output contract; a column the contract does not describe fails
the scan as `not_configured`.

#### `elastic_security` — Elastic Security

Runs the config's ES|QL over the lookback window. Query DSL is refused.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `elasticsearch_url` | no | yes | Must be `https://` |
| `api_key` | yes | yes | The key's `encoded` value (base64 of `id:api_key`) |
| `ca_certificate` | no | no | As for Splunk |
| `tls_verification` | no | no | As for Splunk; `ca_only` suits Elasticsearch's auto-generated certificate |

Use `query_language: esql`, and name the output columns with `STATS ... BY`, `EVAL`,
`RENAME` and `KEEP`, to the same contract as Splunk. `_query` returns one capped answer;
a result that hits the cluster's row cap is reported in the log rather than published as
complete.

### Destination

Exactly one. Every destination has:

| Key | Default | |
|---|---|---|
| `url` | | Must be `https://` unless `allow_insecure_http: true` |
| `tls_verification` | `full` | `full`, `ca_only` or `off`, as for a Splunk source; quote `"off"` or YAML reads it as false |
| `ca_certificate` | | PEM, inline or `{file: path}`; required by `ca_only` |
| `allow_insecure_http` | `false` | The destination's credentials travel with every request |
| `batch_size` | `100` | Events per request |
| `timeout_seconds` | `30` | Per request |

A request that fails with 429, a 5xx, or a connection error is retried up to three
times, honouring `Retry-After` up to 30 seconds. Any other answer that is not a 2xx
fails the batch at once, as does a certificate the engine does not trust.

Splunk's default HEC certificate (`SplunkServerDefaultCert`) names no host, so `full`
refuses it even with its CA. Use `tls_verification: ca_only` with `ca_certificate` set
to the CA that signed it (`$SPLUNK_HOME/etc/auth/cacert.pem` for the default one) rather
than turning verification off. `off` is logged as a warning at startup.

Redirects are not followed: following one would re-send the events and the
destination's headers to an address nobody configured. A 3xx fails the batch with its
status — point `url` at the address it redirects to.

#### `splunk_hec` — Splunk HTTP Event Collector

| Key | Default | |
|---|---|---|
| `token` | | HEC token (secret) |
| `index` | the token's default | |
| `source` | `arthur-ml-engine` | |
| `sourcetype` | `arthur:discovered_agent` | |

Point `url` at the `/services/collector/event` endpoint. Each event's HEC `time` is when
it was observed. Indexer acknowledgement is not used: a 200 means HEC accepted the batch.

#### `webhook` — any HTTPS endpoint

| Key | Default | |
|---|---|---|
| `headers` | `{}` | Sent with every request; values are treated as secrets |

Each request is a `POST` of a JSON array of events.

## What the destination receives

Every event says what it is and where it came from. `schema_version` changes only when a
field changes meaning or goes away.

A discovered agent, one per agent per scan:

```json
{
  "event_type": "arthur.discovery.agent",
  "schema_version": 1,
  "observed_at": "2026-10-07T18:00:00.123456+00:00",
  "source": {
    "id": "6b0f…",
    "name": "vertex-prod",
    "vendor": "gcp_vertex",
    "config_name": "agent-engines"
  },
  "agent": {
    "external_id": "projects/123456789012/locations/us-central1/reasoningEngines/111…",
    "name": "personal-assistant",
    "last_seen": "2026-10-07T17:58:12+00:00",
    "...": "everything else the source reported; fields it cannot see are left out"
  }
}
```

A scan's outcome, one per scan when `emit_scan_outcomes` is on, so a source that stops
working is visible where its agents are:

```json
{
  "event_type": "arthur.discovery.scan_outcome",
  "schema_version": 1,
  "observed_at": "2026-10-07T18:00:04.5+00:00",
  "source": {"id": "6b0f…", "name": "vertex-prod", "vendor": "gcp_vertex", "config_name": "agent-engines"},
  "outcome": {
    "succeeded": true,
    "records_published": 12,
    "batches_published": 1,
    "error": null,
    "error_code": null,
    "started_at": "…",
    "finished_at": "…",
    "...": "the same payload the engine logs for the scan"
  }
}
```

`error_code` is one of `invalid_job`, `unsupported_vendor`, `not_configured`,
`credentials_unavailable`, `authentication_failed`, `permission_denied`,
`provider_error`, `publication_failed`, `cancelled` or `internal_error`. Errors never
carry the source's credentials or the destination's secrets.

The same agents arrive on every scan: each scan sends what the source reports now, and
the destination dedupes on `agent.external_id` and `source.id` if it needs to.

## Running it

With Docker Compose, see
[`deployment/docker-compose/ml-engine-standalone-discovery`](../../deployment/docker-compose/ml-engine-standalone-discovery/README.md).

With Docker directly, mount the config and its secrets and point the engine at them:

```bash
docker run --rm \
  -e ML_ENGINE_DISCOVERY_CONFIG=/etc/arthur/discovery.yaml \
  -e SPLUNK_HEC_TOKEN \
  -v "$PWD/discovery.yaml:/etc/arthur/discovery.yaml:ro" \
  -v "$PWD/secrets:/etc/arthur/secrets:ro" \
  --stop-timeout 30 \
  arthurplatform/ml-engine:latest
```

From a checkout, after the developer setup in the [README](../README.md):

```bash
ML_ENGINE_DISCOVERY_CONFIG=./discovery.yaml uv run python src/ml_engine/job_agent.py
```

The health check on port `7492` (`GET /health`) works as it does in Platform mode.

## How scans are scheduled

- Every (source, config) pair runs at startup (or one `interval` in, without
  `run_on_start`), then again one `interval` after each run **started**.
- A run still going when its next one is due is not doubled up; the next starts as soon
  as it ends.
- At most `max_concurrent_scans` run at once; when more are due, the most overdue goes
  first.
- A run still going after `scan_timeout` is told to stop (Jamf, Splunk and Elastic stop
  at their next safe point and report `cancelled`) and stops counting against
  `max_concurrent_scans`, so a source that hangs cannot keep the others from running.
  A run that never reaches a safe point -- a vendor call that hangs -- cannot be killed;
  it is left running, logged, and its pair is not started again until it ends.
- A failed scan does not stop the engine. Its outcome is logged and, with
  `emit_scan_outcomes`, sent to the destination, and the pair runs again next interval.
- Records are sent as the connector produces them, so a scan that fails part-way keeps
  what it already sent.
- On `SIGTERM` or `SIGINT`, no new scans start, running ones are asked to stop (Jamf,
  Splunk and Elastic stop at their next safe point and report `cancelled`; Vertex
  finishes its listing), and the
  engine waits up to 15 seconds before exiting. A scan still running then is abandoned
  without an outcome. Give the container more than that to stop — Docker's default is
  10 seconds, so use `--stop-timeout 30` or `stop_grace_period: 30s`.
