# AI Inventory on Jamf Pro

Deploying the `osquery-ai-discovery` endpoint to a managed Mac fleet: a scheduled scan that
writes a file, and two Extension Attributes that only read it. Nothing on the inventory path
can block.

**Two Extension Attributes and one script.** A Jamf Policy runs the script on a schedule and
it writes three files; the attributes `cat` them. **Nothing is packaged, signed or notarized**
— the script carries its own payload.

> **There is no inline alternative any more.** This tree once carried a script that *was* the
> Extension Attribute and ran the query inline. It has been deleted, and "Why nothing runs
> inline" at the foot records the measurements that decided it — chiefly a Docker daemon that
> answers `/_ping` with 200 and then never serves `/images/json`, which every probe in the
> guard matrix admits and no Jamf timeout cuts off.

| | |
|---|---|
| Target | Jamf Pro |
| Requires | osquery 5.10+ (5.11+ for the VS Code branch). Nothing else — no interpreter, no Command Line Tools |
| Per-Mac cost | ~7s per Policy run, off the reporting path |
| Attribute value | 21 KB of a 256 KB budget (Jamf itself stores ≥ 1 MB — measured) |

**Do not put `osqueryi`, `bin/discover` or `bin/container-scan` directly in an Extension
Attribute.** Measured against a Docker daemon that answers `/_ping` and then stops serving,
the query never returns — and there is no documented Jamf timeout to save you. Community
evidence runs the other way: EAs at 21 seconds, and `jamf recon` *stalling* rather than being
cut off.

## 00 · Prerequisites — fleet

| Requirement | Why | Confirm with |
|---|---|---|
| osquery 5.10+, **5.11+ for VS Code** | Every query runs through `osqueryi`. All declare `min-osquery: 5.10.0` except `vscode.sql`, which needs **5.11.0** — the `vscode_extensions` table does not exist below it | Application inventory, or `osqueryi --version` |
| Root LaunchDaemon | Some branches read other users' home directories | Standard for a Jamf-deployed daemon |

**The python3 trap is closed as of vendored ref `v0.5.0`, and it is worth knowing what it
was.** `/usr/bin/python3` is a *stub* on a clean macOS install — Apple removed bundled Python in
macOS 12.3 and left a shim that forwards to the active developer directory. Without Command Line
Tools it fails, the job wrote nothing, and both attributes reported `no-cache`, which is
indistinguishable from a Mac with no AI tools on it. **Do not deploy Command Line Tools for this
project.** Nothing on the endpoint has needed them since v0.5.0.

Two halves closed it, and this tree's was not sufficient alone. The framing step here uses
`gzip`/`base64`/`plutil`, all stock; upstream then removed its own last interpreter, moving the
JSON work into shell helpers and osquery's `json_valid`/`json_type` — a dependency the endpoint
already has. `test/lint.sh` holds both ends: it fails if the collector reaches for an
interpreter, and it fails if the payload's real dependencies and this table disagree in either
direction.

## 00b · Find and fix the Macs that cannot collect — Jamf Pro

osquery is the only prerequisite, and it is invisible to Jamf by default: it installs under
`/opt/osquery`, which Application inventory does not scan, and package-receipt criteria depend
on a bundle id that has changed across releases. When it is missing the collector writes
nothing and both attributes report `no-cache` — indistinguishable from a Mac with no AI tools
on it. So measure it, group on the failures, and scope a Policy at the group.

*(Command Line Tools were a second prerequisite until vendored ref `v0.5.0`. They are not one
now — see section 00. Do not deploy them for this project.)*

### The Extension Attribute

**Settings → Computer Management → Extension Attributes → New.** Data Type `String`, Input Type
`Script`. It reports a *reason*, because "missing" and "too old" need different fixes.

| Field | Value |
|---|---|
| Display Name | `Arthur AI Osquery Prereq` |
| Data Type | `String` |
| Inventory Display | `Extension Attributes` |
| Input Type | `Script` |

```bash
#!/bin/bash
FLOOR_MAJOR=5
FLOOR_MINOR=11   # vscode_extensions arrives in 5.11; every other branch needs 5.10

# THE LOOKUP ORDER MIRRORS THE COLLECTOR'S. bin/container-scan resolves $OSQI, then three
# absolute paths, then $PATH. An EA that looked anywhere else could report "installed" on a
# Mac where the collector finds nothing, and then the coverage number measures the wrong thing.
for c in "${OSQI:-}" /usr/local/bin/osqueryi \
         /opt/osquery/lib/osquery.app/Contents/MacOS/osqueryi \
         /usr/bin/osqueryi; do
  [ -n "$c" ] && [ -x "$c" ] && { found="$c"; break; }
done
[ -n "${found:-}" ] || found="$(command -v osqueryi 2>/dev/null)"
[ -n "${found:-}" ] || { echo "<result>absent</result>"; exit 0; }

ver="$("$found" --version 2>/dev/null | awk '{print $NF}')"
[ -n "$ver" ] || { echo "<result>unreadable</result>"; exit 0; }

major="${ver%%.*}"; rest="${ver#*.}"; minor="${rest%%.*}"
if [ "${major:-0}" -lt "$FLOOR_MAJOR" ] 2>/dev/null ||
   { [ "${major:-0}" -eq "$FLOOR_MAJOR" ] && [ "${minor:-0}" -lt "$FLOOR_MINOR" ]; } 2>/dev/null; then
  echo "<result>old:$ver</result>"
else
  echo "<result>$ver</result>"
fi
```

### Smart Groups

**Computers → Smart Computer Groups → New**, one per row. A criterion is three parts — the
attribute, the operator, the value — and the member count is a deployment target list.

| Group | Criteria | Operator | Value | Fix |
|---|---|---|---|---|
| Prereq — osquery missing | `Arthur AI Osquery Prereq` | **is** | `absent` | Install the pkg |
| Prereq — osquery too old | `Arthur AI Osquery Prereq` | **like** | `old:` | Upgrade; these Macs report `vscode=error` |

**`is` where the whole value is the sentinel, `like` where you are matching a fragment.** Jamf's
`like` is a substring test, so `like` `absent` would also catch a future value that merely
contains the word, and a false positive here installs software on a Mac that did not need it.
`old:` always carries a version (`old:5.10.2`), so it can only be matched by fragment — using
**is** with `old:` matches nothing, silently, and an empty Smart Group reads exactly like a
healthy fleet.

**A BLANK ATTRIBUTE IS NOT `absent`, AND NO GROUP ABOVE CAN SEE IT.** The script always
prints one of four values, so it cannot produce a blank; a blank means it never ran on that
Mac — the attribute was created after the Mac's last inventory submission. Those Macs are
invisible to every criterion on this attribute, and to every criterion on the other two, by
construction: an attribute with no value matches neither `is` nor `like` nor their negations.

They are also the population most likely to be mistaken for coverage. A fleet where a third
of the Macs stopped checking in months ago reads as a fleet where a third have no AI tooling,
and no amount of narrowing on attribute values will show otherwise. **Only Jamf's own
`Last Inventory Update` can see a Mac that is not reporting** — see the group in 06.

A **blank** value is not a failure: it is a Mac that has not submitted inventory since you
created the attribute, so the attribute has never run there. Those fill in within a day, and
they are invisible to every criterion above including `is not`. To find them, use operator
**is** with an empty value, or sort an Advanced Search by the column.

### Remediation

**1 · Get the package.** Download the macOS `.pkg` from
[osquery.io/downloads](https://osquery.io/downloads), or your internal mirror. Check the version
against the 5.11 floor before uploading it.

**2 · Upload it.** *Settings → Computer Management → Packages → **New***. Choose the file under
**Filename**, leave the rest at defaults, **Save**. This needs a distribution point; on Jamf
Cloud that is the Jamf Cloud Distribution Point and the upload happens in the browser.

**3 · Create the Policy.** *Computers → Policies → **New***. You land on the **General** payload:

| Field | Value |
|---|---|
| Display Name | `Install osquery` |
| Enabled | checked |
| Trigger | check **Recurring Check-in** |
| Execution Frequency | **Once per computer** |

**4 · Attach the package.** In the left sidebar of the same Policy, click **Packages** →
**Configure** → **Add** beside your osquery package → set **Action** to **Install**. The
*Configure* step is easy to miss: until you click it the payload shows nothing to add.

**5 · Scope it.** The **Scope** tab at the top of the Policy → *Targets* → **Add** → *Computer
Groups* → `Prereq — osquery missing`. **Save**.

**6 · Watch it drain.** Update Inventory, then watch the group empty as Macs check in and report
a version. Scoping at the group the attribute feeds is what makes this self-managing: a Mac
installs osquery, its next inventory reports a version, it leaves the group, and the Policy
stops targeting it. Nothing to turn off afterwards.

`no-cache` on the two AI attributes should drain behind it. A Mac still reporting `no-cache`
with osquery green is a different fault — read its Policy log, and see section 08.

## 01 · Build the payload — terminal

**Build it here, not from the public repo.** The plist and the collector live in this tree,
and `catalog/` must never reach a Mac at all — matching happens
in the collector, and shipping the signatures to the endpoint is the one thing the design
forbids. See [`architecture.md`](../architecture.md).

There is also nothing left to lay out side by side. `dist/collect.sh` carries `bin/` and `dist/`
inside it as an embedded payload and extracts them to a private temp directory at run time, so
the whole deployable is one file for both paths below.

```bash
git clone https://github.com/arthur-ai/arthur-engine
cd arthur-engine/integrations/endpoint-ai-discovery

# Already vendored and built in the tree. Only if you are moving to a newer upstream ref:
tools/vendor-queries.sh <ref>          # verifies upstream's own build gate before copying
tools/build-collector.py               # rebuild dist/collect.sh around the new tree

tools/build-collector.py --check       # expect: dist/collect.sh is up to date (vendored ref …)
test/lint.sh                           # ~1s; gates the vendored tree and the built collector
```

**Verify.** `--check` names the vendored ref, and `cat vendor/osquery-ai-discovery/VERSION`
shows the same one. A ref pinned to a bare commit prints `PROVISIONAL`, which is legitimate and
means no upstream tag carries it yet. Drift means `dist/collect.sh` was built before the last
vendor — rebuild it rather than deploying it.

## 02 · Add the collector to Jamf — Jamf Pro

**No package, no signing, no notarization.** `dist/collect.sh` is one self-contained
file, built by `tools/build-collector.py`: `bin/` and `dist/` travel inside it as an embedded
payload, so Jamf needs only to host a script and run it. It installs nothing — the payload is extracted to a private temp
directory, run, and deleted.

**Settings → Computer Management → Scripts → New.** Paste the whole of
`dist/collect.sh`.

| Field | Value |
|---|---|
| Display Name | `AI Inventory Collector` |
| Category | your usual |
| Priority | `After` |

Then **Computers → Policies → New**:

| Field | Value |
|---|---|
| Trigger | `Recurring Check-in` |
| Execution Frequency | `Once every day` (or `Ongoing` for check-in cadence) |
| Scripts | `AI Inventory Collector` |
| Scope | your pilot Smart Group |

The script ignores the three positional arguments Jamf passes, needs no parameters, and
prints its status line to stdout — so the Policy log shows the outcome without you opening
anything else.

**Verify.** Run the Policy once against a test Mac. The Policy log should read:

```
ok 2026-09-04T23:50:36Z rows=775 apps=ok browser=ok containers=ok filesystem=ok homebrew=ok native-messaging=ok packages=ok ports=ok runtime=ok vscode=ok
```

**Ten branches on macOS** as of v0.3.0: `apps`, `browser`, `containers`, `filesystem`,
`homebrew`, `native-messaging`, `packages`, `ports`, `runtime`, `vscode`. A status line with
six is from before that ref.

Measured cold, from a directory containing nothing but the script, under a stripped
environment: **~7s**, three files written, no temp directory left behind. It was 4.3s at six
branches; ten branches and a container scan are the difference.

### If you would rather deploy a package

A package is a legitimate alternative — it puts `bin/` and `dist/` at a fixed path and runs
them from a LaunchDaemon, which decouples the schedule from Jamf's check-in and keeps the
scan running even if the Policy is later unscoped. It costs a build step and a signing
identity. `deploy/com.arthur.ai-discovery.plist` carries the install and uninstall commands
in its header. Everything from step 04 onward is identical either way — both write the same
three files.

## 03 · Prove it on one Mac — terminal

```bash
# the Policy will have written these; to run it by hand:
sudo /bin/bash dist/collect.sh
ls -l /var/lib/arthur/
```

**Verify — three files.**

```
inventory.json   ~127 KB   the readable payload
inventory.ea      ~21 KB    the framed attribute value, one line
status.txt        ~155 B    one line, for Smart Groups
```

```console
$ cat /var/lib/arthur/status.txt
degraded 2026-09-04T23:50:36Z rows=775 apps=ok browser=ok containers=unhealthy:000 filesystem=ok homebrew=ok native-messaging=ok packages=ok ports=ok runtime=ok vscode=ok
```

A first token of `degraded` is not necessarily a failure — on a Mac with no Docker,
`containers=absent` is the correct answer.

**Docker Desktop is per-user.** Its socket belongs to the installing user and its engine runs
only while that user is logged in, so a root scan at 03:00 legitimately records
`containers=absent` on a Mac that has Docker. Expect container coverage to reflect working
hours.

**`unhealthy:000` is a different thing, and it is not benign.** This ran for a while reporting
`unhealthy:000` on a Mac whose Docker was up for four days and holding 13 images. The cause was
not permissions — root reaches a user's socket fine, verified — but a ping too short to outlast
a cold daemon. A scheduled scan is always the cold case, and an operator checking by hand always
sees it working, because checking warms the daemon. `dist/collect.sh` sets
`DOCKER_PING_TIMEOUT=15`, above upstream's default of 8, because 15 also clears the ~10s a
wedged engine takes to answer 500 — without which the `unhealthy:500` row below never appears.
`test/lint.sh` fails if it drops below 10, or below the vendored default. Upstream's
`docs/containers.md` has the per-state costs.

**If you see `unhealthy:000` on a fleet Mac that has Docker running, treat it as a fault to
investigate, not as the night shift.**

## 04 · The inventory attribute — Jamf Pro

**Settings → Computer Management → Extension Attributes → New.**

**The display name is yours to choose.** The collector finds this attribute by the
`arthur1.` prefix on its value, not by name, so renaming it — or prefixing it to sit
beside your other attributes — changes nothing. The names below are what the reference
deployment uses.

| Field | Value |
|---|---|
| Display Name | `Arthur AI Inventory` |
| Data Type | `String` |
| Inventory Display | `Extension Attributes` |
| Input Type | `Script` |

```bash
#!/bin/bash
# Reads only. The scan runs from a LaunchDaemon, so recon cannot block on it.
VALUE="/var/lib/arthur/inventory.ea"
if [ -r "$VALUE" ]; then
  echo "<result>$(cat "$VALUE")</result>"
else
  echo "<result>no-cache</result>"
fi
```

The value is `arthur1.<base64(gzip(json))>` on a single line. Report the framed file, not
`inventory.json`: raw JSON is roughly **6x the framed value**. The scheduled job is the only
thing that frames, since the inline script that carried a second copy of the format is gone.

**Verify.** One line beginning `<result>arthur1.H4sIA`, about 21,000 bytes, no newlines
inside. To confirm it round-trips:

```bash
python3 -c 'import base64,gzip,json,re,sys
v=re.search(r"<result>(.*)</result>",sys.stdin.read(),re.S).group(1)
print(len(json.loads(gzip.decompress(base64.b64decode(v[8:])))),"rows")'
```

## 05 · The status attribute — Jamf Pro

Not optional. The inventory value is base64 of gzip, so **a Smart Group cannot see inside
it** — you could collect the data and still have no way to ask which Macs are failing.

| Field | Value |
|---|---|
| Display Name | `Arthur AI Inventory Status` |
| Data Type | `String` |
| Inventory Display | `Extension Attributes` |
| Input Type | `Script` |

```bash
#!/bin/bash
STATUS="/var/lib/arthur/status.txt"
[ -r "$STATUS" ] || { echo "<result>no-cache</result>"; exit 0; }
line="$(cat "$STATUS")"
# AGE FROM THE TIMESTAMP INSIDE THE VALUE, not the file's mtime -- a redeploy resets mtime
# without changing the truth. The collector serves the last good scan when a run fails, so a
# healthy-looking `ok` can be days old and this token is the only thing that says so.
stamp="$(echo "$line" | awk '{print $2}')"
secs="$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$stamp" +%s 2>/dev/null)"
if [ -n "$secs" ]; then
  age=$(( ( $(date -u +%s) - secs ) / 3600 ))
  [ "$age" -ge 24 ] && line="$line stale=${age}h"
fi
echo "<result>$line</result>"
```

**Why this one does arithmetic when the inventory EA does not.** A failed scan no longer
erases the last good one — the collector keeps serving it and fails the Policy instead — so
`ok` on its own stopped being evidence of a recent scan. The timestamp was always in the
value; `stale=NNh` is what makes it matchable by a Smart Group, which cannot compare dates
inside a string.

**Verify.**

```
<result>degraded 2026-09-04T23:50:36Z rows=775 apps=ok browser=ok containers=unhealthy:000 filesystem=ok homebrew=ok native-messaging=ok packages=ok ports=ok runtime=ok vscode=ok</result>
```

First token is `ok` or `degraded`, then a UTC timestamp, a row count, and one
`branch=outcome` token per query.

## 06 · Smart Groups — Jamf Pro

All five read **Arthur AI Inventory Status**. The operator differs by row, and it is not cosmetic: `is`
is an exact match on the whole stored value, `like` is a substring test. `no-cache` is the only
one whose stored value is the entire string; the rest are tokens inside a status line that also
carries a timestamp, a row count and ten branches, so **is** on any of those matches nothing.

| Group | Operator | Value | Meaning |
|---|---|---|---|
| AI inventory — not reporting | **is** | `no-cache` | The daemon has never written. osquery missing, package failed, or daemon not loaded. **Fix first** |
| AI inventory — degraded | **like** | `degraded` | At least one branch did not return `ok`. Often benign; narrow with the next two |
| Container scan blocked | **like** | `containers=timeout` | Answered `/_ping` then stalled. A wedged Docker engine — real and fixable |
| A branch errored | **like** | `=error` | A query failed outright, typically an osquery build without a table it needs |
| Serving a stale scan | **like** | `stale=` | The last scan is over a day old. The Mac is reporting real evidence, but the collector has not succeeded since — check the Policy log |

One more, and it does **not** read an Extension Attribute:

| Group | Criteria | Operator | Value | Meaning |
|---|---|---|---|---|
| Not reporting to Jamf | `Last Inventory Update` | **more than x days ago** | `30` | Jamf has not heard from this Mac. Nothing above can see it, whatever its attributes last said |

**This is the denominator, and it is the group to build first.** Every other group here reads
a value the Mac submitted; this one is the only one that can find a Mac that submitted
nothing. Retired hardware lives here, and so does a Mac whose collector broke the same week it
stopped checking in — which is why the two must not be counted together. Scope the discovery
source to exclude it, or its coverage number is permanently wrong in a way no fix improves.

Thirty days is a starting point, not a measurement: it wants to sit above your recon interval
by enough that an ordinary laptop on holiday does not land in it.

**The first token does not carry age.** It says whether the last scan succeeded, not when it
ran, so a daemon that stopped a month ago keeps reporting `ok`. That is what the `stale=NNh`
suffix is for: the status attribute computes it from the timestamp inside the value, because
Jamf cannot do date arithmetic on a string — hence the `like stale=` group above. The payload
also carries a per-branch timestamp, and `bin/classify` prints `STALE:` past a day.

## 07 · Scope and roll out — Jamf Pro

The Extension Attributes collect from every Mac in inventory whether or not the package is
installed — which is why the `no-cache` group exists. Scope the **package**, not the
attributes.

1. **A pilot Smart Group first** — a dozen Macs spanning your osquery versions, including at
   least one heavy Docker user.
2. **Update Inventory**, then read the status attribute across the pilot. Anything reporting
   `no-cache` did not deploy.
3. **Check the value length** on your most loaded pilot Mac. 21 KB is typical; the budget binds
   near 10,300 rows.
4. **Widen in stages.** The payload rides in every inventory submission: roughly 180 MB per
   full sync at 10,000 Macs.

**Watch the value size, not the row count.** An attribute that overruns the 256 KB budget used
to report *nothing*, which is indistinguishable from a Mac with nothing on it. It now reports
`ERROR:oversize:<bytes>` instead — unframed, matchable by a Smart Group, and it replaces the
previous value rather than leaving a stale one looking current. The framed value is
dominated by how loaded the Mac is — applications and Homebrew packages — not by how many AI
agents it has. Container image rows are the most expensive in the payload at ~84 bytes each.

## 08 · Reading the results — Jamf Pro

Every `branch=outcome` token, and what to do. This is the entire vocabulary.

| Outcome | Meaning | Action |
|---|---|---|
| `ok` | The branch ran; its rows are in the payload | None |
| `absent` | No Docker socket on this Mac | None. Correct for a Mac without Docker |
| `unhealthy:000` | Socket exists, nothing answered within the ping timeout. Docker installed and not running, or no user logged in | Expected with no user logged in. **On a Mac with Docker running it is a fault** — too short a ping cannot outlast a cold daemon, which is why the collector sets 15s |
| `unhealthy:500` | Daemon up, engine not serving | Restart Docker |
| `timeout:6` | Answered `/_ping`, then stalled and was killed at 6s | Restart Docker. This is the state the wall-clock bound exists for |
| `error` | Query failed outright — usually a table this osquery build lacks | Check the version against `min-osquery`. `vscode=error` on osquery 5.10 is this and is expected: `vscode_extensions` arrived in 5.11 |
| `no-cache` | The daemon has **never** written here | Deployment problem. Check osquery is installed (section 00b), then the daemon and `/var/log/arthur-ai-discovery.log` |
| `stale=NNh` | The value is a real scan, NNh old, kept because a later run could not collect | The evidence is still good; the collector is not. Read the Policy log — the Mac has been failing since that timestamp |

Two values are not `branch=outcome` tokens at all. `ERROR:oversize:<bytes>` on `Arthur AI Inventory`
means the payload framed larger than the 256 KB budget and the reason was reported in place of
the evidence; `Arthur AI Inventory Status` is unaffected and still says which branches ran. `stale=NNh`
is appended by the status attribute itself, not written by the collector.

**A failed Policy beside a healthy attribute is expected, not a contradiction.** The two carry
different things. When a scan cannot run the collector keeps the last successful payload and
exits non-zero, so Jamf shows the Policy as failed while the attributes keep serving real
evidence — deliberately, because discarding a good payload would report a well-equipped Mac as
empty. Read the Policy log for *why this run failed*, and `stale=NNh` for *how old what you are
looking at is*. A Mac failing for weeks shows both.

### Decoding one Mac's value by hand

```bash
pbpaste | python3 -c 'import base64,gzip,json,sys
v=sys.stdin.read().strip()
json.dump(json.loads(gzip.decompress(base64.b64decode(v[8:]))),sys.stdout,indent=1)' \
  | vendor/osquery-ai-discovery/bin/classify /dev/stdin
```

Prints the findings, which branches ran and when, and `COULD NOT LOOK` for any that did not.

**An image name is weak evidence.** Container image rows resolve by exact repository match
through the catalog's `images` route, but an image name is chosen by whoever ran `docker tag` —
no other identifier in the catalog is. `docker tag alpine paulgauthier/aider` produces an aider
finding indistinguishable from the real image. That is the catalog's one remaining `images`
entry: the model-runner images went with the model runners when upstream narrowed the scope
to agents.

## 09 · Rollback — terminal

Unscope the Policy, then on the Macs:

```bash
rm -rf /var/lib/arthur
```

That is the whole footprint of the script path — it installs nothing else. If you deployed
the package instead:

```bash
launchctl bootout system/com.arthur.ai-discovery
rm -f /Library/LaunchDaemons/com.arthur.ai-discovery.plist
rm -rf /usr/local/arthur /var/lib/arthur /var/log/arthur-ai-discovery.log
```

Then delete or disable both Extension Attributes. Disabling keeps historical values on the
computer records; deleting discards them.

**If you used the package: `bootout` before `bootstrap`, always.** `launchctl` will not reload a changed plist for an
already-loaded label, so an upgrade that skips the bootout leaves the old definition running
and the new files unused — with no error anywhere.

## Why nothing runs inline

The obvious design is an Extension Attribute that runs the query itself, behind a round-trip
guard that demands HTTP 200. This tree built that, shipped it, and then deleted it. The guard
is necessary and it is **not sufficient**. Measured, per Docker state, on whether each guard
admits the branch:

```
                    absent  refuse  hang   error  wedge   healthy
connect() only      skip    skip    RUN    RUN    RUN     RUN      <- stalls forever
curl -s             skip    skip    skip   RUN    RUN     RUN      <- silent zero rows
HTTP 200 required   skip    skip    skip   skip   RUN     RUN      <- still stalls
200 + wall clock    skip    skip    skip   skip   KILLED  RUN      <- correct
```

`wedge` — 200 on `/_ping`, silence on `/images/json` — is Docker Desktop with a live API and an
engine that is not serving, which is the ordinary condition of a Mac starting Docker. The
window between probe and query is small and not zero.

Two further measurements bear on it:

- **An interrupted `osqueryi` exits 0 and prints `[\n\n]`** — valid, parseable, empty JSON. Any
  wrapper that bounds it must discard output because *it* fired the kill, never on the child's
  exit code.
- **One unavailable table zeroes a composed query.** Add a branch whose table this osquery build
  lacks and the whole statement returns 0 rows and exit 1, with five bytes of valid empty JSON
  on stdout. Run the branches in separate processes and it costs one branch: 6 of 6 reported,
  757 rows, the bad one contributing 0. Every query declares `min-osquery: 5.10.0`, so this is
  a real deployment state.

Both are why the scheduled writer runs each branch in its own bounded process and reports a
per-branch outcome.

---

**What this tree reports.** Names, paths, versions and declared permissions. No file contents, no
secrets, no browser history or cookies, and nothing it discovers is executed. It also does
nothing to the machine — no blocking, no remediation, no network calls of its own.

**What it cannot see.** Anything inside a VM guest. What a running container is *doing*, as
opposed to which images exist. Containers outside Docker Desktop — Colima, Rancher, Podman.
Which filesystem roots an MCP server exposes. Outbound destinations by hostname.

Measurements here come from an Apple Silicon Mac on macOS 26, osquery 5.23.1 and Docker 28.4.0,
with 765 inventory rows. Re-measure on your own image before trusting the value-size headroom.
