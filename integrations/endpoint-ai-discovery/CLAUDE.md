# CLAUDE.md

Endpoint AI agent discovery for Arthur. osquery finds what is installed on a Mac or a Linux VM;
a scheduled script writes a file; Jamf Extension Attributes, a Compute Engine VM's guest
attributes, or an EC2 instance's SSM custom inventory, carry it; a collector classifies.

## The boundary, first

**This tree writes no osquery.** The queries, the runner, the Docker health guard and the
wall-clock bound are the osquery binding of
[`ai-detection-spec`](https://github.com/arthur-ai/ai-detection-spec), vendored here at a
pinned ref. What this tree owns is the deployable: the vendoring, the build, the
`arthur1.` wire format and the reporting size budget.

A second implementation here would answer a different question about the same Mac than the
shipped one does, and its tests would pass because they test the copy. `test/lint.sh` fails
if a `.sql` file, an `osqueryi` call or a plaintext query appears outside `vendor/`.

So: **a query change is an upstream change.** Open it there, vendor the new ref, rebuild.

**The boundary applies to prose too: do not restate upstream's documentation here.** Upstream
documents its own behaviour — `osquery/docs/containers.md`, `osquery/queries/COST.md`,
`docs/telemetry.md` — and a copy of it in this tree is a second implementation with the same
failure mode as the deleted `endpoint/`: it drifts silently, and a reader cannot tell which is
current. Link to it
instead. Write down only what this tree decides — a number, a budget, a guard — and say what
the decision is, not the upstream reasoning behind the thing being decided about. A vendor bump
should leave this tree's docs mostly untouched; if it does not, they were carrying upstream's.

## Design

[`docs/architecture.md`](docs/architecture.md) is the end-to-end design: the endpoint
enumerates, the collector matches, and the catalog is authoritative in the public repo and
vendored into ml-engine, not here. It also records which constraints are measured and which are
ours. The size budget is ours on Jamf and Compute Engine's own cap, and Jamf documents no
Extension Attribute timeout.

## Docs

One fact, one place. Before adding a sentence, find the doc that owns it:

| Doc | Owns |
|---|---|
| `README.md` | what this is, how it works in three steps, the layout, the dev commands |
| `docs/quickstart.md` | the shortest path per carrier. Steps and a verify command only; it links to a runbook section for anything more |
| `docs/mdm/<carrier>.md` | operating one carrier: prerequisites, deploy, verify, read the status, troubleshoot, Arthur's access, rollback |
| `docs/architecture.md` | contracts, transport, failure semantics, **every measurement of the payload and the carriers** (Constraints), and every *why* (Decisions). A test's rough runtime beside its command is a hint, not a measurement |
| `docs/image-discovery.md` | the design for Cloud Run and ECS, not yet built: what each control plane and registry gives, and what to measure before building. Nothing here is a runbook step |
| `test/README.md` | what each guard catches |

Runbooks state what to do, not the history of how a step came to be; a measurement a runbook
needs is quoted once, with its number, and the evidence stays in architecture's Constraints.
Section numbers in `gce.md` and `ec2.md` are cited by ml-engine's log messages and tests —
renumbering them is a code change.

## Layout

| Path | What it is |
|---|---|
| `vendor/ai-detection-spec/` | the queries and the runner, at a pinned ref. **The only osquery implementation. Do not edit** — run `tools/vendor-queries.sh`. |
| `tools/vendor-queries.sh` | vendor upstream's osquery binding — `osquery/bin/`, `osquery/dist/` and the bundler — at one ref. Not `catalog/` or `bin/classify` — those are the collector's. |
| `tools/build-collector.py` | build `dist/collect.sh` and `dist/collect-linux.sh`, one file per platform, around one driver. Holds the `arthur1.` framing. |
| `dist/` | generated, and committed on purpose — a reviewer should see it change. |
| `deploy/` | the LaunchDaemon for Macs; the systemd units and `report-guest-attributes.sh`, the Compute Engine carrier; `report-ssm-inventory.sh` and the `ec2.conf` drop-in that runs it, the EC2 carrier. |
| `deploy/arthur-ai-discovery.os-policy.yaml` | the Compute Engine OS policy, and its only copy: `tools/render-os-policy.sh` renders it for gcloud and `deploy/terraform/` reads it. |
| `deploy/terraform/` | a Terraform module that deploys that policy to a fleet's projects and zones, or through one policy orchestrator. Its tests are `terraform test`, against mocked providers. |
| `tools/render-os-policy.sh` | pin the OS policy to one ref: each file's URL there, and the sha256 of the bytes the ref holds. |
| `deploy/arthur-ai-discovery.cfn.yaml` | the EC2 CloudFormation template, and the only copy of its install script: deployed as a stack per region, or as an organization StackSet. Long-form intrinsics only, so it stays plain YAML. |
| `tools/render-cfn-template.sh` | pin the EC2 template to one ref, as `render-os-policy.sh` pins the OS policy. |
| `test/lint.sh` | static checks on everything this tree owns. ~1s, no VM. |
| `test/run-collector.sh` | runs this platform's collector and asserts on it. ~15s, needs osquery. |
| `test/run-guest-attributes.sh` | runs the reporter against a fake metadata server built from measured answers. ~3s, no osquery. |
| `test/run-ssm-inventory.sh` | runs the EC2 reporter against a fake IMDS built from AWS's documentation, and reassembles the file it writes. ~6s, no osquery. |
| `test/run-systemd.sh` | installs and runs the Linux collector under systemd. CI only — it writes to the machine. |
| `test/run-ec2-install.sh` | runs a rendered template's install script twice under `sh`, against the checkout over `file://`. CI only — it writes to the machine. |

## Commands

```bash
sudo ARTHUR_OUT_DIR=/tmp/arthur dist/collect.sh   # run what deploys; writes 3 files
vendor/ai-detection-spec/bin/discover             # raw rows, no framing, no files
vendor/ai-detection-spec/bin/discover --deep      # ...plus a live container scan

tools/vendor-queries.sh <ref>         # vendor the public queries and runner at a ref
tools/build-collector.py              # build both collectors around them
tools/build-collector.py --check      # ...and confirm it carries the vendored tree

test/lint.sh                          # static checks, ~1s, no VM
test/run-collector.sh                 # run this platform's collector and assert on it, ~15s
test/run-guest-attributes.sh          # what the Compute Engine reporter publishes, ~3s
test/run-ssm-inventory.sh             # what the EC2 reporter writes, ~6s

tools/render-os-policy.sh <ref>       # the Compute Engine OS policy, pinned to a ref
tools/render-cfn-template.sh <ref>    # the EC2 CloudFormation template, pinned to a ref
cd deploy/terraform && terraform init -backend=false && terraform test   # the module, mocked
```

Run both after any vendor bump or template edit. `lint.sh` **reads** the deployable and
`run-collector.sh` **runs** it, which is the difference that matters: every static guard here
passed for as long as the collector's extraction preamble went unexecuted by anything but a
human. CI runs lint and the reporter test on Ubuntu, the Mac collector on a macOS runner, and
the Linux collector plus `run-systemd.sh` and `run-ec2-install.sh` on an Ubuntu runner, where
systemd is PID 1. It runs `cfn-lint` on the EC2 template and the Terraform module's tests too.
It also validates a caller at the lowest Terraform and Google provider the module admits:
anything newer passes every other check and breaks a caller pinned there.

**The VM scenario suite is upstream's.** At the vendored ref that is `osquery/test/lint.sh`,
`osquery/test/docker_states.sh` (every Docker daemon state, including `wedge`) and the VM and
container scenarios under `test/scenarios/`, run by upstream CI. Do not re-create it here —
the copy that lived here is exactly how the two implementations diverged unnoticed.

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
  the vendored tree, no payload file that is not admitted by name, no `--names`, every
  `discover` flag still accepted, the framing and its over-cap reason present, and a plist
  that runs the built collector. Add a guard there whenever a class of bug could recur.
- `dist/collect.sh` is generated. Edit the `COLLECTOR` template in `tools/build-collector.py`
  and rebuild; never edit the built file.
- The endpoint enumerates and redacts; the collector classifies (D17). Keep catalog matching
  off the device, and keep anything path-shaped out of the status line — `/Library/Managed
  Preferences` and the Jamf inventory record are readable by every Jamf admin. The bundle
  carries `dist/signatures.sql` for upstream's `discover --names`; never pass that flag.
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

`test/lint.sh` derives that from the payload, not from `dist/collect.sh`'s own code: it counts
interpreter invocations in the vendored binaries, ignoring comments that mention one.

A Tart VM harness lives upstream with the scenarios, at `test/run.sh` in
[`ai-detection-spec`](https://github.com/arthur-ai/ai-detection-spec).
