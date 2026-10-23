# AI Inventory on Compute Engine VMs

A systemd timer runs `dist/collect-linux.sh`, and a reporter publishes what it wrote to the VM's
own **guest attributes**. The Compute Engine API serves those attributes to Arthur. Nothing
connects to the VM, and the VM connects to nothing new. The
[quick start](../quickstart.md#compute-engine-vms) is the short version of this runbook.

One OS policy,
[`deploy/arthur-ai-discovery.os-policy.yaml`](../../deploy/arthur-ai-discovery.os-policy.yaml),
does the install. It installs osquery and drops in four files: the collector, the reporter and
two systemd units. Then it enables the timer. Sections 01 to 03 deploy it with gcloud.
**Section 09 does the same with Terraform**, across every project and zone of a fleet, or
through a VM Manager policy orchestrator.

| | |
|---|---|
| Target | Debian 12 or Ubuntu 24.04, the families the OS policy selects |
| Requires | osquery 5.18 or later, VM Manager, and guest attributes enabled. No interpreter |
| Per-VM cost | ~8s and 1.3s of CPU per run on an `e2-small` |
| Attribute size | ~10 KB on a headless Debian 12 VM. The budget is 256 KB, **which is also Compute Engine's own cap** (exactly 262,144 bytes, measured) |

## 00 · Prerequisites — project

| Requirement | Why | Set with |
|---|---|---|
| OS Config API | VM Manager applies the OS policy | `gcloud services enable osconfig.googleapis.com` |
| `enable-osconfig=TRUE` | The OS Config agent acts on policies only with it | Instance or project metadata |
| `enable-guest-attributes=TRUE` | Without it, the reporter's writes are refused with 403 | Instance or project metadata. The OS policy cannot set it, because that would need a credential on the VM |
| A service account attached to the VM | VM Manager's agent signs its requests with it. **It needs no IAM role**; the guest-attribute write needs no credential | `--service-account` when you create the VM |
| A route to `pkg.osquery.io` and `pkg.osquerypackages.com` | Downloading the osquery package; the first redirects to the second | Cloud NAT, an external IP, or your own mirror |
| A route to wherever the four files are hosted | The OS policy downloads them by URL (section 01) | As above, or host them in your own bucket |
| Private Google Access, on a VM with no external IP | The OS Config agent calls Google APIs | Subnet setting |

The OS Config agent comes preinstalled on the Debian and Ubuntu public images.

## 01 · Pin the files — terminal

The OS policy downloads each file by URL and refuses it unless its sha256 matches.
`tools/render-os-policy.sh` pins the policy to one ref of this repository. It sets each file's
URL at that ref and the sha256 of the bytes the ref holds. Pin a release tag:

```bash
git clone https://github.com/arthur-ai/arthur-engine && cd arthur-engine/integrations/endpoint-ai-discovery
tools/render-os-policy.sh REF > arthur-ai-discovery.yaml
```

The checksums come from git, not from your working tree, so they match the bytes
`raw.githubusercontent.com` serves at `REF`. A ref that is not a tag is pinned to its commit,
because a branch moves. To host the files yourself, copy the four files anywhere the VMs can
reach, keep the same checksums, and change the four URLs.

## 02 · The OS policy assignment — terminal

```bash
gcloud compute os-config os-policy-assignments create arthur-ai-discovery \
  --location=ZONE --file=arthur-ai-discovery.yaml
```

The policy targets every VM in the zone whose OS Config agent is on, and updates 10% of them
every five minutes. An assignment covers one zone, so create one in each zone the fleet runs in.
The policy installs osquery from its apt repository, so it selects Debian and Ubuntu VMs
only; any other image is left alone.

## 03 · Scope and roll out — terminal

The assignment targets every VM in its zone, so the two metadata keys of section 00 are the
only switch. Set them on the project, and each VM takes them as its default:

```bash
gcloud compute project-info add-metadata --project=PROJECT \
  --metadata=enable-osconfig=TRUE,enable-guest-attributes=TRUE
```

**No label narrows the fleet, and no label excludes a VM.** Discovery is for what nobody opted
in, and a VM's owner can set its labels, so an opt-out label would be a way to hide from it.
The only exclusions are on Arthur's source (section 07), set by whoever owns governance, and
counted. An owner can still set `enable-osconfig=FALSE` or `enable-guest-attributes=FALSE` on
the VM itself, which overrides the project's default. Arthur's source then counts the VM
instead of publishing it as a clean machine: `guest-attributes-disabled` for the second key,
and `never-reported` for a VM the first kept from ever being installed.

**To pilot on a few VMs first**, replace `all: true` in the rendered policy with an
`inclusionLabels` block and label those VMs; with Terraform, set the module's `label`. Then put
`all: true` back. The policy's rollout paces the fleet either way: 10% of the targeted VMs every
five minutes.

On Debian 12 (measured, under a pilot label), the policy applied within a minute. A VM created
with the agent on first reported 14.5 minutes after boot: the timer waits 5 minutes after boot,
plus a random delay of up to 10. A VM that was already running reported about 1.5 minutes after
the policy reached it.

## 04 · Prove it on one VM — terminal

```bash
gcloud compute instances get-guest-attributes VM --zone=ZONE --query-path=arthur/
```

You should see two keys. This is from a Debian 12 `e2-small` with osquery 5.23.1 at vendored
ref `v0.12.2`:

```
NAMESPACE  KEY        VALUE
arthur     inventory  arthur1.H4sICHTZ...                       9,816 bytes, 623 rows
arthur     status     ok 2026-10-12T12:58:28Z rows=623 browser=ok containers=absent desktop-linux=ok filesystem-linux=ok jetbrains=ok native-messaging-linux=ok packages=ok packages-linux=ok ports=ok running=ok runtime-linux=ok systemd=ok vscode=ok
```

On a headless server, `browser`, `desktop-linux` and `native-messaging-linux` report `ok` with
no rows: they looked and found nothing. `containers=absent` is correct on a VM with no
container runtime. To count the rows in the inventory:

```bash
gcloud compute instances get-guest-attributes VM --zone=ZONE --query-path=arthur/inventory \
    --format='value(value)' \
  | python3 -c 'import base64,gzip,json,sys
v=sys.stdin.read().strip()
print(len(json.loads(gzip.decompress(base64.b64decode(v[8:])))),"rows")'
```

## 05 · Reading the status

`arthur/status` holds the collector's status line, whose vocabulary is upstream's
([`deployment.md`](https://github.com/arthur-ai/osquery-ai-discovery/blob/main/docs/deployment.md)).
The Jamf runbook's [outcome table](jamf-pro.md#08--reading-the-status--jamf-pro) says what to do
about each outcome. The reporter adds tokens about the latest run:

| Value | Means | Do |
|---|---|---|
| first token `ok` or `degraded` | When the last successful scan ran | `degraded` names the branch that could not look |
| first token `no-cache` | No scan has ever succeeded on this VM | Read the journal (section 06) |
| `failed=<UTC>` | The latest run failed at that time; the inventory is the last good scan | Read the journal |
| `osquery=absent` | The run found no `osqueryi` | The policy's `osquery` resource has not applied. Check the VM's compliance in VM Manager |
| `inventory=refused:<code>` | Compute Engine refused the inventory, so `arthur/inventory` still holds the previous value | Read the journal for the reason |

`arthur/inventory` holds one of three values:

- `arthur1.<base64(gzip(json))>`
- `ERROR:oversize:<bytes>`, when the payload is over budget
- `no-cache`, before any scan has succeeded

If the key is missing, the reporter has never run on the VM, or guest attributes were disabled
before its first run.

**Judge age from the status line's timestamp, never from when you read the value.** A stopped
VM keeps serving its last values, and so does a VM whose guest attributes were turned off after
it reported.

## 06 · When a VM is not reporting — on the VM

```bash
systemctl list-timers arthur-ai-discovery.timer        # scheduled?
systemctl status arthur-ai-discovery.service           # the last run's result
journalctl -u arthur-ai-discovery.service -n 50        # the collector's stderr, then the reporter's
```

| The journal says | Cause |
|---|---|
| `guest attributes are disabled on this VM (HTTP 403 ...)` | `enable-guest-attributes` is not `TRUE` on the VM or its project. Nothing can be published until it is |
| `cannot reach the metadata server` | This is not a Compute Engine VM, or its metadata server is unreachable |
| `discover: no osqueryi found` | osquery is not installed; the status shows `osquery=absent` |
| `arthur/inventory refused (HTTP 400 ...)` | The value was refused; the reason follows |
| `this scan failed its JSON check` | The scan ran but its output did not parse; the line above gives discover's reason. The last good scan is kept |

## 07 · Access for the Arthur collector

In Arthur, add a **Compute Engine** discovery source (`gcp_compute_engine`). Set
`project_ids`, or `organization_id` or `folder_ids` to scan every active project under them
(below), optionally `include_labels` or `exclude_labels`, and `service_account_key`. The two
label fields are the only scope there is, set by whoever owns governance, and a VM they leave
out is still counted as excluded. The key is a JSON key for an account with these
permissions:

- `compute.instances.list`
- `compute.instances.getGuestAttributes`
- `compute.projects.get`

`roles/compute.viewer` includes all three. A custom role with only these three is the least
privilege. Without `compute.projects.get`, the source works only if every VM sets
`enable-guest-attributes` itself, because that permission reads the project's default. A
source without a key uses the engine's own Application Default Credentials only when the engine
sets `ARTHUR_ENGINE_GCP_COMPUTE_ENGINE_ALLOW_ADC=true`.

**An organization or a folder as the scope.** `organization_id` is the organization's number,
`folder_ids` a comma-separated list of folder numbers; either may stand alone or beside
`project_ids`. The source lists every active project under them, folders walked, on every
scan, so a project created tomorrow is in scope tomorrow. The account needs
`resourcemanager.projects.list` and `resourcemanager.folders.list` on the organization or
folder (`roles/browser`), and `roles/compute.viewer` granted there rather than per project;
the Terraform module's `reader` grants per project only. Resource Manager bills the listing to
the credential's own project, so that project needs `cloudresourcemanager.googleapis.com`
enabled; without it every listing answers 403 `accessNotConfigured` and the run fails. A
project the account is refused is
a denied scope on the run, which Arthur shows as a degraded source, and the scan reads the
rest; refused every project, the run fails. A project without the Compute Engine API is
counted and skipped, since no VM can exist in it.

The source does not publish three kinds of VM:

- **`guest-attributes-disabled`**: `enable-guest-attributes` is not `TRUE` on the VM, or on its
  project when the VM does not set it. The API keeps serving old values after the setting is
  turned off, so they cannot be current.
- **`osconfig-disabled`**: nothing was ever written for the VM, and `enable-osconfig` is not
  `TRUE` on the VM, or on its project when the VM does not set it. The OS Config agent acts on
  no policy there, so the rollout can never install the collector. A VM that has reported
  keeps its own reasons, whatever the key says now. Without `compute.projects.get`, a VM that
  does not set the key itself is counted as `never-reported` instead.
- **`not-reported-in-window`**: the status line shows no report within the scan's lookback,
  for example because the VM is stopped or its timer was removed. Its agents go stale in
  Arthur.

A VM that still reports but is failing keeps publishing its last good scan. A VM dated more
than 15 minutes past the scan's clock is published too, with no record dated past the scan, and
the scan's log names it and how far ahead it is: fix its time sync, or its last values stay
current that much longer once it stops reporting.

Every VM the source could not read is also listed, as
`device_coverage.unreadable_devices`: instance id, name, `project/zone`, the reason, and the
time on its status line when it has one. The list holds 1,000 VMs per run; the rest are counted
in `unreadable_devices_truncated`. The VMs a scan cannot see are where unmanaged AI sits, so
that list is the finding to work through, and a VM whose owner turned the agent or guest
attributes off is in it by name. No attribute value travels. Where the list can be read is in
[architecture.md](../architecture.md#what-the-collector-emits).

## 08 · Rollback — terminal

```bash
gcloud compute os-config os-policy-assignments delete arthur-ai-discovery --location=ZONE
# on each VM:
sudo systemctl disable --now arthur-ai-discovery.timer
sudo rm -f /etc/systemd/system/arthur-ai-discovery.service /etc/systemd/system/arthur-ai-discovery.timer
sudo systemctl daemon-reload
sudo rm -rf /usr/local/arthur /var/lib/arthur
```

Deleting the assignment stops enforcing the policy but does not remove what it installed,
hence the commands on each VM. Values already written stay readable after the timer is
removed.

## 09 · With Terraform — terminal

[`deploy/terraform/`](../../deploy/terraform/) deploys the same policy file, with the project
settings from section 00. It needs Terraform 1.5 or later and the Google provider 6.33 or later.

```hcl
module "arthur_ai_discovery" {
  source = "git::https://github.com/arthur-ai/arthur-engine.git//integrations/endpoint-ai-discovery/deploy/terraform?ref=REF&depth=1"

  arthur_engine_ref = "REF" # the same ref: the VMs download the files at it
  projects          = ["my-project"]
  zones             = ["us-central1-a", "us-central1-b"]
  reader            = "serviceAccount:arthur-discovery@my-project.iam.gserviceaccount.com"
}

# project_ids for the source in section 07; include_labels is null unless `label` narrows a pilot
output "arthur_source" {
  value = module.arthur_ai_discovery.arthur_source
}
```

| Creates | Where | Turned off by |
|---|---|---|
| The OS policy assignment | Every project × zone | — |
| `osconfig.googleapis.com` | Every project; left enabled on destroy | `enable_apis = false` |
| `enable-osconfig=TRUE`, `enable-guest-attributes=TRUE` | Every project's metadata, as the default for VMs that do not set their own | Leaving a key out of `project_metadata` |
| `roles/compute.viewer` for Arthur's credential | Every project | Leaving `reader` unset |

Nothing per VM remains. `label` narrows the assignments to a pilot label (section 03); there
is no exclusion label.

**A VM's own metadata overrides the project's, key by key.** A VM with its own
`enable-osconfig=FALSE` gets nothing installed. A VM with its own
`enable-guest-attributes=FALSE` gets the install, but every report is refused, so Arthur counts
it as `guest-attributes-disabled`.

**Pin a tag, and name it twice.** The VMs download the files at `arthur_engine_ref` whenever
the policy is enforced, so the ref must not move: use a tag or a commit, never a branch. The
plan downloads each file at that ref and fails unless it matches the module's own copy. That
catches a `?ref=` bumped without `arthur_engine_ref`, or the reverse. `depth=1` needs a tag; to
pin a commit, drop `depth=1`. To have the VMs download from a mirror, set `file_base_url`. If
the machine running Terraform cannot reach the URLs, set `verify_file_urls = false`.

**Things to know before you apply:**

- **An existing metadata key fails the apply.** If a project already holds
  `enable-osconfig` or `enable-guest-attributes`, the apply fails with
  `key "enable-osconfig" already present in metadata for project …`. If every project already
  sets the key to `TRUE`, leave it out: `project_metadata = ["enable-guest-attributes"]`.
  Otherwise import it:

  ```hcl
  import {
    to = module.arthur_ai_discovery.google_compute_project_metadata_item.discovery["my-project/enable-osconfig"]
    id = "projects/my-project/meta-data/enable-osconfig"
  }
  ```

- **If Terraform already manages the project's metadata** with
  `google_compute_project_metadata`, add the two keys there and set `project_metadata = []`.
  Otherwise the two resources undo each other on every apply.
- **An assignment gcloud already created** under the same name and zone fails the apply with
  `Error 409`. Delete it first, or import it.
- **A local module source must keep the tree.** The module reads files beside it, so a local
  path must be relative, or name the tree before a `//`:
  `/src/arthur-engine/integrations/endpoint-ai-discovery//deploy/terraform`.
- **Every file lands at mode 755.** The Google provider cannot set file modes on an assignment.
  systemd warns that the units are marked executable, and loads them anyway.
- **The apply does not wait for the rollout.** Follow it in VM Manager's compliance view, then
  check a VM as in section 04.
- **Destroying the module deletes every metadata key it manages,** imported ones included.
  Without `enable-osconfig`, other OS policies and patch jobs stop on every VM that does not set
  the key itself. The module does not uninstall the collector from the VMs; section 08 does
  that.

### Across a folder or an organization

Set `orchestrator = { folder = "FOLDER_NUMBER" }` or `{ organization = "ORG_NUMBER" }` to
replace the assignments with one
[VM Manager policy orchestrator](https://cloud.google.com/compute/vm-manager/docs/os-policies/about-policy-orchestrator).
It creates the same assignment in every zone in `zones`, for each project in `projects` and
every project under `include_folders`. It keeps them in step with the policy and sets proper
file modes.

> **Not yet run against a real folder or organization.** The module's tests check what it
> renders, but not whether VM Manager accepts it. Try it on a test folder first.

Once per folder, set up Google's
[prerequisites](https://cloud.google.com/compute/vm-manager/docs/os-policies/orchestrator-prerequisites):
the service agents and their roles. This needs `roles/resourcemanager.folderAdmin`.

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

For an organization, make three changes:

- use `--organization=ORG_NUMBER` and `gcloud organizations add-iam-policy-binding`
- use `service-org-ORG_NUMBER@…` for the service agents
- hold `roles/resourcemanager.organizationAdmin` instead of the folder role

Then:

- **Set a quota project.** Calls at folder or organization level bill a quota project. In the
  `provider "google"` block, set `billing_project = "QUOTA_PROJECT"` and
  `user_project_override = true`. That project needs the OS Config, Compute Engine, Service
  Usage and Resource Manager APIs enabled.
- **VPC Service Controls:** inside a perimeter, the rollout service agent needs an ingress
  rule for `osconfig.googleapis.com`.
- **Projects reached through `include_folders`** get neither the API nor the metadata from this
  module. `arthur_source` lists only `projects`, so add the other projects to Arthur's source
  yourself.
- **Switching an existing deployment to an orchestrator** deletes its assignments in the same
  apply. Until the orchestrator creates its own, the VMs keep what is installed but nothing is
  enforced on them.

The orchestrator runs every six hours. It picks up new projects in scope and replaces
assignments edited by hand. **Deleting an orchestrator leaves its assignments enforcing.** To
remove them, apply with `action = "DELETE"` and wait for that run to finish:

```bash
gcloud compute os-config policy-orchestrators describe arthur-ai-discovery \
  --folder=FOLDER_NUMBER --billing-project=QUOTA_PROJECT
```

Then remove the module.
