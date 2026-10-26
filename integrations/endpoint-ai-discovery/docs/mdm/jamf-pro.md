# AI Inventory on Jamf Pro

A Jamf Policy runs `dist/collect.sh` on a schedule. The script scans the Mac and writes three
files to `/var/lib/arthur/`. Two Extension Attributes read two of those files back with `cat`,
and Arthur reads the attributes through the Jamf Pro API. Nothing is packaged, signed or
notarized, because the script carries its own payload. The
[quick start](../quickstart.md#macs-managed-by-jamf-pro) is the short version of this runbook.

| | |
|---|---|
| Requires | osquery 5.18 or later. No interpreter and no Command Line Tools |
| Per-Mac cost | ~8s per Policy run, outside the inventory path |
| Attribute size | ~24 KB, within a 256 KB budget. Jamf has stored values of at least 1 MB (measured) |

**Never run `osqueryi`, `bin/discover` or `bin/container-scan` inside an Extension Attribute.**
A Docker daemon that answers its health check and then stalls hangs the query, and with it
`jamf recon`. Jamf documents no timeout for Extension Attributes. The scheduled script puts a
time limit on every query; the attributes only read files. Upstream's
[deployment guide](https://github.com/arthur-ai/ai-detection-spec/blob/main/osquery/docs/deployment.md)
gives the details.

## 00 · Install osquery — Jamf Pro

Install osquery 5.18 or later. Older versions run, but every branch whose table they lack
reports `error`. Upstream's
[`docs/limits.md`](https://github.com/arthur-ai/ai-detection-spec/blob/main/docs/limits.md)
lists which branch needs which version.

Jamf does not see osquery by default: it installs under `/opt/osquery`, which Application
inventory does not scan. A Mac without osquery reports `no-cache` on both attributes. So report
the version with an Extension Attribute, group the Macs that fail, and install osquery on those
groups.

**The attribute.** Go to *Settings → Computer Management → Extension Attributes → New*. Set
Display Name to `Arthur AI Osquery Prereq`, Data Type to `String` and Input Type to `Script`:

```bash
#!/bin/bash
FLOOR_MAJOR=5
FLOOR_MINOR=18   # the newest table a branch needs; which is upstream's docs/limits.md

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

**Two Smart Groups.** Create them under *Computers → Smart Computer Groups → New*:

| Group | Criteria | Operator | Value |
|---|---|---|---|
| Prereq — osquery missing | `Arthur AI Osquery Prereq` | **is** | `absent` |
| Prereq — osquery too old | `Arthur AI Osquery Prereq` | **like** | `old:` |

**is** matches the whole value, and **like** matches part of it. Using **is** with `old:`
matches nothing, and gives no error. A blank value means the Mac has not submitted inventory
since you added the attribute; it fills in at the Mac's next recon.

**The install Policy:**

1. Download the macOS `.pkg` from [osquery.io/downloads](https://osquery.io/downloads), or
   take it from your mirror. Upload it at *Settings → Computer Management → Packages → New*.
2. Create a Policy at *Computers → Policies → New*. Set Display Name to `Install osquery`,
   tick *Recurring Check-in*, and set Execution Frequency to *Once per computer*.
3. Under *Packages*, choose *Configure*, then *Add* beside the osquery package, and set Action
   to *Install*.
4. Under *Scope → Targets*, choose *Add → Computer Groups* and add both Prereq groups. Save.

Each Mac leaves the groups once it reports a new enough version, so the Policy stops targeting
it automatically. *Once per computer* counts runs, not versions. When the version floor rises,
attach the new package to a **new** Policy scoped to `Prereq — osquery too old`. Wait for that
group to empty before you deploy a collector that needs the newer version. Until a Mac
upgrades, it reads `degraded` and swamps the groups in section 06.

## 01 · Get the collector — terminal

`dist/collect.sh` is built and committed. Take it from a release tag of this repository:

```bash
git clone --depth 1 --branch REF https://github.com/arthur-ai/arthur-engine
cd arthur-engine/integrations/endpoint-ai-discovery
tools/build-collector.py --check   # expect: dist/collect.sh is up to date (vendored ref …)
```

`--check` prints the vendored ai-detection-spec ref, which
`vendor/ai-detection-spec/VERSION` also records. A ref pinned to a bare commit prints
`PROVISIONAL`; that is legitimate. If the check reports drift, run `tools/build-collector.py`
to rebuild the script before you deploy it.

## 02 · Run the collector on a schedule — Jamf Pro

Go to *Settings → Computer Management → Scripts → New*. Set Display Name to
`AI Inventory Collector` and Priority to `After`, then paste all of `dist/collect.sh`.

Then create a Policy at *Computers → Policies → New*:

| Field | Value |
|---|---|
| Trigger | `Recurring Check-in` |
| Execution Frequency | `Once every day`, or `Ongoing` to run at every check-in |
| Scripts | `AI Inventory Collector` |
| Scope | your pilot Macs |

The script ignores the arguments Jamf passes and prints its status line, so the Policy log
shows the result. Scope the Policy, not the attributes. The attributes run on every Mac and
report `no-cache` wherever the script has not run.

**To deploy a package instead,** install `dist/collect.sh` with
`deploy/com.arthur.ai-discovery.plist`; the plist's header has the install commands. A
LaunchDaemon then runs the scan on its own schedule, separate from Jamf check-in, and it keeps
running if the Policy is unscoped. A package needs a build step and a signing identity. Both
ways write the same files, so the rest of this runbook is the same.

## 03 · The inventory attribute — Jamf Pro

Go to *Settings → Computer Management → Extension Attributes → New*:

| Field | Value |
|---|---|
| Display Name | `Arthur AI Inventory` |
| Data Type | `String` |
| Inventory Display | `Extension Attributes` |
| Input Type | `Script` |

```bash
#!/bin/bash
# Reads only. The scan runs on its own schedule, so recon cannot block on it.
VALUE="/var/lib/arthur/inventory.ea"
if [ -r "$VALUE" ]; then
  echo "<result>$(cat "$VALUE")</result>"
else
  echo "<result>no-cache</result>"
fi
```

The value is `arthur1.<base64(gzip(json))>` on one line. Arthur finds this attribute by the
`arthur1.` prefix on its value, not by its name, so you can name it anything.

## 04 · The status attribute — Jamf Pro

The inventory value is compressed, so a Smart Group cannot match anything inside it. This
attribute carries the status line as plain text, which a Smart Group can match.

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

When a run fails, the collector keeps serving the last good scan, so `ok` alone does not mean
the scan is recent. A Smart Group cannot compare dates inside a string, so this script appends
`stale=NNh` once the scan is more than a day old.

## 05 · Prove it on one Mac — the Mac

On a pilot Mac:

```bash
sudo jamf policy     # runs the collector; the log ends with its status line
sudo jamf recon      # submits inventory, which runs both attributes
ls -l /var/lib/arthur/
```

You should see three files:

```
inventory.json   ~155 KB   what the scan found, readable
inventory.ea      ~24 KB   the inventory attribute's value, one line
status.txt        ~200 B   the status attribute's value
```

The status line has one `branch=outcome` token per query branch. At the vendored ref there are
thirteen on macOS:

```
ok 2026-10-11T22:57:49Z rows=929 apps=ok browser=ok containers=ok filesystem=ok homebrew=ok jetbrains=ok native-messaging=ok packages=ok ports=ok running=ok running-darwin=ok runtime=ok vscode=ok
```

In Jamf, the Mac's record should show *Arthur AI Inventory* starting with `arthur1.H4sI`, and
*Arthur AI Inventory Status* holding a line like the one above. To see the findings in a value
you copied from Jamf, run this from this directory:

```bash
v=../../ml-engine/src/ml_engine/discovery/_vendor; t="$(mktemp -d)"
mkdir "$t/bin" "$t/schema" && cp "$v/classify.py" "$t/bin/classify" && cp "$v/catalog.schema.json" "$t/schema/"
pbpaste | python3 -c 'import base64,gzip,json,sys
v=sys.stdin.read().strip()
json.dump(json.loads(gzip.decompress(base64.b64decode(v[8:]))),sys.stdout,indent=1)' \
  | AI_DETECTION_SPEC_TELEMETRY=0 python3 "$t/bin/classify" --catalog "$v/catalog.json" /dev/stdin
```

The output lists the agents it found, which branches ran and when, and `COULD NOT LOOK` for
any branch that did not. The matcher and the catalog are ml-engine's vendored copies, because
the collector is what matches. `classify` reads the schema from `schema/` beside its own
`bin/`, as a release lays them out, and needs jsonschema. `AI_DETECTION_SPEC_TELEMETRY=0`
matters: without it, `classify` sends a usage event about the payload it read, and this
payload comes from a customer's Mac.

## 06 · Smart Groups — Jamf Pro

Every group below reads *Arthur AI Inventory Status*. `no-cache` is the only value that makes
up the whole status, so it is the only one that takes **is**. The others are fragments of the
status line, so they need **like**.

| Group | Operator | Value | Means |
|---|---|---|---|
| AI inventory — not reporting | **is** | `no-cache` | The collector has never written on this Mac: osquery is missing, or the Policy has not run. Fix these first |
| AI inventory — degraded | **like** | `degraded` | At least one branch could not look. A Mac without Docker does not land here |
| Container scan blocked | **like** | `containers=timeout` | Docker answered, then stalled |
| A runtime nothing reads | **like** | `=unreadable:` | A container runtime this scan does not read, typically Podman. Its containers are not counted |
| A branch errored | **like** | `=error` | A query failed, usually because osquery is older than 5.18 |
| Serving a stale scan | **like** | `stale=` | No scan has succeeded for over a day. Read the Policy log |

**Build this group first.** It reads Jamf's own record, not an attribute:

| Group | Criteria | Operator | Value |
|---|---|---|---|
| Not reporting to Jamf | `Last Inventory Update` | **more than x days ago** | `30` |

Every other group reads a value the Mac submitted, so none of them can find a Mac that stopped
submitting. Exclude this group from Arthur's source with `exclude_groups`. Otherwise retired
Macs count against coverage forever. Thirty days is a starting point; set it far enough above
your recon interval that a laptop on holiday does not land in it.

## 07 · Roll out — Jamf Pro

1. **Start with a pilot.** Pick a dozen Macs across your osquery versions, including at least
   one heavy Docker user.
2. **Run Update Inventory,** then read the status attribute across the pilot. `no-cache` means
   the collector did not run.
3. **Expand in stages.** Every inventory submission carries the ~24 KB value. That is about
   250 MB per full sync at 10,000 Macs.

If a Mac's payload is over the 256 KB budget, the Mac reports `ERROR:oversize:<bytes>` in place
of its inventory. That happens at about 10,000 rows, roughly ten times a heavily loaded Mac.
Size depends on how much software is installed, chiefly applications and Homebrew packages,
not on how many agents there are.

## 08 · Reading the status — Jamf Pro

The status line holds:

1. a first token: `ok`, `degraded` or `no-cache`
2. the scan time
3. the row count
4. one `branch=outcome` token per query branch

The outcome vocabulary is upstream's
([`deployment.md`](https://github.com/arthur-ai/ai-detection-spec/blob/main/osquery/docs/deployment.md#statustxt));
this table says what to do about each:

| Outcome | Means | Do |
|---|---|---|
| `ok` | The branch ran | Nothing |
| `absent` | There is no container runtime to read | Nothing |
| `unhealthy:000` | Docker's socket exists, but nothing answered within 15s | Nothing, if no user is logged in. If Docker is running on the Mac, investigate |
| `unhealthy:500` | Docker's daemon is up, but its engine is not serving | Restart Docker |
| `timeout:<n>` | Docker answered, then stalled and was stopped after `<n>`s | Restart Docker |
| `unreadable:<runtime>` | A runtime this scan does not read is installed | Nothing to fix; its containers are not counted |
| `error` | The query failed, usually on a table this osquery version lacks | Upgrade osquery (section 00) |
| `no-cache` | No scan has ever been written | Check osquery (section 00), then the Policy log |
| `stale=NNh` | The scan shown is NNh old, because later runs failed | The data is still valid; read the Policy log to see why the collector is failing |

`ERROR:oversize:<bytes>` replaces the inventory value when the payload is over budget. The
status attribute still shows which branches ran.

**Docker Desktop runs per user.** When no user is logged in, a root scan records
`containers=absent` or `unhealthy:000` even on a Mac that has Docker. Expect container coverage
to follow working hours.

**A failed Policy next to healthy attributes is expected.** When a run fails, the collector
keeps the last good scan and exits non-zero. Read the Policy log to see why this run failed,
and `stale=NNh` to see how old the data is.

## 09 · Access for the Arthur collector — Jamf Pro

Arthur polls the Jamf Pro API. Nothing connects to Arthur, and no Mac talks to it.

1. Go to *Settings → System → API roles and clients → API Roles → New* and grant the privilege
   *Read Computers*. If the source will be limited to certain groups, also grant
   *Read Smart Computer Groups* and *Read Static Computer Groups*.
2. Under *API Clients → New*, give the client that role, enable it, and generate a client
   secret.
3. In Arthur, add a **Jamf Pro** discovery source with these fields:
   - `base_url`: your Jamf URL, which must use `https://`
   - `client_id` and `client_secret`
   - optionally, `include_groups` and `exclude_groups`: comma-separated computer group names

If a group is in both lists, it is excluded. A group name that matches no group fails the scan.
Without that check, a mistyped exclude would scan exactly the Macs it was meant to leave out.

Each scan reads the Macs whose inventory changed since the previous scan, found by
`general.reportDate`. So a Mac's findings arrive within a day of its recon. Before a tenant's
first scan, run `ml-engine/scripts/jamf_smoke.py`, which tries the shipped client against the
tenant without changing anything.

## 10 · Rollback — terminal

Unscope the Policy, then on each Mac:

```bash
rm -rf /var/lib/arthur
```

That is everything the script leaves behind. If you deployed the package instead:

```bash
launchctl bootout system/com.arthur.ai-discovery
rm -f /Library/LaunchDaemons/com.arthur.ai-discovery.plist
rm -rf /usr/local/arthur /var/lib/arthur /var/log/arthur-ai-discovery.log
```

Then disable or delete both Extension Attributes. Disabling keeps their past values on the
computer records; deleting discards them.

When upgrading the package, always run `bootout` before `bootstrap`. `launchctl` does not
reload a changed plist for a label that is already loaded. If you skip it, the old definition
keeps running and the new files go unused, with no error.
