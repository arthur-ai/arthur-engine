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

#### `gcp_compute_engine` — Compute Engine VMs

Reads the agent inventory Arthur's endpoint collector writes to each VM's guest
attributes. Deploying the collector is
[the Compute Engine runbook](../../integrations/endpoint-ai-discovery/docs/mdm/gce.md).

| Field | Secret | Required | Notes |
|---|---|---|---|
| `project_ids` | no | one of three | Comma-separated project **IDs**, not numbers |
| `organization_id` | no | one of three | The organization's number: every active project under it, folders walked |
| `folder_ids` | no | one of three | Comma-separated folder numbers: every active project under each |
| `include_labels` | no | no | Comma-separated `key=value` labels to limit the scan to |
| `exclude_labels` | no | no | Comma-separated `key=value` labels to leave out; exclude wins |
| `service_account_key` | yes | no | A service account JSON key. Without one, the engine uses Application Default Credentials only if `ARTHUR_ENGINE_GCP_COMPUTE_ENGINE_ALLOW_ADC=true` is set |

The service account needs `compute.instances.list`, `compute.instances.getGuestAttributes`
and `compute.projects.get`, all in `roles/compute.viewer`. Under an organization or a
folder it also needs `resourcemanager.projects.list` and `resourcemanager.folders.list`
there (`roles/browser`), with `roles/compute.viewer` granted there rather than per project.
A project it is refused is a denied scope in the scan's outcome and the scan reads the rest;
refused every project, the scan fails. `query` and `query_language` are as for Jamf, and so
is stopping on shutdown.

Compute Engine records no time a guest attribute was written, so every scan lists every
VM in the projects. The lookback is applied to the time on the collector's status line: a
VM with no report inside it is counted, not published, and a window of `0` publishes
every VM's last report. A VM's own metadata wins over its project's, key by key. A VM
whose `enable-guest-attributes` is off, on the VM, or on its project when the VM does not
set it, is counted as `guest-attributes-disabled` and not read. A VM nothing was ever
written for whose `enable-osconfig` is off in the same way is counted as
`osconfig-disabled`: the OS policy that installs the collector can never reach it. Without
`compute.projects.get`, a VM that does not set `enable-osconfig` itself is counted as
`never-reported` instead.

#### `aws_ec2` — EC2 instances

Reads the agent inventory Arthur's endpoint collector writes to each instance's SSM custom
inventory. Deploying the collector is
[the EC2 runbook](../../integrations/endpoint-ai-discovery/docs/mdm/ec2.md).

| Field | Secret | Required | Notes |
|---|---|---|---|
| `regions` | no | yes | Comma-separated regions, such as `us-east-1,eu-west-1`, or `all` for every region each account has enabled (asked in `us-east-1`; another partition names its regions) |
| `access_key_id` | yes | no | An access key, with `secret_access_key`. Without one, the engine uses its own AWS credentials only if `ARTHUR_ENGINE_AWS_EC2_ALLOW_DEFAULT_CREDENTIALS=true` is set |
| `secret_access_key` | yes | no | Set with `access_key_id`, or neither |
| `role_arn` | no | no | A role those credentials assume, as session `arthur-ai-discovery` |
| `external_id` | no | no | The external ID the role's trust policy requires; only with `role_arn`. Also sent when assuming the member role in each account |
| `accounts` | no | no | `all` for every active account in the organization, or comma-separated 12-digit account IDs. Each is read through its member role; unset, the credential's own account is read directly |
| `member_role_name` | no | no | The role assumed in each account, by name; defaults to `arthur-ai-discovery` |
| `include_tags` | no | no | Comma-separated `key=value` tags to limit the scan to |
| `exclude_tags` | no | no | Comma-separated `key=value` tags to leave out; exclude wins |

The credential needs `ec2:DescribeInstances`, `ssm:DescribeInstanceInformation` and
`ssm:ListInventoryEntries`, and nothing more: AWS's read-only managed policies cover them
but also read Parameter Store and instance user data. With `accounts` set it needs
`organizations:ListAccounts` (for `all`) and `sts:AssumeRole` on the member role instead,
and the member role in each account holds the three actions plus `ec2:DescribeRegions`.
An account whose role cannot be assumed, or a region it is refused, is a denied scope in
the scan's outcome and the scan reads the rest; refused everywhere, the scan fails.
`query` and `query_language` are as for Jamf, and so is stopping on shutdown.

EC2 has no per-instance report date to filter on, so every scan lists every instance in
the regions. The lookback is applied to the time on the collector's status line: an
instance with no report inside it is counted, not published, and a window of `0`
publishes every instance's last report. A running instance SSM does not manage is
counted as `not-ssm-managed`, and a Windows instance as `unsupported-platform`.

#### `aws_bedrock` — AWS Bedrock

Lists the account's Bedrock agents and AgentCore agent runtimes, and reads CloudTrail
for the IAM roles that call Bedrock's models.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `regions` | no | yes | Comma-separated regions, such as `us-east-1,us-west-2` |
| `list_agents` | no | no | `true` (default) or `false`: list agents and agent runtimes |
| `read_cloudtrail` | no | no | `true` (default) or `false`: read model callers from CloudTrail |
| `access_key_id` | yes | no | As for `aws_ec2`; without one, the engine uses its own AWS credentials only if `ARTHUR_ENGINE_AWS_BEDROCK_ALLOW_DEFAULT_CREDENTIALS=true` is set |
| `secret_access_key` | yes | no | Set with `access_key_id`, or neither |
| `role_arn` | no | no | A role those credentials assume, as session `arthur-ai-discovery` |
| `external_id` | no | no | The external ID the role's trust policy requires; only with `role_arn` |

The credential needs `bedrock:ListAgents`, `bedrock-agentcore:ListAgentRuntimes` and
`cloudtrail:LookupEvents`. The connector never calls `GetAgentRuntime`, which returns a
runtime's environment variables, or `GetAgent`, which returns its prompt. Use
`query_language: none` and leave `query` empty.

Agents and runtimes are an inventory: the lookback is not applied to them. CloudTrail is
read over the lookback, or the last seven days when it is `0`, for `Converse`,
`ConverseStream`, `InvokeModel` and `InvokeModelWithResponseStream`. Each IAM role (or
IAM user) that called one becomes a record per region, named for the models it called,
with external id `{account}/{region}/iam_role/{role ARN}`. IAM Identity Center (SSO)
roles and the root user are people: their calls are counted in the job log, not
reported. A part AWS refuses in a region, or a region AgentCore does not run in, is a
warning and the rest of the scan goes on; a refused credential, or every part refused,
fails the scan.

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

`llm_models`, `tools` and `sub_agents` may be a string or a multivalue of strings (what
`VALUES()` returns), `data_sources` likewise for URLs; each value becomes one entry.

##### Sample: Kong Gateway logs

Self-hosted Kong Gateway has no usage API. When its `http-log` plugin ships to
Elasticsearch and the `ai-proxy` plugin logs statistics (`logging.log_statistics: true`),
this query lists one agent per Kong consumer and the models it was served:

```esql
FROM kong-ai-logs
| WHERE consumer.id.keyword IS NOT NULL AND ai.proxy.meta.plugin_id.keyword IS NOT NULL
| EVAL model = CASE(
    response.status < 400 AND ai.proxy.meta.response_model.keyword IS NOT NULL,
    CONCAT(ai.proxy.meta.provider_name.keyword, "/", ai.proxy.meta.response_model.keyword),
    NULL)
| STATS last_seen = MAX(@timestamp),
        name = MAX(consumer.username.keyword),
        llm_models = VALUES(model)
    BY consumer_id = consumer.id.keyword
| EVAL external_id = CONCAT("kong:kong:8000:", consumer_id),
       name = COALESCE(name, consumer_id),
       llm_models = MV_SORT(llm_models)
| KEEP external_id, name, last_seen, llm_models
| SORT external_id
| LIMIT 10000
```

- Replace `kong-ai-logs` with your index, and `kong:8000` with your Kong proxy's host
  (port omitted when 443). It namespaces the consumer id, so two gateways never share an
  agent. Never change it once scanned: the `external_id` is the agent's permanent key.
- Rows without a consumer (a refused or missing key) are not agents and are dropped, as is
  traffic on routes without `ai-proxy`. An `ai-proxy` request answered 400 or above
  counts toward `last_seen` but adds no model.
- `LIMIT 10000` is Elasticsearch's default maximum for one query; without it the cluster
  stops at 1,000 rows. More consumers than that need a narrower query.
- The key needs `read` on that index only. The query reads no request headers or bodies.

#### `aws_network` — AWS network logs (read from Amazon CloudWatch Logs)

Reads network logs from CloudWatch Logs log groups and reports each internal source seen
calling a host known to serve model inference (OpenAI, Anthropic, Amazon Bedrock, Azure
OpenAI and AI Foundry, Gemini and Vertex AI, Mistral, Cohere, Groq, OpenRouter, Together,
DeepSeek, xAI, Perplexity, Fireworks), or one of the source's own hosts or ranges. One
record per EC2 instance; else per network interface (default VPC flow logs name one);
else per address in its VPC. A line naming only an address and no VPC is counted in the
log and skipped, since the same address in two VPCs is two hosts.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `region` | no | yes | Region of the log groups, e.g. `us-east-1` |
| `log_group_names` | no | yes | Comma-separated log groups, up to 20; a log group shared into a monitoring account by its ARN |
| `log_format` | no | yes | How lines are read: `route53_resolver_query_log` (Route 53 Resolver query logs, JSON), `vpc_flow_log_v2` (VPC Flow Logs, default version 2 format), or `custom` to use `extraction_regex` |
| `extraction_regex` | no | no | Required for `log_format: custom` and read only then. A regex with named groups: `src` and `dest` (a hostname or IP) required; `instance_id`, `interface_id`, `vpc_id`, `account_id`, `timestamp` (ISO 8601 or epoch) optional. `(?P<name>…)` or `(?<name>…)`; at most 2048 characters |
| `access_key_id` | no | no | IAM access key ID; set with `secret_access_key`, or leave both empty to use the engine's own AWS credentials, which needs `ARTHUR_ENGINE_AWS_NETWORK_ALLOW_DEFAULT_CREDENTIALS=true` on the engine |
| `secret_access_key` | yes | no | The key's secret |
| `role_arn` | no | no | An IAM role to assume with that credential before reading |
| `external_id` | no | no | Sent when assuming `role_arn` |
| `extra_inference_hosts` | no | no | Comma-separated, up to 100: hosts (`*` stands for part of one label; a host also matches its subdomains) or IP addresses and CIDRs, such as an internal LLM gateway |

The credential (or `role_arn`) needs only `logs:FilterLogEvents` on the log groups;
assuming `role_arn` also needs `sts:AssumeRole` on it.

Use `query: ""` and `query_language: none`: the extractor is a field of the source, and a
config's query is ignored. The lookback window is the time range read; `0` reads
everything the log groups retain. A scan reads at most 1,000,000 events; one at that cap
is reported in the log rather than published as complete. Lines are matched in the
engine, each with a 50 ms limit and a 16 KiB length cap, so a regex that backtracks
badly skips lines (counted in the job log) instead of holding the scan.

VPC Flow Logs carry only addresses, and the large providers serve from shared CDN
addresses, so with `vpc_flow_log_v2` only `extra_inference_hosts` ranges match. A source
identified by address is weaker evidence than an instance: Lambda functions, containers
and pods share and reuse VPC addresses.

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

`denied_scopes` lists the parts of an organization-wide scope the scan was refused and
read past, each as `{"scope": "projects/acme-dev-456", "reason": "permission_denied"}`:
a project under a Compute Engine source's organization or folder, an AWS account
(`123456789012`) whose member role could not be assumed, or an account and region
(`123456789012/eu-west-1`). `reason` is `permission_denied` or `unreachable`. A scan
succeeded with denied scopes is a scan that did not see all of its scope, which a
destination should alert on. The list is empty for a source whose scope is one thing,
which fails the scan instead.

A source that reads machines (`jamf_pro`, `gcp_compute_engine`, `aws_ec2`) adds
`device_coverage` to the outcome: how many machines it read, decoded and could not read,
the unreadable ones by reason, and **each unreadable machine by identity**, which is the
finding a destination should alert on, since a machine the scan cannot see is where
unmanaged AI sits:

```json
"device_coverage": {
  "devices_read": 412,
  "devices_decoded": 380,
  "devices_unreadable": 32,
  "unreadable_by_reason": {"never-reported": 30, "osconfig-disabled": 2},
  "unreadable_devices": [
    {
      "device_key": "4823710983451",
      "name": "build-1",
      "location": "acme-prod-123/us-central1-a",
      "reason": "osconfig-disabled",
      "last_reported": null
    }
  ],
  "unreadable_devices_truncated": 0,
  "...": "the scope counts"
}
```

| Field | Meaning |
|---|---|
| `device_key` | The carrier's own stable id: a Jamf management id, a Compute Engine instance id, an EC2 instance id |
| `name` | What the carrier shows for it: the computer name, the VM name, the `Name` tag |
| `location` | Where the carrier addresses it: `project/zone` on Compute Engine, `account/region` on EC2, absent for an MDM |
| `reason` | The reason it was counted under in `unreadable_by_reason` |
| `last_reported` | When the machine last reported, from its status line or the MDM's report date; absent when neither says |

The list holds at most 1,000 machines per scan; `unreadable_devices_truncated` is how
many more were counted and not listed. No attribute value, payload or
credential is ever in it.

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
