# Endpoint discovery: architecture

This doc covers how AI tooling on a machine becomes a finding in Arthur. One rule decides most
of the design: **the endpoint enumerates, and the collector classifies.**

## Ownership

| | Repo | Holds | Must not hold |
|---|---|---|---|
| Queries and catalog | [`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery) (public, MIT) | the SQL, the runner, the Docker health guard, the wall-clock bound, and the agent catalog | anything specific to Arthur or to a carrier |
| Deployable | `integrations/endpoint-ai-discovery/` (this tree) | the build, the `arthur1.` wire format, the size budget, and the Jamf, Compute Engine and EC2 transports | a copy of the queries, the catalog, or any matching |
| Collector | `ml-engine/src/ml_engine/discovery/` | matching, the catalog it matches against (vendored at the same upstream ref), and the records it emits | a copy of the queries |
| Policies | arthur-platform | what to do about a finding | anything about collection |

**Matching happens in exactly one place: the collector.** The endpoint lists everything and
sends it as evidence, so a newly added signature can re-match evidence Arthur already holds,
without a new scan of any machine.

Upstream's bundler packs one catalog-derived file into every bundle: `dist/signatures.sql`, for
`bin/discover --names`. It rides in the payload unread. `test/lint.sh` fails if the collector
ever passes `--names`. `tools/build-collector.py` admits payload files by name, so no other
catalog-derived file reaches an endpoint unvetted.

The catalog covers agents only. Model runners, the MCP SDK, LLM gateways and container
runtimes do not act on a user's behalf, so they are out of scope. Upstream's
`catalog/agents.yaml` records each exclusion and its reason.

**One driver, two builds.** Upstream's macOS and Linux queries use different tables, so this
tree builds one collector per platform around the same driver:

- `dist/collect.sh` for Macs, run by a Jamf Policy or a LaunchDaemon
- `dist/collect-linux.sh` for Compute Engine and EC2, run by a systemd timer

Each refuses to run on the other platform and names the reason.

## End-to-end flow

```
  osquery-ai-discovery (public)        queries, runner, catalog
          │
          │  vendored at a pinned tag: dist/ into this tree, catalog/ into ml-engine
          ▼
  the machine                          dist/collect.sh or collect-linux.sh, on a schedule
    /var/lib/arthur/inventory.ea       the evidence: arthur1.<base64(gzip(json))>
    /var/lib/arthur/status.txt         collection health, one line
          │
          │  the carrier the machine already reports to:
          │  Jamf Extension Attributes · Compute Engine guest attributes · EC2 SSM custom inventory
          ▼
  the carrier's API                    Jamf Pro API · Compute Engine API · SSM API
          │
          │  the collector polls; nothing connects to it
          ▼
  collector (ml-engine)                decodes, matches, emits one record per (device, agent)
          │
          │  findings only; the platform never receives a raw row
          ▼
  arthur-platform                      policies
```

The machine talks only to the carrier it already reports to. That means no new network route,
no firewall rule and no credential on the device. The collector needs outbound HTTPS to the
carrier's API, and nothing listens for inbound connections.

## Contracts

### The row

Every branch emits rows with the same six columns, in this order:

```
kind, id, ver, loc, extra, perms
```

`kind` says what the row is: `app`, `npm`, `ext`, `image`, and so on. The set of kinds, and what
each one claims, is upstream's. See upstream's
[`docs/agents.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/agents.md)
and [`docs/containers.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/containers.md).
Every kind counts against the size budget, because the deployed run executes every branch.

### The payload

The payload is a bare JSON array of rows, framed as `arthur1.<base64(gzip(json))>`. If the
framed value is larger than the budget, the payload is replaced by `ERROR:oversize:<bytes>`.
Serial, hostname and OS are left out on purpose. The carrier's record already holds them, and
a second copy would be a second source of truth for a device's identity.

### The scan row

Every payload carries one dated scan row per branch:

```json
{"kind":"scan","id":"containers","ver":"1788199567","loc":"/var/run/docker.sock","extra":"ok","perms":""}
```

`ver` is the scan time in unix seconds, so the payload dates itself. A carrier that can only
`cat` a file cannot read the file's mtime, and a redeploy resets the mtime anyway. `extra` is
the branch's outcome, which the status line repeats as `branch=outcome`. That vocabulary is
upstream's
([`deployment.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/deployment.md#statustxt-whose-vocabulary-is-a-contract)).
It is a contract: Smart Groups match on these strings, and the collector branches on them.

The carriers in this tree add tokens to the status line:

- `stale=NNh`: appended by the Jamf status attribute when the scan is more than a day old
- `failed=<UTC>`, `osquery=absent` and `inventory=refused:<code>`: appended by the Compute
  Engine and EC2 reporters about the latest run

### What the collector emits

The collector emits findings, never evidence. It emits one record per (device, agent):

```
external_id        f"{device_key}:{agent_id}"
name               the catalog's name for the agent
last_seen          the scan row's `ver`: when the machine scanned
creation_source    address + observations
```

**Several routes collapse into one record.** One agent often shows up through several routes.
Codex CLI, for example, appears as an npm global *and* a CLI shim. A key per route would report
one install several times. On one developer Mac, 20 evidence rows made 10 agents.

`device_key` is the carrier's own device id, never the serial number. VMs and refurbished units
have empty or duplicate serials, and an id that changes creates a duplicate record on every scan.
`external_id` stays stable when one of an agent's routes is uninstalled. The address is
(device, primary route), because its job is to find the thing on the machine again.

**It also reports the machines it could not read.** Each scan's outcome carries device
coverage: how many machines it read and decoded, the unreadable ones counted by reason, and
each of those listed, up to 1,000 per scan. An entry says which machine it is (device key and
name), where it is, why it could not be read and when it last reported, and nothing else:
never an attribute value, a payload or a credential. The list reaches the job log's
`discovery_scan_outcome` line and a standalone engine's outcome event on every scan. The
Platform's run gets the counts, and gets the list once the engine's `arthur-client` declares
the field; the engine needs no change for that.

`loc` and `ver` mean different things for different kinds, and the collector maps them per
kind. For example, an `image` row carries a digest in `loc`, and a `container` row carries its
state in `ver`.

### Three timestamps

| | Source | Freezes when |
|---|---|---|
| `last_seen` | the scan row's `ver`, or the report time when the payload carries none | the agent is uninstalled and stops appearing in rows |
| report time | Jamf: `general.reportDate`. Compute Engine and EC2: the newest timestamp on the status line, so a later `failed=<UTC>` counts | the machine stops reporting |
| *(derived)* | report time recent, but `ver` old | the scheduled scan keeps failing on a machine that still reports |

The carriers surface the third case on the status line: `stale=NNh` on Jamf, and `failed=<UTC>`
on Compute Engine and EC2. First-sighting is not reported by any source: the platform computes
it as the earliest `last_seen` it has recorded.

On Compute Engine and EC2 the report time is the machine's own clock, and the lookback bounds
it only from below. A machine whose clock runs fast therefore stays inside the lookback that
much longer once it stops reporting. Discovery comes first, so it is still published, and the
scan names it with its skew rather than withholding it; no `last_seen` is later than the scan's
own clock.

## Transport

A carrier must provide four things, listed in [`mdm/README.md`](mdm/README.md):

- a way to run a script on a schedule
- a per-device string attribute
- an inventory API
- a stable device id

The collector names no carrier, so each transport below is the carrier half alone.

### Jamf Pro: Extension Attributes

Two Extension Attributes are read by `jamf recon`:

- **the inventory**: `arthur1.…`, ~24 KB
- **the status line**: ~200 bytes, for Smart Groups

The collector finds the inventory by its `arthur1.` prefix, not by the attribute's name, so a
fleet can name both attributes anything.

The collector polls `GET /api/v1/computers-inventory?section=EXTENSION_ATTRIBUTES,GENERAL`. It
filters and sorts on `general.reportDate`, Jamf's documented way to find devices that submitted
inventory recently. The same pull runs on a schedule (since the last success) and on demand
(since an operator's choice). A source can be limited to computer groups. It resolves the
group names before reading any device, and drops out-of-scope Macs before decoding their
payloads. Each run reports devices read, in scope and excluded as `device_coverage`.

**An on-demand pull must show Jamf's report date beside the collector's own ingest time.** When
someone says the data is old, there are two possible causes, and only one is the collector's:

| Observation | Cause | Fix |
|---|---|---|
| Jamf's report date is recent; the collector's ingest is older | the collector is behind | the on-demand pull |
| Jamf's report date is itself old | the Mac has not run `recon` | a Jamf problem, which the collector cannot fix |

### Compute Engine: guest attributes

A VM writes its own guest attributes through its metadata server, and the Compute Engine API
serves them. As with Jamf, the machine writes where it already can, and the collector reads
with one API call. `deploy/report-guest-attributes.sh` runs the collector and publishes
`arthur/inventory` and `arthur/status`. [`mdm/gce.md`](mdm/gce.md) covers the deployment.

**One key carries the inventory.** A guest attribute holds exactly 262,144 bytes, which is this
tree's budget to the byte, so splitting the payload across keys would gain nothing.

**There is no report date.** Nothing records when a guest attribute was written, and a stopped
VM keeps serving its last values. So freshness comes from the status line's timestamp, and the
collector reads every instance on every scan.

### EC2: SSM custom inventory

An instance's SSM Agent uploads custom inventory from a file the instance writes, and the SSM
API serves it. `deploy/report-ssm-inventory.sh` runs the collector and writes
`Custom:ArthurAIDiscovery`. A drop-in on the same systemd unit runs it in place of the
guest-attribute reporter. The agent uploads with the instance's existing SSM permissions, so no
credential is added. [`mdm/ec2.md`](mdm/ec2.md) covers the deployment.

**The payload travels in parts.** A custom inventory value holds at most 4,096 characters. So
each value is cut into numbered parts, and every part carries the whole value's sha256. The
reader refuses any set of parts that does not rebuild exactly one whole value. A lost part
therefore reads as an instance that cannot be read, never as a shorter payload with fewer
agents in it.

**The reporter cannot see the upload.** A refused or capped upload shows in the agent's log,
not in the values. So the only sign Arthur gets is a status line that stops advancing. As on
Compute Engine, freshness is the status line's timestamp. It is never the inventory's
`CaptureTime`, which advances on every association run whether or not the values changed.

## Failure semantics

**An empty value looks exactly like a clean machine.** Most of the design defends against that.
Every failure reports a reason, and no path may report "nothing" without saying why:

- **A branch that cannot look** writes a dated scan row that says so, such as `unhealthy:000`,
  `timeout:6` or `error`, rather than dropping its rows silently. How upstream bounds and
  guards each branch is its
  [`containers.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/containers.md).
- **An oversize payload** writes `ERROR:oversize:<bytes>`, never a truncated value or nothing.
- **A scan that cannot run** keeps the last good payload and fails the run, so the Jamf Policy
  or the systemd unit reads as failed. Erasing good evidence to signal a fault would report a
  well-equipped machine as empty.
- **The kept payload dates itself.** Each carrier makes its age visible: `stale=NNh` on Jamf,
  `failed=<UTC>` from the Linux reporters. The collector judges freshness from the scan rows'
  `ver`, the only timestamp that survives a redeploy.

## Constraints

| Constraint | Value | Status |
|---|---|---|
| Jamf EA script timeout | none documented | Community reports show EAs running 21s, and `jamf recon` stalling rather than being cut off. An EA without a time limit does not fail fast; it hangs that Mac's inventory |
| Jamf EA value cap | **≥ 1 MB** | **Measured** 2026-09-05: a 1,048,576-byte value round-tripped from script through `jamf recon` and Jamf Pro to an API read, with identical sha256. Jamf documents no cap. Anything above 1 MB is unmeasured |
| Guest attribute value cap | **exactly 262,144 bytes** | **Measured** 2026-10-03 on Debian 12: one byte more is refused with HTTP 400, never truncated |
| Guest attributes over a VM's life | survive reboot and stop/start; served while stopped | **Measured** 2026-10-03, identical sha256. With `enable-guest-attributes=FALSE`, the VM gets HTTP 403 and the API still serves the old values. Suspend and resume are not measured |
| SSM custom inventory value cap | **exactly 4,096 characters** | **Measured** 2026-10-16 on Amazon Linux 2023. The agent refuses 4,097 *silently*: it logs to `/var/log/amazon/ssm/errors.log`, skips the file, and reports the association as `Success` |
| SSM custom inventory per type | no cap at the budget | **Measured** 2026-10-16: AWS's quotas page says 200 KB, yet 262,144 and 614,400 characters each uploaded and read back intact |
| SSM inventory per node per day | **5,000 KB, enforced** | **Measured** 2026-10-16: the upload that crosses it fails with `TotalSizeLimitExceededException`, and the previous values are still served |
| A Linux-only association on Windows | **Skipped**, not failed | **Measured** 2026-10-23, SSM Agent 3.3.5390.0 on Windows Server 2022. State Manager counted the instance `Skipped`, `InvalidPlatform`, under the template's document with its `platformType` precondition and under `AWS-RunShellScript` alike, so it never counts toward `MaxErrors`. Run Command's history lists the same invocation as `Failed` |
| A pin bump through CloudFormation | **runs the install at once** | **Measured** 2026-10-23. `update-stack-set` added document version 2 as the default and updated the association's `baseUrl`. The association ran at once on every instance. No file's sha256 changed, and the timer was not restarted |
| Size budget | 256 KB framed | **Our choice** on Jamf. On Compute Engine it is the platform's own cap, so it must not rise; `test/lint.sh` enforces this. The budget keeps our loud failure (`ERROR:oversize`) ahead of any carrier's unobserved one. At ~26 framed bytes per row it fires near 10,000 rows, about 11× the Mac measured below |
| Jamf inventory cadence | at most once a day per device | **Documented by Jamf.** This limits discovery latency to ~24h |
| Jamf API concurrency | 5 concurrent connections | **Documented by Jamf.** There is no hard rate limit, but exceeding it degrades Jamf Pro |
| Webhook delivery | **undocumented** | Neither Jamf's admin docs nor its developer docs give a retry policy, delivery guarantee, timeout or dead-letter queue |
| Collector ingress | none | Nothing listens. Built on the vendored `bin/classify`, the collector also sends usage telemetry by default (upstream's `docs/telemetry.md`). The endpoint sends nothing |

Measured payloads with osquery 5.23.1, run cold:

| Machine | Vendored ref | Rows | Raw | Framed | Run |
|---|---|---|---|---|---|
| Apple Silicon Mac, macOS 26.6.2, Docker up, unprivileged (2026-10-11) | `v0.12.0` | 929 | 155,562 B | 24,668 B (9%) | ~8s |
| `e2-small` Debian 12 VM, root under systemd (2026-10-12) | `v0.12.2` | 623 | 66,737 B | 9,816 B (3.7%) | ~8s, 1.3s CPU |
| `t3.small` Amazon Linux 2023, root under systemd (2026-10-16) | `v0.12.2` | 809 | 88,050 B | 11,376 B (4.3%) | 6s, 1.4s CPU |
| GitHub `ubuntu-24.04` runner, root, Docker up (2026-10-12) | `v0.12.2` | 1,782 | 193,075 B | 27,400 B (10%) | — |

Through Jamf, a full sync at 10,000 Macs moves about 250 MB: the Mac above's 24,668 bytes
each. That cost is accepted: it saves 10,000 network paths, and the same bytes leave each Mac
whichever way they travel.

## Decisions

| Decision | Why |
|---|---|
| The endpoint enumerates; only the collector matches | A filtering endpoint never sends the evidence, so a new signature could not re-match what Arthur already holds. With one place to match, a catalog change needs no fleet re-scan |
| The catalog lives in the public repo and is vendored into the collector | A catalog of published product identifiers is osquery material, so it belongs with the queries and the reference matcher. A second, private catalog would drift |
| `dist/signatures.sql` rides in the payload, unread | Upstream packs it into every bundle. Leaving it out would mean patching the vendored bundler. The real rule, no matching on the endpoint, stays guarded: the collector never passes `--names` |
| No summary attribute | Counting agents on the endpoint needs a catalog there. Raw counts mean nothing: `app=4` becomes `app=398` once everything is enumerated. The status line carries collection health instead |
| Identity comes from the carrier's record, not the payload | The collector already fetches the record. Duplicating serial, host and OS spends payload and creates a second source of truth |
| One inventory attribute, not one per query | The size argument for splitting rests on a cap we invented. Per-branch outcomes are already in the payload. Splitting would add correlation across values collected at different times |
| The collector polls; nothing connects to it | Each machine already talks to its carrier and to nothing else. So the fleet needs no new route, firewall rule or device-held credential, and the collector needs no inbound path |
| No Jamf webhook | Jamf documents no delivery semantics for any of its webhook events, so a reconciliation pull would be needed anyway. The webhook would then add only latency, which is not wanted |
| No push from each machine | Push needs a route and a credential on every machine, while the bytes are about the same: ~24 KB leaves each Mac through Jamf or directly. A collector that cannot reach the carrier's API could not poll either, so push is no fallback |
| ~24h discovery latency | Jamf collects inventory at most once a day. AI-tool inventory is not threat detection |
| Guest attributes carry Compute Engine; one key holds the inventory | The VM writes through its own metadata server, with no credential, no route and nothing connecting in. The measured cap equals the budget. A GCS write would need a credential and egress on every VM |
| SSM custom inventory carries EC2, in parts that each carry the whole value's sha256 | The agent uploads with the instance's own SSM permissions. The alternatives all fall short: instance tags hold 256 characters and need a credential to write; Parameter Store holds 4–8 KB and needs one too; Run Command output stops at 24,000 characters and needs `ssm:SendCommand` |
| A reporter wraps the collector on Linux, one per cloud | The collector names no carrier. The reporter is the carrier half, as the Extension Attribute is on Jamf, and it can name a failed run because it saw it |
| One unit file for both clouds; a drop-in picks EC2's reporter | The collector, schedule and hardening are the same on both clouds, so a second unit would be a drifting copy. The drop-in clears `ExecStart` before setting it, which `test/lint.sh` checks |
| EC2 deploys from one CloudFormation template, as a stack or an organization StackSet; no Terraform module | A service-managed StackSet reaches every account in an OU, including accounts that join it later. A Terraform AWS provider reaches one account, so a module would cover only the accounts named when it was applied. The template is the only copy of the install script: the runbook renders it, and CI lints it and runs it |
| Queries vendored at a pinned tag | Diffs are reviewable, the build works offline, and the version is visible in the tree. A submodule adds friction to cloning and CI; fetching at build time needs network in CI |

## Open questions

- **Quick Setup and custom inventory.** Quick Setup's host-management inventory association
  takes priority over any other. Whether it gathers custom inventory is undocumented and
  unmeasured. A fleet whose inventory comes from it may need a change before it reports.
- **Jamf API credential storage and rotation.** It is not decided where the collector's Jamf
  credential lives or how it rotates. It is the only secret in the data path.
