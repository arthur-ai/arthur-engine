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

#### `gcp_containers` — Cloud Run and GKE workloads

Lists every Cloud Run service, Cloud Run job and GKE workload in the projects, and
reports a workload when one of its images is an agent's in the catalog (`images:`), or
every workload when `report_all_workloads` is true. Each record names the GCP service
account the workload runs as, so it can be joined with the callers in Vertex AI's audit
log.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `project_ids` | no | yes | Comma-separated project **IDs**, not numbers |
| `regions` | no | no | Comma-separated regions to list Cloud Run jobs in. Empty asks Cloud Run for every region it serves, one call each, which takes most of a scan's time |
| `report_all_workloads` | no | no | `true` to report every workload, not only catalog matches. Defaults to `false` |
| `service_account_key` | yes | no | A service account JSON key. Without one, the engine uses Application Default Credentials only if `ARTHUR_ENGINE_GCP_CONTAINERS_ALLOW_ADC=true` is set |

The service account needs `roles/run.viewer` and `roles/container.viewer`. The second
grants the Kubernetes reads too (`container.deployments.list`, `container.pods.list`,
`container.serviceAccounts.list` and the rest), because GKE authorises a Google identity's
Kubernetes calls against its IAM roles as well as RBAC; it does not grant reading
Secrets. `query` is the catalog, as for Jamf; `query_language: none`.

A GKE workload is its controller -- Deployment, StatefulSet, DaemonSet, CronJob -- or a
Job or Pod nothing owns; `kube-system`, `kube-public`, `kube-node-lease` and the `gke-`
and `gmp-` namespaces are left out. The engine must be able to reach each cluster's
endpoint; a cluster it cannot reach is logged and the rest of the scan goes on, as is a
project where an API is off or refused. Two refusals do end the scan: a credential
refused outright (HTTP 401) stops it at once, and a scan that could list nothing at all
fails with the first refusal's status, so a key with no access reads as denied rather
than as a project without workloads.

The lookback window is not applied: every scan lists every workload.

#### `wiz` — Wiz

Reads two inventories from one Wiz tenant, across every cloud account the tenant has
connected: the cloud resources of the configured Wiz Security Graph entity types
(AI-SPM), and the AI frameworks and SDKs Wiz detected on VMs, container images and
serverless functions (the workload inventory), which is where self-hosted agents show up.

| Field | Secret | Required | Notes |
|---|---|---|---|
| `api_endpoint_url` | no | yes | The tenant's GraphQL endpoint from Wiz's User Settings > Tenant: `https://api.<data center>.app.wiz.io/graphql`, or `.app.wiz.us/graphql` for FedRAMP. Any other host is refused |
| `auth_environment` | no | no | `commercial` (default, `auth.app.wiz.io`), `gov` (`auth.gov.wiz.io`) or `fedramp` (`auth.app.wiz.us`): which token endpoint issues the token |
| `client_id` | no | yes | A Wiz service account's client ID |
| `client_secret` | yes | yes | That service account's client secret |
| `entity_types` | no | no | Comma-separated Wiz Security Graph entity types to list instead of the default `AI_AGENT,AI_SERVICE`, for example `AI_AGENT,AI_SERVICE,MCP_SERVER` |

Use `query: ""` and `query_language: none`. The scan sends nothing but the token request
and two read-only queries, `cloudResourcesV2` and `hostedTechnologies`, each paged 500
at a time. Scopes for the service account:

- AI-SPM inventory (`cloudResourcesV2`): `read:resources`. **Confirmed**: a live run
  read it with a credential holding `read:resources` and neither `read:inventory` nor
  `read:all` (ArcavenAE/stave `1cfb526`, `_kos/findings/finding-010-*.md:39-43`, with
  the credential's scopes in `finding-009-*.md:31-34`).
- Workload inventory (`hostedTechnologies`): `read:resources` and `read:inventory`, or
  `read:all`. **Unconfirmed**: `read:inventory` is a real scope
  (AxtonGrams/terraform-provider-wiz `4fee5a8`, `internal/common.go:87`), but no public
  source ties it to this query.

The unit tests validate both queries and their variables against a pinned public copy of
Wiz's GraphQL schema (ArcavenAE/stave `b893774`, `spec/wiz-schema.graphql`, printed
from live introspection). That checks shape, not live data.

When Wiz refuses a query for a missing scope, its denial lists the scopes that would do
("access denied, at least one of the following is required: [...]", **confirmed** in
ArcavenAE/stave `6728a95`, `finding-009-*.md:29-34`). The engine quotes that list
verbatim, scope names only, in the Test Connection error and the job log, so they say
which scope to add. A tenant that restricts API access to an IP allowlist must allow
the engine's egress address, or every query fails with `FORBIDDEN_IP`.

**Entity types.** `AI_AGENT` and `AI_SERVICE` are Wiz's own `GraphEntityType` names, as
are the other AI types `entity_types` can list: `AI_AGENT_REGISTRY`, `AI_DATASET`,
`AI_DEPLOYMENT`, `AI_EXTENSION`, `AI_GATEWAY`, `AI_GUARDRAIL`, `AI_MODEL`,
`AI_PIPELINE`, `AI_SECURITY_FINDING`, `AI_SKILL`, `AI_SKILL_TEMPLATE`, `AI_TOOL` and
`MCP_SERVER`. Only the two are the default because the others are not agents, and a
record per model, deployment or tool would mint a task for each. If the tenant does not
know a name, Wiz rejects the query and the scan fails as `not_configured` saying to set
`entity_types`.

Each resource is one record, keyed on the cloud provider's own id and never on an id
Wiz assigns itself:

| Wiz has | `external_id` (and the address's `resource_id`) | Example |
|---|---|---|
| `providerUniqueId` | that, verbatim | `arn:aws:bedrock:us-east-1:123456789012:agent/AB12` |
| only `externalId` | `<cloudPlatform>:<account>:<externalId>`, the platform lower-cased | `aws:123456789012:i-0abc123def4567890` |
| neither, or `externalId` with no `cloudPlatform` | skipped, with a job-log warning naming the entity type | |

Why both: `providerUniqueId` is nullable, and a live run had it on 9 of 20
`cloudResourcesV2` records (**confirmed**, ArcavenAE/stave `1cfb526`,
`finding-010-*.md:43`; the schema, `b893774` `spec/wiz-schema.graphql:15772,15797`, has
`externalId: String!` beside `providerUniqueId: String`). Both are the provider's ids
(**strong inference**: demisto/content `f92da85` looks a resource up by an ARN in
`providerUniqueId`, `Packs/Wiz/Integrations/Wiz/Wiz.py:2832` and `README.md:461`, and
maps `externalId` to the "Unique (provider) cloud resource ID",
`Classifiers/classifier-WizDefend_Mapper.json:65-67`). `externalId` can be unique only
inside its account (an instance's short id), hence the qualified form, which keeps
`external_id` unique across every cloud the tenant scans. A resource that later gains a
`providerUniqueId` changes identity once. The `providerUniqueId` form matches what a
native cloud source reports for the same agent. The address's instance is the cloud
account (`cloudAccount.externalId`, lower-cased for Azure, also in the qualified form),
its scope the resource's `region`, else its `regionLocation` (`global` when it has
neither), and `last_seen` is Wiz's `lastSeen`, else the resource's `updatedAt`,
`firstSeen` or `createdAt`; a resource with none, or with no account, is skipped with a
warning. No service names are claimed.

**Workload inventory.** The scan also asks `hostedTechnologies` for the technologies
Wiz files under the `MACHINE_LEARNING_AND_AI` stack layer on `VIRTUAL_MACHINE`,
`CONTAINER_IMAGE` and `SERVERLESS` resources (the same filter as
lindsp77/wiz-health-assessment-skill `e4afe70`, `scripts/generate_deck.py:743-751`).
Running containers are left out: their ids change on every restart, and the image
carries the same technologies. Which technologies count as agent frameworks is decided
by the engine, on `technology.name` only: the hosted technology's own `name` is
`<technology> (<resource name>)` (**confirmed**, `NGINX (docker.io/nginx@dec7a90b)` in
port-labs/ocean `67254a9`, `integrations/wiz/.port/examples/hosted-technology/a.json:3`),
so a resource named `mcp-gateway` never makes NGINX an agent. The rules, in order:

1. A technology Wiz marks `isCloudService` (Azure OpenAI, say) is dropped: managed AI
   services are the AI-SPM inventory's (**confirmed** field,
   `spec/wiz-schema.graphql:88185`; `false` on every technology in Port's examples).
2. Kept when the name, lower-cased with spaces and punctuation removed, contains one of
   `langchain`, `langgraph`, `llamaindex`, `crewai`, `autogen`, `semantickernel`,
   `haystack`, `openaiagents`, `claudeagent`, `agentdevelopmentkit`, `googleadk`,
   `modelcontextprotocol` or `fastmcp`.
3. Kept when `mcp` is one of its words (`MCP Server`, `mcp`; not `mcpx`).
4. Kept when it names a model vendor beside a word that makes it the vendor's library:
   `openai` with `sdk`, `agent(s)`, `python`, `node`, `nodejs` or `library` (`OpenAI
   Python SDK`, `openai-node`); `anthropic` or `claude` with `sdk` or `agent(s)`
   (`Anthropic SDK`, `Claude Agent SDK`). A vendor's name alone (`OpenAI`, `openai`,
   `Anthropic`) is not kept: it names the service (**strong inference**: the same
   health-assessment repo lists `OpenAI` beside `Azure OpenAI` as services a scanner
   covers, `scripts/csv_metrics_processor.py:255-257`).

Everything else in that layer is dropped, PyTorch and TensorFlow included (**strong
inference** that the layer holds them: `csv_metrics_processor.py:38`, "AI libraries &
frameworks (PyTorch, TensorFlow, etc.)"). **Wiz's exact spellings of agent frameworks
are not published**, so each scan logs, once, the ML and AI technology names it saw and
did not keep, each with Wiz's technology id (a numeric string such as `2599`, Port's
example line 5), at most 50 and never a resource name, which shows what the rules miss.
The technology id is not stored on the record: `AgentObservations` has no field for it.

Each (technology, workload) is one record, addressed as a VM's software is on Compute
Engine and EC2: the address's instance is the workload's native id (its `graphEntity`'s
`providerUniqueId`, else `<cloudPlatform>:<account>:<externalId>` from the resource, as
above), its scope `<account>/<region>` (`<account>/global` without a region), its
`resource_kind` `technology` and its `resource_id` the technology name as Wiz spells
it. `external_id` is `<workload native id>:<technology key>`, the key being the name
lower-cased with each run of other characters made one `-`:

| Workload id from | Example `external_id` |
|---|---|
| `graphEntity.providerUniqueId` | `arn:aws:ec2:us-east-1:123456789012:instance/i-0abc:langchain` |
| `resource.externalId` | `aws:123456789012:i-0abc:langchain` |

Nothing Wiz assigns is part of it: a workload with neither id, or no account or
timestamp, is skipped with a job-log warning naming its entity type. `last_seen` is the
hosted technology's `updatedAt`, else its `firstSeen`; the record carries the detected
version and no model or service name.

If Wiz refuses the workload query (`UNAUTHORIZED`) or rejects its shape
(`BAD_USER_INPUT`), the scan still publishes the AI-SPM records, says so in the job log
(quoting the scopes Wiz asked for) and reports the denied scope `workload-inventory`. Any other failure fails the scan as
before, after publishing what was found.

The lookback window is not applied: both queries read an inventory, so every scan
reports every matching resource and technology whatever `lookback_window_seconds` says.
Each inventory is read for at most 100 pages, and the job log says so when one stops
there.

##### Testing against a fake Wiz

`ml-engine/tests/fakes/wiz` is a fake Wiz tenant for development: the token endpoint
and the GraphQL API, with every query executed against the pruned copy of Wiz's schema
the unit tests use, over synthetic data (`tenant.json`: 6 AI-SPM resources and 4
agent frameworks on workloads that become records, plus the cases the connector skips
or drops). It is not in the engine image. CI runs the connector against it in
`tests/unit/discovery/test_wiz_fake_e2e.py`.

1. Start it from `ml-engine/` (`uv sync --group dev` first). `--page-size 3` makes a
   scan page through both inventories:

   ```bash
   uv run python -m tests.fakes.wiz --port 8099 --page-size 3
   ```

2. Point the engine at it. On the engine, and only there, set
   `ARTHUR_ENGINE_WIZ_API_BASE_URL_OVERRIDE=http://127.0.0.1:8099`. Both the token
   request and the queries then go to the fake, and every scan's job log warns that
   the override is set. Only `http(s)://` on `localhost`, `127.0.0.1` or `[::1]` with
   no path is accepted; anything else fails the scan. Unset, nothing changes.
   - An engine run from a checkout reaches the fake on `127.0.0.1` as it is.
   - An engine in Docker (the local stack's data-plane container) does not: set the
     variable on that container (a compose override's `environment:`), recreate it,
     then run the fake inside its network namespace:

     ```bash
     docker run --rm -d --name fake-wiz --network container:<data-plane container> \
       -v "$PWD/ml-engine/tests:/w/tests:ro" -w /w python:3.13-slim \
       sh -c 'pip install -q graphql-core==3.3.0 && python -m tests.fakes.wiz --port 8099 --page-size 3'
     ```

     Recreating the data-plane container again drops that namespace, so restart
     `fake-wiz` after it.

3. In the Platform UI, Governance > Discovery > Sources, add a Wiz source:

   | Field | Value |
   |---|---|
   | `api_endpoint_url` | `https://api.us1.app.wiz.io/graphql` (validated as for Wiz, never contacted while the override is set) |
   | `auth_environment` | `commercial` |
   | `client_id` | `fake-wiz-client-id` |
   | `client_secret` | `fake-wiz-client-secret` |
   | `entity_types` | blank |

   Add a config on the local engine with `query` empty, `query_language: none` and any
   lookback.

4. **Test Connection** succeeds with preview rows. **Scan now**: the Scans tab shows 10
   records, and the Agents tab lists them with the Wiz mark, for example
   `support-triage-agent` and `LangChain on agent-host-1`. The job log lists the
   skipped resource and workload and the unmatched technologies (Anthropic, PyTorch,
   TensorFlow).

5. Flip a fault on the running fake and test again
   (`curl -X POST 'localhost:8099/_control/fault?mode=<mode>'`, `mode=none` to stop):

   | Mode | Expected |
   |---|---|
   | `bad-credentials` | Test Connection fails as Authentication, vendor status 401; a scan fails `authentication_failed` |
   | `missing-scope` | Test Connection succeeds with AI-SPM rows only; the scan publishes 6 records, reports the denied scope `workload-inventory`, and the job log quotes `[read:inventory read:all]` |
   | `forbidden-ip` | Fails as Authorization, status 403, naming the IP allowlist |
   | `rate-limit-once` | One HTTP 429 with `Retry-After`, retried, then success |
   | `rate-limit-in-200` | `RATE_LIMIT_EXCEEDED` inside an HTTP 200, retried, then success |
   | `repeated-cursor` | The AI-SPM listing stops at the repeated cursor with a warning; 5 AI-SPM records |

   `GET /_control/state` lists the requests the fake answered. `--fault <mode>` or
   `FAKE_WIZ_FAULT` starts it with one set.

For a standalone engine, use a `webhook` destination at
`http://127.0.0.1:8099/_sink` with `allow_insecure_http: true`; `GET /_sink` returns
what it was sent. Standalone configs refuse `vendor: wiz` until the engine's
arthur-client includes the `wiz` vendor.

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
| `regions` | no | yes | Comma-separated regions, such as `us-east-1,eu-west-1`, or `all` for every region each account has enabled. The named regions choose the partition, and must share one; `all` is the `aws` partition's, so another partition names its regions |
| `access_key_id` | yes | no | An access key, with `secret_access_key`. Without one, the engine uses its own AWS credentials only if `ARTHUR_ENGINE_AWS_EC2_ALLOW_DEFAULT_CREDENTIALS=true` is set |
| `secret_access_key` | yes | no | Set with `access_key_id`, or neither |
| `role_arn` | no | no | A role those credentials assume, as session `arthur-ai-discovery` |
| `external_id` | no | no | The external ID the role's trust policy requires; with `role_arn`, or with `accounts`, where it is sent when assuming the member role in each account and needs no `role_arn` |
| `accounts` | no | no | `all` for every active account in the organization, or comma-separated 12-digit account IDs. Each is read through its member role; unset, the credential's own account is read directly |
| `member_role_name` | no | no | The role assumed in each account, by name; defaults to `arthur-ai-discovery` |
| `include_tags` | no | no | Comma-separated `key=value` tags to limit the scan to |
| `exclude_tags` | no | no | Comma-separated `key=value` tags to leave out; exclude wins |

The credential needs `ec2:DescribeInstances`, `ssm:DescribeInstanceInformation` and
`ssm:ListInventoryEntries`, plus `ec2:DescribeRegions` with `regions: all`, and nothing
more: AWS's read-only managed policies cover them but also read Parameter Store and
instance user data. With `accounts` set it needs
`organizations:ListAccounts` (for `all`) and `sts:AssumeRole` on the member role instead,
and the member role in each account holds the three actions plus `ec2:DescribeRegions`.
An account whose role cannot be assumed, a named region the account has not enabled, or a
region it is refused, is a denied scope in the scan's outcome and the scan reads the rest;
refused everywhere, the scan fails.
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
