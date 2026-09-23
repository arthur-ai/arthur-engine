# Endpoint AI Discovery

Endpoint AI agent discovery for Arthur.


Arthur governs AI agents, but today it only sees agents it is already instrumented into. The
fastest-growing category of enterprise AI risk is not on a server — it is on employee laptops:
agentic coding tools with shell and filesystem access, fully autonomous local agents, personal
agents bridging chat platforms, and AI browsers and extensions that can read every authenticated
page. (Model runners, MCP libraries and container runtimes are *not* agents and are deliberately
out of scope — see [`docs/architecture.md`](docs/architecture.md).)

None of this is visible to Arthur. Critically, **none of it is visible to Jamf's native inventory
either** — Jamf inventories `.app` bundles, package receipts and plugins, while these tools install
as npm globals, Homebrew casks, browser extensions and JSON config files.

## Approach

Detection runs **on the endpoint**; transport goes through the management plane.

[osquery](https://osquery.io) is the inventory substrate — it has already solved structured OS
enumeration across macOS versions. Arthur owns the semantic layer on top: what a tool can *reach*,
and whether it is something we have never seen before.

The endpoint collects and redacts; **the collector classifies**, and it is the only place matching
happens — no Mac holds a catalog. Keeping matching server-side means a new signature re-matches
against evidence already held, so the day a new agent is catalogued you learn which Macs already
had it, without waiting for a fleet re-scan. That is why the deployed query **enumerates** rather
than filtering to a list of known identifiers.

### One implementation, and it is vendored

The queries, the runner, the Docker health guard and the wall-clock bound live in
[**osquery-ai-discovery**](https://github.com/arthur-ai/osquery-ai-discovery) and are vendored
here at a pinned ref. **This tree writes no osquery.** What it owns is the deployable: the
vendoring, the build, the `arthur1.` wire format and the reporting size budget — Arthur's, not
osquery's.

That boundary was learned rather than designed. This tree carried a second, hand-written
implementation beside the vendored one for a while: three `.sql` files and a runner with its own
guard and its own bound. It **filtered** to a list of known bundle identifiers while the artifact
a fleet actually receives **enumerates**, so the two answered different questions about the same
Mac — and every test passed, because the tests tested the copy. It is gone, and `test/lint.sh`
fails if a `.sql` file, an `osqueryi` call or a plaintext query reappears outside `vendor/`.

## Status

Early. The MVP ships **no Arthur binary**: upstream osquery, one scheduled script, two Jamf
Extension Attributes that only `cat` a file, and the collector. That removes code signing,
notarization and a bespoke PPPC profile from the critical path.


## Try it

On any Mac with [osquery](https://osquery.io/downloads) installed, run the thing that deploys:

```bash
sudo ARTHUR_OUT_DIR=/tmp/arthur dist/collect.sh
```

`dist/collect.sh` **is** the artifact a fleet gets — one self-contained file that carries the
vendored `bin/` and `dist/` inside it as an embedded payload. There is no second implementation
to drift, and running it by hand is running the deliverable. It installs nothing: the payload is
extracted to a private temp directory, run, and deleted.

It writes three files and prints the health line:

```bash
cat /tmp/arthur/status.txt                          # collection health, one line
python3 -m json.tool /tmp/arthur/inventory.json     # the readable payload
head -c 40 /tmp/arthur/inventory.ea                 # arthur1.H4sIAGs1l2oC/…
```

Measured on one reference Mac at vendored ref `v0.4.0`, 2026-09-18, osquery 5.23.1: **804
rows** across ten branches, 126,741 bytes of JSON framed to **20,808 — 8% of the 256 KB
budget.** The vendored runner is ~6.4s of that, timed on its own.

For raw rows with no framing and no output files, the vendored runner is right there:

```bash
vendor/osquery-ai-discovery/bin/discover          # base inventory, one JSON array
vendor/osquery-ai-discovery/bin/discover --deep   # …plus a live container scan
```

Every failure path emits a *reason* — `ERROR:oversize:<bytes>`, or a `kind=scan` row saying
which branch could not look — never an empty value. An absent attribute is indistinguishable
from "this Mac has no AI tools," and that misreads as a clean fleet. A scan that cannot run
keeps the last successful one and fails the *Policy* instead, so evidence is never destroyed
to signal a fault; the status line then carries `stale=NNh`.

## The two Extension Attributes

A Jamf Policy runs `collect.sh` on a schedule; the attributes only read what it wrote. Nothing
on the inventory path can block.

| EA | Reads | Carries | Size |
|---|---|---|---|
| `AI Inventory` | `inventory.ea` | the evidence — `arthur1.<base64(gzip(json))>`, or `ERROR:oversize:<bytes>` | ~21 KB, measured |
| `AI Inventory Status` | `status.txt` | collection health, plain text and greppable | 154 bytes, measured |

The evidence EA is gzipped, and that is not premature: the raw JSON measured **~127 KB** on the
reference Mac. Framed as `arthur1.<base64(gzip(json))>` the same payload is ~21 KB.

But **Jamf Smart Groups cannot match inside a compressed blob**, so the second EA carries the
writer's own status line:

```
degraded 2026-09-18T13:46:38Z rows=804 apps=ok browser=ok containers=unhealthy:000 filesystem=ok homebrew=ok native-messaging=ok packages=ok ports=ok runtime=ok vscode=ok
```

First token is `ok` or `degraded`; then a timestamp, a row count, and one outcome per branch
from the closed vocabulary in [`architecture.md`](docs/architecture.md#the-scan-row).

### Smart Group recipes

Criteria use *AI Inventory Status* → **like**:

| Goal | Match on |
|---|---|
| Macs where collection is broken | `degraded` |
| Macs where the container branch cannot look | `containers=unhealthy` |
| Macs where a branch failed outright | `=error` |
| Macs the payload never reached | `ERROR:` on *AI Inventory* |
| Macs that have never collected | `no-cache` |
| Macs serving a scan over a day old | `stale=` |

**Smart Groups answer "is collection healthy", not "which Macs run OpenClaw".** That is a
deliberate consequence of enumeration, and the trade is worth naming: the status line carries no
bundle identifiers because computing them on the device would need a catalog on the device,
which is the one thing the design forbids. Under enumeration the counts would also stop meaning
"AI things" — `app=4` becomes `app=398` on this Mac. **Agent identity is a collector question**,
and the collector re-matches every new signature against evidence it already holds, without a
fleet re-scan.

**Build groups on positive presence only** (risk R11). A failed or absent scan must never read as
absence — hence `degraded` as a positive match rather than an absence rule.

Deliberately absent from the status line: anything path-shaped. `file` ids are absolute paths
containing usernames, and the Jamf inventory record is readable by every Jamf admin.

## Layout

| Path | Contents |
|---|---|
| `vendor/osquery-ai-discovery/` | the queries, the runner and the catalog, vendored at a pinned ref. **The only osquery implementation. Do not edit** |
| `tools/vendor-queries.sh` | vendor `bin/`, `dist/` and `catalog/` from the public repo at one ref |
| `tools/build-collector.py` | build `dist/collect.sh`, the single file an MDM deploys |
| `dist/collect.sh` | the deployable: the vendored runner and queries, embedded. Generated, and committed on purpose |
| `deploy/` | the LaunchDaemon, for fleets preferring a package to an MDM policy |
| `test/lint.sh` | everything this tree owns. ~1s, no VM — see [test/README.md](test/README.md) |
| `docs/` | design and deployment docs |

The catalog is **not vendored here**: signatures are the collector's, and it vendors them into
`ml-engine/src/ml_engine/discovery/`. `build-collector.py` and `test/lint.sh` both assert the
payload carries none, because a Mac holding the signatures it is meant to enumerate past would
be invisible inside a 21 KB base64 blob.

## Rebuilding

```bash
tools/vendor-queries.sh <ref>     # verifies upstream's own build gate before copying
tools/build-collector.py          # rebuild dist/collect.sh around the new tree
test/lint.sh                      # gates the vendored tree and the built collector
```

**Re-vendoring is not a copy — check what the new tree stopped doing.** Upstream removed
`bin/discover --framed` once, correctly, because `arthur1.` and the size budget are Arthur's;
`dist/collect.sh` called that flag, so the bump would have shipped a collector whose only real
work exits 1 on every Mac. `test/lint.sh` now fails if the collector passes `discover` a flag the
vendored runner does not accept.

## Docs

- [**Endpoint discovery: the end-to-end design**](docs/architecture.md) — how AI tooling on a
  Mac becomes a finding in Arthur: ownership across the three repos, the row and envelope
  contracts, transport, failure semantics, and which constraints are measured versus
  self-imposed. Read this first.
- [**AI Inventory on Jamf Pro**](docs/mdm/jamf-pro.md) — deployment runbook for the
  scheduled-writer pattern: two Extension Attributes, one LaunchDaemon, one script, with a
  verification step and expected output for each.
