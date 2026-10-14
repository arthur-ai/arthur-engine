# AI Inventory on Compute Engine VMs

Deploying the `osquery-ai-discovery` endpoint to Linux VMs on Google Cloud: a systemd timer runs
the collector, and a reporter publishes what it wrote to the VM's own **guest attributes**,
where the Compute Engine API serves them to Arthur. Nothing connects to the VM, and the VM
connects to nothing new.

**Four files and one OS policy.** VM Manager installs osquery, drops `collect-linux.sh`, the
reporter and two systemd units, and enables the timer. The reporter does the job a Jamf
Extension Attribute does by `cat`-ing a file, so the collector is the same one a Mac runs, built
for Linux.

| | |
|---|---|
| Target | Compute Engine VMs on Debian 12, Ubuntu 24.04 or Rocky Linux 9 — the families upstream proves the Linux artifact on |
| Requires | osquery 5.18+, VM Manager, guest attributes enabled. No interpreter |
| Per-VM cost | ~8s and 1.3s of CPU per run on an `e2-small`, off the reporting path |
| Attribute value | ~10 KB on a headless Debian 12 VM, of a 256 KB budget — **which on Compute Engine is the platform's own cap** |

## What guest attributes give, measured

Checked on 2026-10-03 on an `e2-small` Debian 12 VM with no service account and no external IP,
reading back through `gcloud compute instances get-guest-attributes` — the API Arthur reads.

| Question | Result |
|---|---|
| Value cap | **Exactly 262,144 bytes.** One byte more is refused with HTTP 400, `Maximum value of 262144 bytes allowed (262145found )` — loud, never a truncation. The collector's own budget is the same number, so `ERROR:oversize:<bytes>` fires first, and `test/lint.sh` fails if the budget rises |
| Read-back integrity | Values of 16 KB to 256 KB read back with identical sha256 |
| A credential on the VM | None needed to write: the metadata server is local to the VM |
| Reboot; stop then start | Values survive with identical sha256 |
| While stopped | The API still serves every value — so a stopped VM's last report reads as current unless its timestamp is checked |
| `enable-guest-attributes=FALSE` | Inside the VM, PUT and GET return HTTP 403 `Guest attributes endpoint access is disabled.` The API keeps serving the old values |
| Suspend and resume | **Not measured** |

## 00 · Prerequisites — project

| Requirement | Why | Set with |
|---|---|---|
| OS Config API | VM Manager applies the OS policy | `gcloud services enable osconfig.googleapis.com` |
| `enable-osconfig=TRUE` | The OS Config agent acts on policies only with it | Instance or project metadata |
| `enable-guest-attributes=TRUE` | Without it the reporter's writes are refused with 403 and nothing is reported | Instance or project metadata. **The OS policy cannot set it**: it runs inside the VM, and changing the VM's own metadata would need a credential there |
| A service account attached to the VM | VM Manager signs its agent's requests with it. **It needs no IAM role**, and nothing of Arthur's uses it — the guest-attribute write needs no credential at all | `--service-account` at create time |
| A route to `pkg.osquery.io` and `pkg.osquerypackages.com` | The osquery package; the first redirects to the second | Cloud NAT, an external IP, or your own mirror |
| A route to wherever the four files are hosted | The OS policy fetches them by URL (section 01) | As above, or host them in your own bucket |
| Private Google Access, on a VM with no external IP | The OS Config agent talks to Google APIs | Subnet setting |

The OS Config agent is preinstalled on the Debian, Ubuntu and Rocky public images.

## 01 · Pin the files — terminal

The OS policy downloads each file by URL and refuses it unless its sha256 matches, so a policy
names exact bytes. Pin a commit of this tree:

```bash
git clone https://github.com/arthur-ai/arthur-engine && cd arthur-engine
COMMIT=$(git rev-parse HEAD)
cd integrations/endpoint-ai-discovery
tools/build-collector.py --check && test/lint.sh        # the tree you are pinning is the built one
shasum -a 256 dist/collect-linux.sh deploy/report-guest-attributes.sh \
              deploy/arthur-ai-discovery.service deploy/arthur-ai-discovery.timer
echo "$COMMIT"
```

Each file is then at
`https://raw.githubusercontent.com/arthur-ai/arthur-engine/$COMMIT/integrations/endpoint-ai-discovery/<path>`.
To host them yourself instead, copy the four files anywhere the VMs can reach and keep the same
checksums.

## 02 · The OS policy assignment — terminal

Replace `COMMIT` and the four `SHA256_*` values with section 01's output.

```yaml
# arthur-ai-discovery.yaml
osPolicies:
  - id: arthur-ai-discovery
    mode: ENFORCEMENT
    resourceGroups:
      - inventoryFilters:
          - osShortName: debian
          - osShortName: ubuntu
        resources:
          - id: osquery-repo
            repository:
              apt:
                archiveType: DEB
                uri: https://pkg.osquery.io/deb
                distribution: deb
                components:
                  - main
                gpgKey: https://pkg.osquery.io/deb/pubkey.gpg
          - id: osquery
            pkg:
              desiredState: INSTALLED
              apt:
                name: osquery
          # A file resource writes into its directory and does not create it.
          - id: install-dir
            exec:
              validate:
                interpreter: SHELL
                script: if [ -d /usr/local/arthur ]; then exit 100; else exit 101; fi
              enforce:
                interpreter: SHELL
                script: mkdir -p -m 755 /usr/local/arthur && exit 100
          - id: collector
            file:
              path: /usr/local/arthur/collect-linux.sh
              state: CONTENTS_MATCH
              permissions: '755'
              file:
                remote:
                  uri: https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/dist/collect-linux.sh
                  sha256Checksum: SHA256_COLLECTOR
          - id: reporter
            file:
              path: /usr/local/arthur/report-guest-attributes.sh
              state: CONTENTS_MATCH
              permissions: '755'
              file:
                remote:
                  uri: https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/deploy/report-guest-attributes.sh
                  sha256Checksum: SHA256_REPORTER
          - id: service
            file:
              path: /etc/systemd/system/arthur-ai-discovery.service
              state: CONTENTS_MATCH
              permissions: '644'
              file:
                remote:
                  uri: https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.service
                  sha256Checksum: SHA256_SERVICE
          - id: timer
            file:
              path: /etc/systemd/system/arthur-ai-discovery.timer
              state: CONTENTS_MATCH
              permissions: '644'
              file:
                remote:
                  uri: https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery/deploy/arthur-ai-discovery.timer
                  sha256Checksum: SHA256_TIMER
          # NeedDaemonReload too, not only is-active: after a unit file changes the timer is
          # still active, and without a reload systemd keeps running the old definition.
          - id: timer-enabled
            exec:
              validate:
                interpreter: SHELL
                script: |
                  for u in arthur-ai-discovery.service arthur-ai-discovery.timer; do
                    [ "$(systemctl show -p NeedDaemonReload --value "$u")" = no ] || exit 101
                  done
                  systemctl is-enabled --quiet arthur-ai-discovery.timer \
                    && systemctl is-active --quiet arthur-ai-discovery.timer && exit 100
                  exit 101
              enforce:
                interpreter: SHELL
                script: systemctl daemon-reload && systemctl enable --now arthur-ai-discovery.timer && exit 100
instanceFilter:
  inclusionLabels:
    - labels:
        arthur-ai-discovery: enabled
rollout:
  disruptionBudget:
    percent: 10
  minWaitDuration: 300s
```

```bash
gcloud compute os-config os-policy-assignments create arthur-ai-discovery \
  --location=ZONE --file=arthur-ai-discovery.yaml
```

An assignment is per zone; create one in each zone the fleet runs in. **Rocky Linux** takes the
same resources with osquery's yum repository in place of the apt one — upstream proves the
artifact there, and this runbook has not yet been run on it.

## 03 · Scope and roll out — terminal

The assignment targets VMs labelled `arthur-ai-discovery=enabled`, so the label is the switch:

```bash
gcloud compute instances add-metadata VM --zone=ZONE \
  --metadata=enable-osconfig=TRUE,enable-guest-attributes=TRUE
gcloud compute instances add-labels VM --zone=ZONE --labels=arthur-ai-discovery=enabled
```

Start with a handful, then widen: `rollout` above changes at most 10% of the targeted VMs every
five minutes.

**When the first report arrives**, measured 2026-10-12 on Debian 12:

| Labelled | Policy applied | First report |
|---|---|---|
| At creation | 43s after the VM was created | 14.5 min after boot: `OnBootSec` (5 min) plus the random delay (up to 10) |
| An already-running VM (up 7 min) | 14s after the label | 1 min 24s after the label: `OnBootSec` had passed, so only the random delay |

## 04 · Prove it on one VM — terminal

```bash
gcloud compute instances get-guest-attributes VM --zone=ZONE --query-path=arthur/
```

**Verify — two keys.** From the run that proved this runbook, 2026-10-12, `e2-small`, Debian 12,
osquery 5.23.1, vendored ref `v0.12.2`:

```
NAMESPACE  KEY        VALUE
arthur     inventory  arthur1.H4sICHTZ...                       9,816 bytes, 623 rows
arthur     status     ok 2026-10-12T12:58:28Z rows=623 browser=ok containers=absent desktop-linux=ok filesystem-linux=ok jetbrains=ok native-messaging-linux=ok packages=ok packages-linux=ok ports=ok running=ok runtime-linux=ok systemd=ok vscode=ok
```

Thirteen branches on Linux. On a headless server `browser`, `desktop-linux` and
`native-messaging-linux` read `ok` with no rows — looked, nothing there — and `containers=absent`
is correct on a VM with no container runtime. To decode the inventory by hand:

```bash
gcloud compute instances get-guest-attributes VM --zone=ZONE --query-path=arthur/inventory \
    --format='value(value)' \
  | python3 -c 'import base64,gzip,json,sys
v=sys.stdin.read().strip()
print(len(json.loads(gzip.decompress(base64.b64decode(v[8:])))),"rows")'
```

**The failure states, as that VM reported them through the same API:**

| Done on the VM | `arthur/inventory` | `arthur/status` | The unit |
|---|---|---|---|
| osquery removed, after a good scan | the last good scan, unchanged | `ok 2026-10-12T12:58:28Z … failed=2026-10-12T12:59:40Z osquery=absent` | failed |
| ...and `/var/lib/arthur` removed | `no-cache` | `no-cache failed=2026-10-12T12:59:52Z osquery=absent` | failed |
| `enable-guest-attributes=FALSE` | the last values, still served | the last values, still served | failed; the journal names the 403 |
| a value of 262,144 bytes, then one of 262,145 | the first accepted; the second refused, the first kept | `… inventory=refused:400` | failed on the second |

## 05 · Reading the status

`arthur/status` is the collector's status line — its vocabulary is upstream's, in
[`docs/deployment.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/deployment.md) —
plus what the reporter adds about the latest run:

| Value | Meaning | Action |
|---|---|---|
| first token `ok` / `degraded` | The last successful scan, and when it ran | `degraded` names the branch that could not look |
| first token `no-cache` | No scan has ever succeeded on this VM | Deployment problem: read the journal (section 06) |
| `failed=<UTC>` | The latest run failed, at that time. The inventory is the last good scan | Read the journal for why |
| `osquery=absent` | ...because the runner found no `osqueryi` | The OS policy's `osquery` resource has not applied: check the VM's compliance in VM Manager |
| `inventory=refused:<code>` | Compute Engine refused the inventory, so `arthur/inventory` still holds the previous value | Read the journal for the server's reason |

`arthur/inventory` is `arthur1.<base64(gzip(json))>`, `ERROR:oversize:<bytes>` when the payload
framed larger than the budget, or `no-cache` before any scan has succeeded. A key that is absent
is a VM the reporter never ran on, or one with guest attributes disabled since before its first
run.

**Judge age from the status line's timestamp, never from the read.** A stopped VM keeps serving
its last values, and so does one whose guest attributes were turned off after it reported. The
inventory dates itself too — every branch's `kind=scan` row carries its scan time in `ver`. The
inventory is written a moment before the status, so an inventory newer than the status beside it
is a run caught between the two writes, or, if it stays that way, one whose status write failed.

## 06 · When a VM is not reporting — on the VM

```bash
systemctl list-timers arthur-ai-discovery.timer        # scheduled?
systemctl status arthur-ai-discovery.service           # the last run's result
journalctl -u arthur-ai-discovery.service -n 50        # the collector's stderr, then the reporter's
```

| The journal says | Cause |
|---|---|
| `guest attributes are disabled on this VM (HTTP 403 ...)` | `enable-guest-attributes` is not `TRUE` on the VM or its project. Nothing can be published until it is |
| `cannot reach the metadata server` | Not a Compute Engine VM, or its metadata server is unreachable |
| `discover: no osqueryi found` | osquery is not installed; the status says `osquery=absent` |
| `arthur/inventory refused (HTTP 400 ...)` | The value was refused; the reason follows |
| `this scan failed its JSON check` | The scan ran but its payload did not parse; discover's reason is the line above. The last good scan is kept |

## 07 · Access for the Arthur collector

The collector lists instances and reads each one's `arthur/` namespace:
`compute.instances.list` and `compute.instances.getGuestAttributes`. `roles/compute.viewer`
includes both (checked 2026-10-03); a custom role holding only those two is the least privilege.

## 08 · Rollback — terminal

```bash
gcloud compute os-config os-policy-assignments delete arthur-ai-discovery --location=ZONE
gcloud compute instances remove-labels VM --zone=ZONE --labels=arthur-ai-discovery
# on each VM:
sudo systemctl disable --now arthur-ai-discovery.timer
sudo rm -f /etc/systemd/system/arthur-ai-discovery.service /etc/systemd/system/arthur-ai-discovery.timer
sudo systemctl daemon-reload
sudo rm -rf /usr/local/arthur /var/lib/arthur
```

Deleting the assignment stops enforcing it; it does not remove what it installed, hence the
commands on each VM. Removing the timer stops new writes; the values already written stay
readable — removing them is not something this tree has measured.
