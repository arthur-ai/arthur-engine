# CLAUDE.md

Endpoint AI agent discovery for Arthur. osquery finds what is installed on a Mac; a scheduled
script writes a file; two Jamf Extension Attributes read it; a collector classifies.

## The boundary, first

**This tree writes no osquery.** The queries, the runner, the Docker health guard and the
wall-clock bound all live in
[`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery) and are vendored
here at a pinned ref. What this tree owns is the deployable: the vendoring, the build, the
`arthur1.` wire format and the reporting size budget.

A second implementation here would answer a different question about the same Mac than the
shipped one does, and its tests would pass because they test the copy. `test/lint.sh` fails
if a `.sql` file, an `osqueryi` call or a plaintext query appears outside `vendor/`.

So: **a query change is an upstream change.** Open it there, vendor the new ref, rebuild.

**The boundary applies to prose too: do not restate upstream's documentation here.** Upstream
documents its own behaviour — `docs/containers.md`, `queries/COST.md`, `docs/telemetry.md` —
and a copy of it in this tree is a second implementation with the same failure mode as the
deleted `endpoint/`: it drifts silently, and a reader cannot tell which is current. Link to it
instead. Write down only what this tree decides — a number, a budget, a guard — and say what
the decision is, not the upstream reasoning behind the thing being decided about. A vendor bump
should leave this tree's docs mostly untouched; if it does not, they were carrying upstream's.

## Design

[`docs/architecture.md`](docs/architecture.md) is the end-to-end design: the endpoint
enumerates, the collector matches, and the catalog is authoritative in the public repo and
vendored here. It also records which constraints are measured and which are ours — the "10s
Extension Attribute timeout" and the size budget are both self-imposed, and neither is
documented by Jamf.

## Layout

| Path | What it is |
|---|---|
| `vendor/osquery-ai-discovery/` | the queries and the runner, at a pinned ref. **The only osquery implementation. Do not edit** — run `tools/vendor-queries.sh`. |
| `tools/vendor-queries.sh` | vendor `bin/` and `dist/` from the public repo at one ref. Not `catalog/` — that is the collector's. |
| `tools/build-collector.py` | build `dist/collect.sh`, the single file an MDM deploys. Holds the `arthur1.` framing. |
| `dist/collect.sh` | generated, and committed on purpose — a reviewer should see it change. |
| `deploy/` | the LaunchDaemon, for fleets preferring a package to an MDM policy. |
| `test/lint.sh` | static checks on everything this tree owns. ~1s, no VM. |
| `test/run-collector.sh` | runs `dist/collect.sh` and asserts on it. ~15s, needs osquery. |

## Commands

```bash
sudo ARTHUR_OUT_DIR=/tmp/arthur dist/collect.sh   # run what deploys; writes 3 files
vendor/osquery-ai-discovery/bin/discover          # raw rows, no framing, no files
vendor/osquery-ai-discovery/bin/discover --deep   # ...plus a live container scan

tools/vendor-queries.sh <ref>         # vendor the public queries + catalog at a ref
tools/build-collector.py              # build dist/collect.sh around them
tools/build-collector.py --check      # ...and confirm it carries the vendored tree

test/lint.sh                          # static checks, ~1s, no VM
test/run-collector.sh                 # run the deployable and assert on it, ~15s
```

Run both after any vendor bump or template edit. `lint.sh` **reads** the deployable and
`run-collector.sh` **runs** it, which is the difference that matters: every static guard here
passed for as long as the collector's extraction preamble went unexecuted by anything but a
human. Both run in CI, on Ubuntu and on a macOS runner respectively.

**The VM scenario suite is upstream's.** At the vendored ref that is `test/lint.sh`,
`test/docker_states.sh` (all six Docker daemon states, including `wedge`) and thirteen VM
scenarios, run by upstream CI. Do not re-create it here — the copy that lived here is exactly
how the two implementations diverged unnoticed.

`test/run-collector.sh` is not that copy coming back, and the line between them is what each
one asserts about. The scenarios ask *did the query find this software*, which is a question
about the vendored tree; `run-collector.sh` asks *did the collector frame this scan, keep the
last good one, and leave nothing behind*, which is a question about the four things this tree
owns. If an assertion here would still make sense with the queries replaced, it belongs here.
If it names an agent, a table or a row count, it belongs upstream.

## The one thing to understand

**Every defect found in this project has been silent.** Plausible output, wrong values, exit
code zero, no error anywhere. Not one of them announced itself. The list so far — most of these
were found in the queries, which now live upstream, and the lessons are why the boundary above
exists:

| Defect | Symptom |
|---|---|
| `JOIN` instead of `CROSS JOIN` | 0 extensions, no error |
| One `%` in a path glob | Matched Edge, silently missed Chrome |
| `npm_packages` recursion | 883 rows instead of 7 |
| Hardcoded `registry.ollama.ai/library` | Found 1 model of 2, looked healthy |
| Missing trailing slash on a dotdir glob | 0 rows, no error |
| `SUM()` over zero rows | Whole summary line `NULL` — clean Macs reported nothing |
| Stock Apple NMH manifest | Two phantom findings on *every* Mac in the fleet |
| `permissions_json` | Not round-trippable — repeated empty keys |
| Wrong bundle id (`bot.molt.mac`) | Demo punchline matched nothing, anywhere |
| `connect()` probe on a socket | Succeeded in 0.000s, query then stalled indefinitely |
| `curl -s` as a health check | Exits 0 on HTTP 500 — reported "no containers" without looking |
| Empty bash array under `set -u` | bash 3.2 only, so it worked locally and died on every Mac |
| A second implementation beside the vendored one | Filtered where the deployed one enumerates. Every test passed; they tested the copy |
| 1s ping against a cold Docker Desktop | `unhealthy:000` on a healthy daemon holding 13 images. Warm it answers in 0.003s, so checking by hand always looked fine |
| Collector looked the payload up by its Extension Attribute's display name | The deployed fleet had prefixed the name. Every Mac read as never-reported, the scan published nothing and exited 0 — a fleet covered in agents reported as clean |

So: **assert on counts and specific identifiers, never on "did it parse".**

And the corollary the last one added: **a fake built from an API's documentation confirms
only that the code matches somebody's reading of it.** It cannot know what a tenant serves
or what its admins named things. `ml-engine/scripts/jamf_smoke.py` runs the shipped client
against a real tenant, read-only; run it before a tenant's first scan.

## Rules that came from being wrong

- **Never infer a fact you can check.** `homebrew_packages covers formulae only` and
  `bot.molt.mac is the bundle id` were both inferred from adjacent evidence, both wrong, and
  both propagated into docs and commit messages before a real install contradicted them.
- **A Homebrew `zap` stanza is not a source for a bundle id.** It enumerates artifacts to
  clean up *including historical ones*, so it is a superset of current identity.
- **Measure what actually ships.** The old suite measured gzip+base64 bytes while the script
  emitted raw JSON. Neither number was wrong alone; together they hid a 34 KB payload against
  the budget. There is now one artifact — `dist/collect.sh` — and running it by hand is
  running the deliverable.
- **Prefer a loud failure to a partial success.** An oversize payload writes
  `ERROR:oversize:<bytes>` rather than nothing; a branch that could not look writes a dated
  `kind=scan` row saying why. An empty attribute cannot be distinguished from a clean Mac.
- **Loud in the channel that carries health, not the one that carries evidence.** A scan that
  cannot run keeps the last successful payload and fails the *Policy*; it does not erase good
  evidence to signal a problem. On an Ongoing schedule a transient failure is ordinary, and
  reporting a well-equipped Mac as empty is the same wrong answer as reporting an empty one as
  equipped. The kept value dates itself, and the status attribute turns that into `stale=NNh`
  so a Smart Group can see it — otherwise this trade would hide a Mac that broke for good.
- **Don't edit a shell script while it is running.** bash reads scripts by byte offset; an
  edit mid-run corrupts execution in ways that look like unrelated syntax errors.
- **A vendored program's interface is not ours, and a vendor bump can remove it.** Upstream
  deleted `bin/discover --framed` — correctly: `arthur1.` and the size budget are Arthur's, not
  osquery's. `dist/collect.sh` called that flag, so the bump would have shipped a collector whose
  only real work exits 1 on every Mac. The framing lives in `tools/build-collector.py` now, and
  `lint.sh` fails if the collector passes `discover` a flag the vendored runner does not accept.
  Re-vendoring is not a copy; check what the new tree stopped doing.
- **A local copy of an upstream thing will drift, and it will drift silently.** That is the
  whole reason `endpoint/` and the VM suite are gone. If something upstream is wrong, fix it
  upstream and re-vendor.

## Conventions

- `test/lint.sh` enforces what comments cannot: one implementation, a collector that carries
  the vendored tree, no catalog in the payload, every `discover` flag still accepted, the
  framing and its over-cap reason present, and a plist that runs the built collector. Add a
  guard there whenever a class of bug could recur.
- `dist/collect.sh` is generated. Edit the `COLLECTOR` template in `tools/build-collector.py`
  and rebuild; never edit the built file.
- The endpoint enumerates and redacts; the collector classifies (D17). Keep catalog matching
  off the device, and keep anything path-shaped out of the status line — `/Library/Managed
  Preferences` and the Jamf inventory record are readable by every Jamf admin.
- A vendored ref pinned to a bare commit prints `PROVISIONAL`. That is legitimate; pin a tag
  once one carries it.

### Comments state the rule, not the incident

This tree's comments are dense on purpose — a guard nobody understands gets deleted. But
density is not licence to narrate. **Write what a maintainer must not break; do not write
what happened to whoever wrote it.**

| Write this | Not this |
|---|---|
| "Count invocations, not mentions: comments discussing python3 read as a dependency." | "This counted mentions, and three comments kept the guard reporting python3 was required." |
| "The cap is not a platform limit: 1 MB was measured as a floor, never a ceiling." | "The old 30 KB was guarding a limit that does not exist." |
| "Strip comments before checking for the frame; the driver explains it at length." | "Changing it left the guard passing on its own explanation. This repo has made the same mistake three times." |

The test: **delete the sentence and ask whether someone is now more likely to break
something.** If not, it was a war story. The measurement that justifies a number stays — a
cap without its evidence is a magic constant. The anecdote about how the number was once
wrong does not.

Specifically out: dates, "used to", "already once", "this repo has shipped", references to
files or repositories that no longer exist, and cross-references that send a reader to
another document to parse a comment. A reader arriving cold has none of that context and
does not need it.

## Environment

Apple Silicon. Running `dist/collect.sh` needs osquery and nothing else — no VM, and from
vendored ref `v0.5.0` no interpreter either.

**Both halves had to move, and ours was not sufficient alone.** `gzip`/`base64`/`plutil`
replaced this tree's `python3 -c`; upstream then removed its last one, putting the JSON work
into shell helpers and osquery's own `json_valid`/`json_type`. In between, a claim that the
deployable needed only osquery shipped and was false — the check behind it looked at
`dist/collect.sh` and not at the vendored binaries inside it. `test/lint.sh` now derives the
answer from the payload and counts invocations rather than mentions: it read three comments as
a live dependency at the very ref that removed it.

A Tart VM harness lives upstream with the scenarios, at `test/run.sh` in
[`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery).
