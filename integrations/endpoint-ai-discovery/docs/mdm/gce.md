# AI Inventory on Compute Engine VMs

Deploying the `osquery-ai-discovery` endpoint to Linux VMs on Google Cloud: a systemd timer runs
the collector, and a reporter publishes what it wrote to the VM's own **guest attributes**,
where the Compute Engine API serves them to Arthur. Nothing connects to the VM, and the VM
connects to nothing new.

**Four files and one OS policy.** VM Manager installs osquery, drops `collect-linux.sh`, the
reporter and two systemd units, and enables the timer. The reporter does the job a Jamf
Extension Attribute does by `cat`-ing a file, so the collector is the same one a Mac runs, built
for Linux.

The policy is one file, [`deploy/arthur-ai-discovery.os-policy.yaml`](../../deploy/arthur-ai-discovery.os-policy.yaml).
Sections 01 to 03 deploy it with gcloud. **With Terraform, section 09 replaces them**: a module
that deploys the same file to every project and zone of a fleet, or through one VM Manager
policy orchestrator at a folder or an organization.

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
names exact bytes. `tools/render-os-policy.sh` pins the policy to one ref of this repository:
each file's URL at that ref, and the sha256 of the bytes the ref holds. Pin a release tag, which
CI has passed:

```bash
git clone https://github.com/arthur-ai/arthur-engine && cd arthur-engine/integrations/endpoint-ai-discovery
tools/render-os-policy.sh REF > arthur-ai-discovery.yaml
```

The checksums are read out of git, not off the working tree, so they are the bytes
`raw.githubusercontent.com` serves at `REF`. A ref that is not a tag is pinned to its commit,
because a branch moves. To host the files yourself instead, copy the four files anywhere the VMs
can reach, keep the same checksums, and change the four URLs.

## 02 · The OS policy assignment — terminal

[`deploy/arthur-ai-discovery.os-policy.yaml`](../../deploy/arthur-ai-discovery.os-policy.yaml)
installs osquery from its apt repository, drops the collector, the reporter and the two units,
and enables the timer, on VMs labelled `arthur-ai-discovery=enabled`, 10% of them every five
minutes. Section 01 rendered it:

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

Start with a handful, then widen: the policy's `rollout` changes at most 10% of the targeted VMs
every five minutes.

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

The collector is a `gcp_compute_engine` discovery source, in the Platform's Cloud class. It
lists instances, reads each in-scope VM's `arthur/` namespace, and reads a project's
`enable-guest-attributes` default when a VM does not set its own: `compute.instances.list`,
`compute.instances.getGuestAttributes` and `compute.projects.get`. `roles/compute.viewer`
includes all three; a custom role holding only those three is the least privilege, and one
without `compute.projects.get` works only if every VM sets the flag itself.

The source's `service_account_key` is that account's JSON key. A source without one uses the
engine's own Application Default Credentials (Workload Identity on GKE, say) only when the
engine sets `ARTHUR_ENGINE_GCP_COMPUTE_ENGINE_ALLOW_ADC=true`; otherwise the scan fails and
names the field.

A VM whose `enable-guest-attributes` is not `TRUE`, on the VM or on its project when the VM
does not set it, is counted as `guest-attributes-disabled` and its values are not read:
the API keeps serving them after the setting is turned off, so they cannot be current.

A VM whose status line (section 05) shows no report within the scan's lookback window,
stopped or with its timer removed, is counted as `not-reported-in-window` and not published,
so its agents go stale on the Platform as a Mac's do when it stops checking in. A VM still
reporting but failing keeps publishing its last good scan.

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

## 09 · With Terraform — terminal

[`deploy/terraform/`](../../deploy/terraform/) deploys the same policy file, with the project
settings from section 00. It reads the policy rather than restating it, and pins each file to
the copy in its own package, so the module at a ref deploys that ref's collector.

```hcl
module "arthur_ai_discovery" {
  source = "git::https://github.com/arthur-ai/arthur-engine.git//integrations/endpoint-ai-discovery/deploy/terraform?ref=REF&depth=1"

  arthur_engine_ref = "REF" # the same ref: the VMs download the files at it
  projects          = ["my-project"]
  zones             = ["us-central1-a", "us-central1-b"]
  reader            = "serviceAccount:arthur-discovery@my-project.iam.gserviceaccount.com"
}

# project_ids and include_labels for the source in section 07
output "arthur_source" {
  value = module.arthur_ai_discovery.arthur_source
}
```

| Creates | Where | Turned off by |
|---|---|---|
| The OS policy assignment | Every project × zone | — |
| `osconfig.googleapis.com` | Every project; left enabled on destroy | `enable_apis = false` |
| `enable-osconfig=TRUE`, `enable-guest-attributes=TRUE` | Every project's metadata, so every VM's OS Config agent turns on; the policy still reaches only the label | `project_metadata = false`, then set them per VM |
| `roles/compute.viewer` for Arthur's credential | Every project | Leaving `reader` unset |

Then label the VMs, wherever they are defined. It takes Terraform 1.5 and the Google provider
6.33 or later.

**The ref is pinned twice, and the plan checks they agree.** It downloads each file at
`arthur_engine_ref` and fails unless the bytes match the module's own copy. So a `?ref=` bumped
without `arthur_engine_ref`, or the reverse, fails the plan rather than every VM's checksum.
`file_base_url` points the VMs at a mirror instead. `verify_file_urls = false` skips the
download, for a machine running Terraform that cannot reach the URLs the VMs use.

**Source it from git**, as above, or by a relative path into a checkout of this repository. The
module reads files beside it in this tree. An absolute local path copies only the module's own
directory, and the plan fails naming the missing policy file. `depth=1` makes the download a
shallow clone, measured at 39 MB in 6s. It takes a tag or a branch: with a bare commit `init`
fails, `Remote branch … not found`, so drop `depth=1` to pin one.

What differs from the gcloud path:

- **Every file lands at 755.** The Google provider makes an assignment's file permissions
  output-only, so the API's default applies. The scripts need it. systemd warns that the units
  are marked executable and loads them.
- **The apply does not wait for the rollout.** A pin bump re-rolls every labelled VM at the
  policy's pace, which on a fleet outlasts the provider's timeout. Follow it in VM Manager's
  compliance view, then section 04.
- **Destroying the module deletes the assignments and both metadata keys**, project-wide. It
  leaves what the policy installed; section 08's commands remove that from each VM.
- **Project metadata Terraform already manages** with `google_compute_project_metadata`, which
  owns every key, takes the two keys there instead. Set `project_metadata = false`, or the two
  resources undo each other on every apply.

### Across a folder or an organization

`orchestrator = { folder = "FOLDER_NUMBER" }`, or `{ organization = "ORG_NUMBER" }`, replaces
the assignments with one
[VM Manager policy orchestrator](https://cloud.google.com/compute/vm-manager/docs/os-policies/about-policy-orchestrator).
It creates the same assignment in every project and zone in its scope — `projects`, and every
project under `include_folders`, in `zones` — and keeps them in step with the policy. It also
sets the file modes, 755 for the scripts and 644 for the units, which an assignment through
Terraform cannot.

> **Not yet run against a real folder or organization.** The module's tests check what it
> renders; whether VM Manager accepts the orchestrator and rolls it out is not yet measured.
> Prove it on a test folder first.

Once per folder, Google's
[prerequisites](https://cloud.google.com/compute/vm-manager/docs/os-policies/orchestrator-prerequisites):
the service agents and their roles, which takes `roles/resourcemanager.folderAdmin`.

```bash
gcloud beta services identity create --service=osconfig.googleapis.com --folder=FOLDER_NUMBER
gcloud beta services identity create --service=progressiverollout.googleapis.com --folder=FOLDER_NUMBER
for agent in osconfig:osconfig.serviceAgent osconfig-rollout:osconfig.rolloutServiceAgent \
             progrollout:progressiverollout.serviceAgent; do
  gcloud resource-manager folders add-iam-policy-binding FOLDER_NUMBER \
    --member="serviceAccount:service-folder-FOLDER_NUMBER@gcp-sa-${agent%%:*}.iam.gserviceaccount.com" \
    --role="roles/${agent#*:}"
done
```

For an organization, the same with `--organization=ORG_NUMBER`,
`gcloud organizations add-iam-policy-binding` and `service-org-ORG_NUMBER@…`, which takes
`roles/resourcemanager.organizationAdmin`. Then:

- **A quota project.** Calls at a folder or an organization bill one: in the `provider "google"`
  block, `billing_project = "QUOTA_PROJECT"` and `user_project_override = true`, with the OS
  Config API enabled in that project.
- **VPC Service Controls.** Inside a perimeter, the rollout service agent needs an ingress rule
  for `osconfig.googleapis.com`, or the orchestrator fails to create assignments in those
  projects.
- **Projects reached through `include_folders`** get neither the API nor the metadata from this
  module, and Arthur's source reads only the projects it lists. `arthur_source` lists `projects`
  alone.

Google documents that the orchestrator runs an iteration every six hours, finds projects added
to its scope, and replaces an orchestrated assignment that someone edits by hand.

**Deleting an orchestrator leaves its assignments enforcing.** To remove them, apply with
`action = "DELETE"`. Wait for that iteration to finish
(`gcloud compute os-config policy-orchestrators describe arthur-ai-discovery --folder=FOLDER_NUMBER --billing-project=QUOTA_PROJECT`),
then remove the module.
