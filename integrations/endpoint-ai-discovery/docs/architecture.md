# Endpoint discovery: the end-to-end design

How AI tooling on a Mac becomes a finding in Arthur. Three repos, one direction of travel, and
one rule that decides most of the design: **the endpoint enumerates, the collector classifies.**

## Ownership

| | Repo | Holds | Must not hold |
|---|---|---|---|
| Queries and signatures | [`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery) (public, MIT) | the SQL, the runner, the guard, the wall-clock bound, **and the catalog** | any Jamf or Arthur specific deployment glue |
| Deployable | `integrations/endpoint-ai-discovery/` (this tree) | the `arthur1.` wire format, the size budget, the deployable artifact, the Jamf transport | a copy of the queries, **the catalog**, or the matching |
| Collector | `ml-engine/src/ml_engine/discovery/` | **matching**, summaries, the record sink, **and the catalog it matches against** | a copy of the queries |
| Policies | arthur-platform | what to do about a finding | collection concerns |

Framing is this tree's, not upstream's: the wire format is Arthur's and the size budget a
property of the reporting channel, and neither is a fact about osquery. `tools/build-collector.py` now owns the framing, and
`lint.sh` fails if `dist/collect.sh` passes `bin/discover` a flag the vendored runner no longer
accepts, which is how that removal was caught rather than shipped.

**Matching happens in exactly one place: the collector. The endpoint holds no catalog at all.**
Everything below follows from that. It is why the endpoint enumerates, why there is no summary
Extension Attribute, and why a new signature can be added without re-scanning a single Mac.

The catalog the collector matches against is **authoritative in the public repo** and vendored
here alongside the queries. One file, one place to add a signature, and a public one — a
catalog of published product identifiers is osquery material in the same sense the queries are,
and `bin/classify` there is the reference implementation of what a signature means. What must
never exist is a *second* catalog: two would drift on signatures, which is the failure
enumeration was adopted to prevent.

**The catalog is agents only, and that narrowed upstream.** Model runners (`ollama`,
`lm-studio`, `jan`, `llama-cpp`), the MCP SDK, LiteLLM and Docker Desktop were all removed: a
runner *serves* a model, an SDK is what an agent is *built with*, a gateway is what one *calls
through*, and a container runtime is *how we look* rather than what we look for. None acts on a
user's behalf, so counting them as agents overstates the finding. Two consequences reach this
repo: the `model` query branch went with them, and whether Docker is present is now answered by
the `scan` row's `ok` / `absent` / `unhealthy:<code>` / `timeout:<n>`, which a bundle id could
never distinguish. `catalog/agents.yaml` carries the removals as data, with the reason for each.

**Upstream ships Linux; this deployable does not.** From v0.3.0 there is no single composed
artifact — `dist/discovery-darwin.sql` and `dist/discovery-linux.sql` name disjoint sets of
tables, and `bin/discover` chooses by `uname -s`. What this tree builds is a macOS collector: a
LaunchDaemon, Jamf Extension Attributes, `/var/lib/arthur`. So `dist/collect.sh` embeds the
darwin artifact alone and refuses to run anywhere else, by name rather than by failing on a
missing path. Embedding the Linux half as well would cost little and claim a platform nothing
here schedules, deploys or tests. If Arthur ever inventories Linux endpoints, the artifact
already exists upstream and the work is here: a second payload, a second plist, a transport
that is not Jamf.

The `ports` route is retired too, and the reasoning is worth keeping: `bin/classify` refuses a
port unless the process holding it already names the agent, so the port never fires until
something else has identified it — no identifying power, a second opinion from the same witness.
A listening port says an agent is *running* rather than installed, which is liveness, not
identity.

## End-to-end flow

Boundaries are where things **run**, not who owns the code — ownership is the table above.
Each arrow is labelled with what crosses it: the platform never sees a raw row, and **no Mac
ever talks to the collector.**

```
                        ┌──────────────────────────────────────────────────┐
     build time         │ osquery-ai-discovery                      public │
                        │   queries/*.sql ──► tools/build.py ──► dist/     │
                        │   catalog/agents.yaml    the signatures          │
                        └────────────────────────┬─────────────────────────┘
                                                 │ vendored at a pinned tag:
                                                 │ dist/ to the Mac below,
                                                 │ catalog/ to the collector
                                                 ▼
  ┌───────────────────────────── the Mac ──────────────────────────────────┐
  │  vendor/osquery-ai-discovery/dist/                                     │
  │    discovery-darwin.sql · discovery-deep.sql                           │
  │  plus the collector script this tree builds around them, which frames  │
  │  the value: bin/discover writes the JSON, collect.sh writes the ea     │
  │                        │ scheduled run: one process per branch,        │
  │                        │ guarded and wall-clock bounded                │
  │                        ▼                                               │
  │  /var/lib/arthur/   inventory.ea   evidence, ~21 KB framed here        │
  │                     status.txt     collection health, 154 bytes        │
  └────────────────────────────────┬───────────────────────────────────────┘
                                   │ two Extension Attributes,
                                   │ collected by `jamf recon`
                                   ▼
  ┌──────────────────────────── Jamf Pro ──────────────────────────────────┐
  │  the inventory record for this Mac                                     │
  │    Arthur AI Inventory          the evidence                           │
  │    Arthur AI Inventory Status   the health line                        │
  │    serial · hostname · OS · general.reportDate  ◄── Jamf knows these   │
  └────────────────────────────────┬───────────────────────────────────────┘
                                   │ THE COLLECTOR REACHES OUT, on a schedule
                                   │ GET /api/v1/computers-inventory
                                   │   ?section=EXTENSION_ATTRIBUTES,GENERAL
                                   │   filtered on general.reportDate
                                   ▼
  ┌──── collector ─────────────────────────────────────────────────────────┐
  │  ml-engine/src/ml_engine/discovery/                                    │
  │  • matching, against vendor/…/catalog/agents.yaml at the same tag      │
  │  • THE ONLY PLACE MATCHING HAPPENS. No Mac holds a catalog             │
  │  • matching · summaries                                                │
  │  • NO INBOUND PATH AT ALL. Outbound HTTPS to Jamf, one credential      │
  └────────────────────────────────┬───────────────────────────────────────┘
                                   │ FINDINGS, not evidence. The platform
                                   │ never receives a raw row.
                                   ▼
  ┌──── arthur-platform ───────────────────────────────────────────────────┐
  │  • policies, and what to do about a finding                            │
  │  • holds no collection concerns: no queries, no catalog, no transport  │
  └────────────────────────────────────────────────────────────────────────┘
```

Jamf is in the evidence path, not beside it. That is the whole point: the Mac already talks to
Jamf and to nothing else, so the fleet needs no new route, no new firewall rule and no
device-held credential.

**Nothing connects *to* the collector.** Not a Mac, not Jamf — the collector polls. It needs
outbound HTTPS to the Jamf Pro API and nothing listening, which is one fewer assumption than
even a webhook would require.

## Contracts

### The row

Six columns, in this order, from every branch:

```
kind, id, ver, loc, extra, perms
```

`kind` is one of `app`, `npm`, `brew`, `daemon`, `port`, `ext`, `nmh`, `file`, `image`,
`container`, `ilabel` — plus `scan`, below. `container` and `ilabel` arrived with v0.4.0; what
they claim, and how strongly, is upstream's `docs/containers.md`. What matters here is that they
reach the deployed payload — `discover --write` runs every branch, so they appear without
`--deep` — and so count against the size budget below.

`model` was a tenth and is gone: upstream dropped the model runners from the catalog, and
the manifest-glob branch that fed it went with them. A branch's first `UNION ALL` arm must alias all six by name: a
UNION takes its column names from the first arm alone, and an unaliased one silently inherits
whatever precedes it. That shipped once — the pack's `browser` query returned 74
correctly-counted rows keyed `'ext'` and `permissions || CASE WHEN manifest_json LIKE …`,
readable by nothing.

### The scan row

Every payload carries one per branch, dated:

```json
{"kind":"scan","id":"containers","ver":"1788199567","loc":"/var/run/docker.sock","extra":"ok"}
```

`ver` is unix seconds — the payload dates itself, because a reader that can only `cat` a file
cannot check its mtime, and a config-management tool that redeploys the file resets the mtime
without changing the truth. `extra` is a closed vocabulary:

| `extra` | means |
|---|---|
| `ok` | the branch ran; its rows in this payload are real |
| `absent` | the scan found no runtime it can name — no Docker socket, and none of the other runtimes it probes for. A fact about the machine rather than a fault, and the only non-`ok` value that leaves the status line's first token `ok` |
| `unreadable:<runtime>` | a runtime is installed but this scan does not read it — Podman, say. Containers it holds are uncounted, so this is a gap and not an absence |
| `unhealthy:<code>` | the socket answered `<code>`, not 200. `000` is no reply inside the probe budget |
| `timeout:<n>` | answered `/_ping`, then blocked on the query and was killed at `<n>`s |
| `error` | the branch failed outright, typically a table this osquery build lacks |
| `no-cache` | nothing has been written. A deployment fault, not a fact about the Mac |
| `stale=NNh` | **not a scan-row value.** The *status* attribute appends it when the served scan is over a day old — the collector keeps the last good payload when a run fails, so `ok` alone stopped implying recency. Derived by the EA from the timestamp in the value |

This vocabulary is a contract. Smart Groups match on these strings and the collector branches
on them, so it does not grow silently.

**`ok` and `absent` are the two that say nothing is wrong** — one ran and found things, the
other looked and there was nothing to find. The rest are branches that could not look, and
keeping them apart is what makes the first token worth alerting on: a signal that fires on
every Mac without Docker is one a fleet learns to ignore.

`unreadable:<runtime>` exists because `absent` used to cover both cases — a Podman host
reported the state needing action as the state needing none. It is also the bound on what
`absent` claims: the scan names the runtimes it knows, so `absent` means none of those were
found, not that no container can exist on the machine. That is the same bound every branch
has — `apps=ok` reports what matched where it globbed.

### The envelope the collector receives

```json
{"scan": {"serial": "…", "host": "…", "os": "…", "osquery": "…",
          "at": "…", "tool": "…", "containers_scanned": true},
 "findings": [ …rows… ]}
```

Three things the envelope does not carry, and why:

- **`findings` becomes the enumerated rows** — 83 to roughly 759 on a reference Mac. The
  collector filters; the endpoint no longer does.
- **`containers_scanned` is superseded.** A boolean cannot distinguish "no Docker" from
  "Docker wedged", which is precisely the distinction the guard exists to make. The scan rows
  carry it exactly. Derive the boolean from the `containers` scan row during migration, then
  retire it.
- **Identity comes from Jamf, not from the payload.** `serial`, `host` and `os` are already
  in the computer's inventory record, which the collector is reading anyway — that is what
  `section=…,GENERAL` is for. Putting them in the EA value spends payload on data Jamf already
  holds, and invents a second source of truth for a Mac's identity. The endpoint keeps only
  what Jamf cannot know: the rows, the per-branch outcomes, and the osquery version that
  produced them.

### What the collector emits

Findings, never evidence. One record per (device, agent), carrying the identity the
resolver keys on and everything the sensor could see:

```
external_id        f"{device_key}:{agent_id}"
name               the catalog's name for the agent
last_seen          the scan row's `ver` -- when the MAC scanned
creation_source    address + observations, below
```

**Routes collapse into the grain.** One agent commonly arrives through several at once —
Codex CLI as an npm global *and* a CLI shim, Claude Desktop as a bundle id *and* a
native-messaging host — and a per-route key would report one install several times.
Measured on a developer Mac: 10 agents across 20 evidence rows.

`device_key` is the MDM's own id, never the serial: VMs and refurbished units produce
empty or duplicate serials, and an identity that churns mints a duplicate every scan.

**The address names the evidence; `external_id` names the agent.** `external_id` stays
stable when one of an agent's routes is uninstalled; the address is (device, primary
route) because its job is finding the thing again on the machine.

`loc` and `ver` mean different things per kind, and two of those meanings are not what an
observation field names: the `images` route carries a digest in `loc`, not a path, and a
`container` row carries its *state* in `ver`, not a version. Both are mapped per kind.

### Three timestamps, three failure modes

| | source | freezes when |
|---|---|---|
| `last_seen` | the `kind=scan` row's `ver` | the agent is uninstalled — it stops appearing in rows |
| `last_scanned` | the MDM's own per-device report date | the Mac stops checking in |
| *(derived)* | report date recent **and** `ver` old | the scheduled scan died on a live, reporting Mac |

The third is the only fault the collector can report and no Smart Group can see.
First-sighting is absent because no source can report it — it is the earliest `last_seen`
the platform has recorded, and the platform computes it.

## Transport

**Jamf is the first MDM to carry this, not the only one it can.** `dist/collect.sh`
names no vendor: it runs on a schedule, writes three files, and stops. What an MDM has
to provide — a scheduled script, a per-device string attribute large enough for the
payload, an inventory API filterable on a per-device report date, and a stable device id
— is written down in [`mdm/README.md`](mdm/README.md), and the sections below describe
how Jamf satisfies each.


**The collector polls Jamf. Nothing connects to the collector.** Jamf's own documented pattern
for an integration that needs inventory data, and the reason the fleet needs no new
networking.

Two Extension Attributes, both written by the scheduled run and both read by `jamf recon`.
The names below are the reference deployment's; the collector finds the evidence by the
`arthur1.` prefix on its value rather than by name, so a fleet may call them anything:

| EA | Carries | Size |
|---|---|---|
| `Arthur AI Inventory` | the evidence — `arthur1.<base64(gzip(json))>`, or `ERROR:oversize:<bytes>` | ~21 KB, measured |
| `Arthur AI Inventory Status` | collection health, plain text and greppable | 154 bytes, measured |

The health line is the writer's own status output, unchanged:

```
ok 2026-09-18T13:46:38Z rows=804 apps=ok browser=ok containers=ok filesystem=ok homebrew=ok native-messaging=ok packages=ok ports=ok runtime=ok vscode=ok
```

Its only consumer is Jamf itself — a Smart Group finding Macs where collection is broken, so a
Jamf policy can remediate. The collector does not need it: the same per-branch outcomes are
inside the evidence payload.

### How the collector gets it

**It polls. There is no webhook.** One function, two triggers:

```
pull(since)  ── scheduled ──  since = the last successful run
             └─ on demand ──  since = an operator's choice, or one serial
```

`GET /api/v1/computers-inventory?section=EXTENSION_ATTRIBUTES,GENERAL`, filtered on
`general.reportDate` — Jamf's documented parameter for "devices that have submitted inventory
within the last day". The `Read Computers` privilege and nothing else.

**Why not `ComputerInventoryCompleted`.** Jamf documents 24 webhook events and **documents no
delivery semantics for any of them**: no retry policy, no delivery guarantee, no timeout, no
dead-letter, and nothing about whether a webhook is disabled after repeated failures. Checked
in both the admin documentation and the developer documentation. So delivery must be assumed
fire-and-forget — which means a reconciliation pull is required regardless, and once the pull
exists the webhook buys only latency. Latency below a day is not wanted here, and Jamf does
not collect inventory more than daily anyway.

That leaves the webhook as an inbound HTTPS endpoint, its own authentication, its own failure
modes and a permanent "did we miss an event" question, in exchange for nothing. Dropped.

(For the record, in case it is ever wanted: the event carries serial number, device name,
model, OS version and build, user and network details — enough to identify a Mac, never the
inventory record. It is always trigger-then-callback.)

### On demand, and telling two kinds of stale apart

The on-demand trigger exists for one case: somebody looks at Arthur and says the data is old.
It is the same `pull()`, so it costs nothing extra to have.

**It must report Jamf's `general.reportDate` beside the collector's own last-ingest time**, per
Mac, because there are two unrelated causes and only one is the collector's:

| observation | cause | fix |
|---|---|---|
| Jamf's report date is recent, the collector's ingest is older | the collector is behind | the on-demand pull fixes it |
| Jamf's report date is itself nine days old | the Mac has not run `recon` | nothing the collector can do. A Jamf problem |

Without that comparison the on-demand pull becomes a button people press that changes nothing,
and the real fault stays invisible.

### Push was considered and rejected

The retired inline script carried a `--push URL` mode, and it was **never part of this
design.** Its two justifications are both gone: sub-daily latency is not wanted, and a
collector that cannot reach the Jamf Pro API cannot poll either, so it has no fallback role. It
costs a route from every Mac to the collector plus a credential on every Mac.

Recorded as rejected rather than retained as an option, because an option in a design document
is something somebody eventually builds. It went with the script.

### One EA for evidence, not one per query

Rejected deliberately:

- The argument for splitting was per-EA size headroom, and that rests on a cap we invented
  (see Constraints).
- The thing splitting would buy — knowing which branch failed — is already inside the payload
  as one dated `kind=scan` row per branch.
- Splitting adds correlation: several values collected at possibly different times, needing a
  scan id, with a partial-scan failure mode a single payload does not have. Under the pull
  model the collector would have to reassemble them per computer, for nothing.

## Failure semantics

This is the part the project is actually built on. Every defect found in it so far has been
silent: plausible output, wrong values, exit code zero, no error anywhere.

**An empty value is indistinguishable from a clean Mac.** That is the failure everything else
here defends against. So every failure reports a reason, and no path is allowed to return
"nothing" without saying why.

**A bounded query must not trust what it killed.** Measured on osquery 5.23.1 against a daemon
that answers `/_ping` and then stalls: `SIGTERM` stops `osqueryi` in 0.35s and it exits **0**,
having printed `[\n\n]` — a valid, parseable, *empty* JSON array. A wrapper reading the child's
exit code and stdout would report a Mac with no AI tools on it. Output is discarded on the
strength of having fired the kill, and on nothing else.

**A health check is necessary and not sufficient.** Per Docker state, whether each guard admits
the branch:

```
                    absent  refuse  hang   error  wedge   healthy
connect() only      skip    skip    RUN    RUN    RUN     RUN      <- stalls forever
curl -s             skip    skip    skip   RUN    RUN     RUN      <- silent zero rows
HTTP 200 required   skip    skip    skip   skip   RUN     RUN      <- still stalls
200 + wall clock    skip    skip    skip   skip   KILLED  RUN      <- correct
```

`wedge` — 200 on `/_ping`, silence on `/images/json` — is Docker Desktop with a live API and an
engine that is not serving, the ordinary condition of a Mac starting Docker. The window between
probe and query is small and not zero.

**Branches run in their own process on the write path**, and that is a reliability decision
rather than a performance one. Composed into one statement, one unavailable table returns **0
rows and exit 1**, with five bytes of valid empty JSON on stdout — a consumer that ignores exit
status cannot tell that from a clean Mac. Run apart, the same fault costs one branch: 6 of 6
reported, the bad one contributing 0. Every query declares `min-osquery: 5.10.0`, so a missing
table is a real deployment state.

**Freshness is judged from the payload, never from a file.** The scan row's `ver` is the only
timestamp that survives a redeploy.

## Constraints

Each with its status, because two of these were quoted as platform limits for a long time and
are not.

| Constraint | Value | Status |
|---|---|---|
| EA script timeout | — | **No documented Jamf timeout.** Community evidence runs the other way: EAs measured at 21s, and `jamf recon` *stalling* rather than being cut off. An unbounded EA does not fail fast; it hangs that Mac's inventory |
| EA value cap | **≥ 1 MB** | **Measured** 2026-09-05, and it is not the budget below. A 1,048,576-byte value round-tripped script → `jamf recon` → Jamf Pro → API read with an identical sha256 — not truncated, not rejected. Jamf documents no cap and the column is `LONGTEXT`. The ceiling above 1 MB is still unmeasured, and nothing here needs it |
| Our time budget | 10s composed | **Self-imposed**, to keep recon brisk. Enforced by `tools/measure.py --check` |
| Our size budget | 256 KB framed | **Self-imposed**, and **not** a bandwidth decision — fleet cost is payload × fleet (200 MB per sync at 10,000 Macs) whatever this says. It buys margin: `ERROR:oversize:<bytes>` is loud and known, what Jamf does past its own limit is unobserved, and margin keeps the known failure in front of the unknown one. Was 30 KB, which an ordinary Mac reached 68% of. At the measured 25.4 framed bytes/row it fires near 10,300 rows against the ~840 a loaded Mac carries — 13× a real machine, 4× under the measured floor, and a tripwire for a runaway branch |
| Enumerated payload | 804 rows, 126,741 B raw, 20,808 B framed (8% of budget) | **Measured** at vendored ref `v0.4.0`, Apple Silicon, macOS 26.6.2, osquery 5.23.1, Docker up with 20 images. Was 778 rows / 19,288 B framed at `98eaeca`; v0.4.0's `ilabel` arm is the growth |
| Fleet cost through Jamf | 179 MB per full sync at 10,000 Macs | **Measured** (27 MB filtered). Now a cost accepted rather than avoided: it buys 10,000 fewer network paths. The same bytes leave the Mac either way |
| Health line | 154 bytes | **Measured** at ten branches, all `ok`; a degraded line runs longer |
| Jamf inventory cadence | at most once per day per device | **Documented by Jamf.** Caps end-to-end discovery latency at ~24h |
| Jamf API concurrency | 5 concurrent connections | **Documented by Jamf.** No hard rate limit; exceeding it degrades Jamf Pro |
| Incremental pulls | `general.reportDate` filter | **Documented by Jamf** — "devices that have submitted inventory within the last day" |
| Webhook delivery semantics | **undocumented** | Checked both the admin and developer documentation: no retry policy, no delivery guarantee, no timeout, no dead-letter. This is why the design polls |
| Collector ingress | none | Nothing listens. Outbound HTTPS to Jamf — plus Amplitude if the collector is built on the vendored `bin/classify`, which from v0.4.0 sends usage telemetry by default (upstream's `docs/telemetry.md`). **The endpoint stays silent** — `classify` is not in the payload |
| `docker_images` | no timeout of its own | **Measured.** osquery 5.23.1 offers no flag to bound a query: `--docker_socket` is the only docker flag, `--alarm_timeout` is shutdown-only with a 10s floor, `--schedule_timeout` bounds osqueryd's schedule |

Neither self-imposed budget should be restated as a platform limit. The cap in particular was
the entire argument for splitting evidence across many Extension Attributes.

## Decisions

**One reversal, recorded rather than quietly replaced.** Direct push from each Mac was chosen
first, on the strength of keeping the payload out of Jamf's inventory. It was superseded
once the cost was counted properly: push needs a route and a credential on every Mac, and the
same ~21 KB leaves the Mac either way — through Jamf it is `Mac → Jamf 21 KB` plus one
incremental server-to-server read, against push's `Mac → Jamf 154 B` plus `Mac → collector
21 KB`. The bytes are close. The 10,000 network paths and 10,000 credentials are not.

| Decision | Why |
|---|---|
| The endpoint enumerates | A filtered endpoint never sends the evidence, so a new signature cannot re-match against what is already held — which is the property this tree's README already claims |
| Matching happens only in the collector; the endpoint holds no catalog | One place to change, and changing it costs no fleet re-scan |
| The catalog is authoritative in the public repo and vendored into the collector | A catalog of published identifiers is osquery material, and keeping it public means a signature is added once, in the open, next to the queries and the reference matcher. A second private catalog would drift, which is the failure enumeration exists to prevent |
| No summary EA | Computing counts on the endpoint needs a catalog there. Under enumeration the retired summary query goes from 238 chars to **13,522**, with `ids=` naming **564** ids — Adobe, Citrix, stock Apple apps. And the counts stop meaning "AI things": `app=4` becomes `app=398` on the reference Mac. The status line carries collection health instead |
| Jamf carries health only | Policies are managed in arthur-platform, so Jamf needs no findings targeting |
| The collector **polls** Jamf; nothing connects to the collector | The Mac already talks to Jamf and nothing else, so the fleet needs no new route, firewall rule or device-held credential. Polling also means no inbound path to the collector — one fewer assumption than a webhook needs |
| No webhook | Jamf documents no delivery semantics for any of its 24 events — no retry, no guarantee, no timeout, no dead-letter. Delivery must be assumed fire-and-forget, so a reconciliation pull is required anyway; the webhook then buys only latency, which is not wanted |
| Push rejected outright, not retained as an option | Both its justifications are gone: sub-daily latency is not wanted, and a collector that cannot reach the Jamf API cannot poll either. An option in a design document is something somebody eventually builds |
| ~24h discovery latency accepted | Jamf collects inventory at most once per day per device, so this follows from the decision above rather than being chosen separately. AI-tool inventory is not threat detection |
| Identity read from Jamf's record, not the payload | `serial`, `host` and `os` are already in the record the collector fetches. Duplicating them spends payload and invents a second source of truth |
| One EA, not one per query | See Transport. The size argument rests on a cap we invented; attribution already exists in the payload |
| Queries vendored at a pinned tag | Reviewable diffs, works offline, and the version is visible in the tree. A submodule adds clone and CI friction; fetch-at-build needs network in CI |
| The bound lives in the runner, not the SQL | osquery has no per-query timeout, so the only bound is a kill on a process — and a kill is per process, which is why the expensive branch runs in its own |

## Open questions

- ~~**What to pin.**~~ — closed. Upstream cuts releases and this tree pins a tag;
  `vendor/osquery-ai-discovery/VERSION` records which. A bare commit still prints
  `PROVISIONAL`, which is legitimate until a tag carries what you need.
- **Jamf API credential scope and rotation.** One credential with `Read Computers`, held by
  the collector. Where it lives and how it rotates is undecided, and it is now the only
  secret in the data path.

### Answered by polling Jamf

Four questions about this direction, and their answers:

- ~~Whether webhook delivery is reliable enough~~ — **it is undocumented, so the question is
  moot.** The pull is required either way, and the webhook is gone.
- ~~Auth and reachability for the push path~~ — no path from any Mac, and one server-side
  credential instead of 10,000.
- ~~How the collector notices a Mac that stopped reporting~~ — **Jamf is the roster.**
  `general.reportDate` answers it directly, which is stronger than a Smart Group on
  `no-cache`: it distinguishes "reported, and collection is broken" from "has not reported at
  all", and the second is invisible to an Extension Attribute by construction.
- ~~Envelope provenance~~ — `serial`, `host` and `os` come from the computer record the
  collector already fetches.

## One implementation

This tree carries **one** osquery implementation, the vendored one.

| Path | What happened |
|---|---|
| `endpoint/discovery.sql` | **deleted.** Superseded by the vendored `dist/discovery-darwin.sql` (`dist/discovery.sql` until v0.3.0 split it per platform), which enumerates where this one filtered |
| `endpoint/containers.sql` | **deleted.** Superseded by the vendored `dist/discovery-deep.sql`, whose version carries the guard matrix and the wall-clock bound |
| `endpoint/summary.sql` | **deleted.** The status line carries collection health; the collector computes everything else |
| `endpoint/discovery.sh` | **deleted**, rather than reduced to a wrapper. `dist/collect.sh` already runs the vendored runner and writes both attribute values, and a second thing that also framed `arthur1.` would be a second implementation of the one format this tree owns. `--push`, `PUSH_URL` and the envelope builder went with it |
| `test/endpoint/fake_docker.py`, `docker_states.sh` | **deleted.** Upstream's versions are supersets — all six daemon states including `wedge`, the bound's tests, and a whole-suite ceiling this copy never had |
| `test/endpoint/scenarios/*` | **deleted.** Nine of eleven shared a name with the public repo's, which now has thirteen; `30-local-models` covered a kind upstream retired, and `70-docker` is covered by upstream's `docker_states.sh`. They tested the queries, which are no longer this tree's concern |
| `test/endpoint/lint.sh` | **kept, moved to `test/lint.sh` and rewritten** around what this tree owns, plus a new guard: no `.sql` file, no `osqueryi` invocation and no plaintext query outside `vendor/` |
| `README.md`, `CLAUDE.md` | **rewritten.** Both describe an endpoint that enumerates, and name the vendored tree as the only implementation |

**The guard matters more than the deletion.** A second copy does not announce itself — this
one filtered where the deployed artifact enumerated, answered a different question about the
same Mac, and passed every test, because the tests tested the copy. `test/lint.sh` fails if it
comes back.
