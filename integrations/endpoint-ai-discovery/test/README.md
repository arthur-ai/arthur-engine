# Tests

```bash
test/lint.sh            # static checks. ~1s, no VM, no network, no osquery.
test/run-collector.sh   # run dist/collect.sh and assert on it. ~15s, needs osquery.
```

Two gates, and they check different kinds of thing. `lint.sh` **reads** the deployable;
`run-collector.sh` **runs** it. Until the second existed, the only executable code this tree
owns — the extraction preamble inside `dist/collect.sh` — was exercised only when somebody
ran the collector by hand on their own Mac, which is the shape of the `set -u` empty-array
defect in [CLAUDE.md](../CLAUDE.md): bash 3.2 only, fine locally, dead on every Mac.

## What is tested here, and what is not

This tree owns the **deployable**: `tools/vendor-queries.sh` brings the queries and the
runner across at a pinned ref, `tools/build-collector.py` wraps them in `dist/collect.sh`,
and this tree adds the `arthur1.` framing and the size budget — Arthur's wire format and
Arthur's reporting channel, neither of them a fact about osquery.

It does **not** own the queries, the runner, `bin/container-scan`, the Docker health guard
or the wall-clock bound. Those live in
[`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery) and are
vendored here at the ref in `vendor/osquery-ai-discovery/VERSION`. Their tests live there
too, and at the vendored ref that is `test/lint.sh`, `test/docker_states.sh` and thirteen
VM scenarios, run by upstream CI.

**Do not re-create that suite here.** A local copy would test a local query rather than the
artifact a fleet receives, and it would pass while doing so.

## `test/lint.sh`

| Guard | What it catches |
|---|---|
| No `.sql`, no `osqueryi` call, no plaintext query outside `vendor/` | A second discovery implementation reappearing. This is the regression guard for the cleanup described above |
| `build-collector.py --check` | `dist/collect.sh` built before the last `tools/vendor-queries.sh` |
| Payload files admitted by name (`ENDPOINT_FILES` in `tools/build-collector.py`, run through `--check`) | A file upstream adds to its bundle reaching endpoints unvetted, catalog-derived ones above all |
| No `agents.yaml`, no `catalog/` in the built collector | The catalog reaching a Mac. The endpoint enumerates and matches nothing |
| No `--names` in the driver | Matching on the endpoint. The bundle carries `dist/signatures.sql` for it, unread |
| One `ARTHUR_PAYLOAD_EOF` pair | The collector embedding a previous copy of itself |
| Every flag either collector passes to `bin/discover`, in every call, is still accepted | A vendor bump removing a flag. This has happened: upstream deleted `--framed`, correctly, and the collector called it |
| Both builds checked by every collector guard | A guard proving one build and saying nothing about the other's bytes |
| `CAP` at most 262,144 | The budget rising past what a Compute Engine guest attribute accepts, so GCE's 400 would fire before our `ERROR:oversize` |
| The units: a oneshot running the reporter as root; a timer with `OnBootSec` and `OnUnitActiveSec`, wanted by `timers.target` | A VM that never runs the scan, or reports nothing for its first hour |
| The unit, the reporter and the collector agree on one install directory | Every VM failing its first run on a missing path |
| No interpreter in the reporter; upstream still prints `no osqueryi found` | The reporter needing more than the collector does; `osquery=absent` silently never firing after a vendor bump |
| `arthur1.` and `ERROR:oversize` present | The framing or its over-cap reason being dropped, which leaves an empty attribute — indistinguishable from a Mac with no AI tools on it |
| `bash -n` on both collectors, the reporter and `vendor-queries.sh` | A template edit in `build-collector.py` producing a syntax error nobody runs until a Policy does |
| Vendored `VERSION` exists; `PROVISIONAL` is announced | A commit pin becoming permanent by inattention |
| The plist runs `collect.sh` with `RunAtLoad` | A fresh Mac reporting nothing until the first interval elapses |
| `DOCKER_PING_TIMEOUT` ≥ 10 **and** ≥ the vendored default | A cold Docker reported as `unhealthy:000`. The second half catches an upstream bump crossing our value, after which the export would lower the bound instead of raising it |
| No interpreter in the collector's own code | The framing step reaching for `python3` again. `/usr/bin/python3` is a shim that fails without Command Line Tools, silently |
| The payload's real prerequisites match the runbook's table | Docs claiming the endpoint needs less than it does. This shipped once: the collector's own code was interpreter-free while the vendored runner called `python3` in ten places, invisible because the payload is base64 |

The `no second implementation` guard is mutation-tested by construction — drop a `.sql`
file anywhere outside `vendor/`, add a script that shells out to `osqueryi`, or paste
`FROM apps` into a `.py`, and it names the file and fails.

## `test/run-collector.sh`

Runs this platform's build — `dist/collect.sh` on macOS, `dist/collect-linux.sh` on Linux —
three times into a scratch directory and asserts on what it wrote. Root is not required — a Policy runs it as root and sees more rows, but nothing asserted here
depends on that.

| Guard | What it catches |
|---|---|
| `collect.sh` exits 0 and writes all three files | The preamble failing to extract or run at all — `base64 -D` vs `-d`, `tar`, `chmod`, a `TMPDIR` a Jamf-run script does not have |
| `inventory.ea` is one line, mode 644, `arthur1.`-prefixed | A wrapped base64 value carrying newlines into `<result>`, or a value the EA script cannot read as a user |
| `inventory.ea` decodes byte-for-byte back to `inventory.json` | **The attribute not being this scan.** This tree shipped that: a failed run left the previous payload in place and the framing step re-framed it into a fresh-looking value and exited 0 |
| Six-column rows, one `kind=scan` marker per branch, every marker dated within the hour | A branch silently not running; a kept payload passing as a fresh one |
| The branch set in `status.txt` equals the marker set in the payload | The two attributes describing different scans — a Smart Group and a payload that disagree about what ran |
| Framed size under the cap `collect.sh` itself declares | A Mac that would report `ERROR:oversize` instead of its inventory, and a cap that drifted from the one being enforced |
| A failed scan: non-zero exit, **both attribute values untouched** | Either half of the trade this tree made — republishing a stale value as fresh, or deleting a good one to signal a problem |
| A failed first-ever scan: non-zero exit, **no files at all** | A partial file left behind claiming to be a result, when `no-cache` is the true answer |
| A scan that fails its JSON check — the shipped driver against a stub `discover` whose `--cache` cannot run — leaves both previous files untouched, passes discover's reason through, and leaves no staging directory | A failure after the scan erasing the last good inventory. Every step of a run, not only the scan, keeps the last good one |
| No `arthur-collect.*` directory left behind | The extraction directory leaking once per run, which on an Ongoing schedule fills a volume months later |

The container branch: the macOS runner has no Docker and reports `absent`; the Ubuntu runner
has one and reports `ok`. The 15s cold-ping bound is reached by neither. The daemon states are
upstream's `test/docker_states.sh`, against the vendored runner.

## `test/run-guest-attributes.sh`

Runs `deploy/report-guest-attributes.sh` against `test/fake-metadata-server.py`, with a stub
for the collector, because the question is what the reporter publishes from each thing a
collector can leave behind. The fake answers only as a real VM measurably did: the 262,144-byte
cap with its 400, and the 403 when guest attributes are disabled.

| Case | What it catches |
|---|---|
| A clean scan is published byte for byte, without the file's newline | A value one byte too long, or not this scan |
| A value of exactly 262,144 bytes is accepted | The newline pushing a value at the cap over it |
| A refused inventory keeps the previous value; the status says `inventory=refused:400` | A VM serving an old inventory with nothing saying why |
| A failed run publishes the kept scan with `failed=<UTC>` | A failure that looks like a fresh scan |
| No scan ever, no osquery: `no-cache`, and `no-cache failed=<UTC> osquery=absent` | An empty key, which reads as a clean VM |
| Guest attributes disabled: the 403 named, nothing stored | A VM that cannot report and says nothing |
| No metadata server: named, non-zero | The same, off Compute Engine |
| `status.txt` without `inventory.ea`: both keys `no-cache` | A status claiming a scan the inventory does not carry |
| One 503, retried through to success | A transient failure failing the run |
| Inventory refused, then the status request dropped: each logged with its own reason | A reason left over from the previous request |
| `http_proxy` set to a dead proxy: published directly | A fleet-wide proxy capturing the link-local metadata request |
| `TERM` during collection: non-zero, nothing published | A stopped run carrying on without its working directory and blaming the metadata server |

`flaky` (one 503) and `drop-status` (no answer on the `status` key) are the fake's own
behaviours, labelled as such; every other answer it gives was measured on a real VM.

## `test/run-systemd.sh`

Installs the Linux collector, the reporter and the units at their real paths, runs one
activation under systemd against the fake, one with `/tmp` and `/var/tmp` remounted `noexec`
(where the collector run by hand with no `TMPDIR` must fail and the unit must succeed), one with
guest attributes disabled, then starts the timer and checks it has a next run, and removes
everything. It writes to the machine, so it runs only with
`ARTHUR_TEST_INSTALLS_UNITS=1`, as root, where systemd is PID 1 — in CI, the Ubuntu runner.

## Running the real thing

There is no test-only path — `run-collector.sh` runs `dist/collect.sh`, and so should you:

```bash
sudo ARTHUR_OUT_DIR=/tmp/arthur dist/collect.sh
cat /tmp/arthur/status.txt
python3 -m json.tool /tmp/arthur/inventory.json | less
```

With Docker down the run says so (`containers=unhealthy:000`) rather than reporting zero
images. Needs osquery and nothing else; it writes three files and installs nothing. For what a
reference Mac reports, see the [README](../README.md#try-it). The numbers live in one place
so they cannot disagree.
