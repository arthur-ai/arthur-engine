# Quick start

Each deployment has three parts:

1. osquery on each machine.
2. A scheduled script that scans the machine and writes the result to a file.
3. The platform you already manage the machines with, which carries that file to Arthur.

Nothing connects to the machine, and no Arthur credential is stored on it.

- [Try it on one Mac](#try-it-on-one-mac): needs only osquery, and installs nothing
- [Macs managed by Jamf Pro](#macs-managed-by-jamf-pro)
- [Compute Engine VMs](#compute-engine-vms)
- [EC2 instances](#ec2-instances)

Each path links to its full runbook, which covers prerequisites, troubleshooting and rollback.

## Try it on one Mac

Install [osquery](https://osquery.io/downloads) 5.18 or later. Nothing else is needed.

```bash
git clone --depth 1 https://github.com/arthur-ai/arthur-engine
cd arthur-engine/integrations/endpoint-ai-discovery
sudo ARTHUR_OUT_DIR=/tmp/arthur dist/collect.sh
```

This is the same script that runs across a fleet, and it installs nothing. To check it:

```bash
cat /tmp/arthur/status.txt                        # starts with ok or degraded
python3 -m json.tool /tmp/arthur/inventory.json   # what it found
```

On Linux, run `dist/collect-linux.sh`. The Jamf runbook's
[section 05](mdm/jamf-pro.md#05--prove-it-on-one-mac--the-mac) explains the three files, and
its [section 08](mdm/jamf-pro.md#08--reading-the-status--jamf-pro) explains each status
outcome.

## Macs managed by Jamf Pro

Full runbook: [jamf-pro.md](mdm/jamf-pro.md).

1. **Deploy osquery 5.18 or later.** Upload the `.pkg` from
   [osquery.io/downloads](https://osquery.io/downloads) and install it with a Policy
   ([section 00](mdm/jamf-pro.md#00--install-osquery--jamf-pro)).
2. **Add the collector.** Go to *Settings → Computer Management → Scripts → New* and paste
   all of `dist/collect.sh`. Take it from a release tag of this repository.
3. **Schedule it.** Create a Policy with trigger *Recurring Check-in* and frequency
   *Once every day*. Add the script and scope the Policy to a few pilot Macs
   ([section 02](mdm/jamf-pro.md#02--run-the-collector-on-a-schedule--jamf-pro)).
4. **Add two Extension Attributes** that read what the collector writes:
   [Arthur AI Inventory](mdm/jamf-pro.md#03--the-inventory-attribute--jamf-pro) and
   [Arthur AI Inventory Status](mdm/jamf-pro.md#04--the-status-attribute--jamf-pro).
5. **Check one pilot Mac.** On the Mac, run:

   ```bash
   sudo jamf policy    # runs the collector; the log ends with its status line
   sudo jamf recon     # submits inventory, which runs both attributes
   ```

   In Jamf, the Mac's *Arthur AI Inventory* value should start with `arthur1.`, and its
   *Arthur AI Inventory Status* value should start with `ok` or `degraded`.
6. **Connect Arthur.** Create a Jamf API client whose role has *Read Computers*. In Arthur,
   add a Jamf Pro discovery source with your Jamf URL and the client's ID and secret
   ([section 09](mdm/jamf-pro.md#09--access-for-the-arthur-collector--jamf-pro)).
7. **Expand to more Macs in stages.** First build the
   [Smart Groups](mdm/jamf-pro.md#06--smart-groups--jamf-pro) that show which Macs cannot
   collect.

## Compute Engine VMs

Full runbook: [gce.md](mdm/gce.md). The OS policy targets Debian 12 and Ubuntu 24.04.

1. **Apply the Terraform module.** It does four things:
   - enables the OS Config API
   - sets the project metadata that VM Manager and guest attributes need
   - creates the OS policy assignment in each zone
   - grants Arthur's service account `roles/compute.viewer`

   ```hcl
   module "arthur_ai_discovery" {
     source = "git::https://github.com/arthur-ai/arthur-engine.git//integrations/endpoint-ai-discovery/deploy/terraform?ref=REF&depth=1"

     arthur_engine_ref = "REF" # the same release tag
     projects          = ["my-project"]
     zones             = ["us-central1-a"]
     reader            = "serviceAccount:arthur-discovery@my-project.iam.gserviceaccount.com"
   }

   output "arthur_source" {
     value = module.arthur_ai_discovery.arthur_source
   }
   ```

   Replace `REF` with a release tag of this repository, never a branch. If a project already
   sets `enable-osconfig` or `enable-guest-attributes`, read
   [section 09](mdm/gce.md#09--with-terraform--terminal) before applying. To deploy without
   Terraform, use gcloud as in [sections 00 to 03](mdm/gce.md#00--prerequisites--project).
2. **Check the VMs can install it.** Each VM needs a service account attached (it needs no
   roles). It also needs a route to the osquery package repository and to GitHub
   ([section 00](mdm/gce.md#00--prerequisites--project)).
3. **Label the VMs to cover.** The label is what turns discovery on for a VM.

   ```bash
   gcloud compute instances add-labels VM --zone=ZONE --labels=arthur-ai-discovery=enabled
   ```

4. **Check one VM.** A new VM reports within about 15 minutes of boot. A VM that was already
   running reports a few minutes after it is labelled.

   ```bash
   gcloud compute instances get-guest-attributes VM --zone=ZONE --query-path=arthur/
   ```

   You should see two keys: `inventory`, starting with `arthur1.`, and `status`, starting with
   `ok` or `degraded`. If a key is missing or reads `no-cache`, follow
   [section 06](mdm/gce.md#06--when-a-vm-is-not-reporting--on-the-vm).
5. **Connect Arthur.** Add a Compute Engine discovery source. Set its `project_ids` and
   `include_labels` from the `arthur_source` output, and give it the service account's JSON
   key ([section 07](mdm/gce.md#07--access-for-the-arthur-collector)). To scan every project
   under an organization or a folder instead, set `organization_id` or `folder_ids`.

## EC2 instances

Full runbook: [ec2.md](mdm/ec2.md). Instances must be managed by SSM and run Amazon Linux 2023
or Ubuntu 24.04.

1. **Pin the files.** Pin a commit of this repository and record the checksums of the five
   files it installs ([section 01](mdm/ec2.md#01--pin-the-files--terminal)).
2. **Create the install association.** It installs osquery, the collector and its timer on
   instances tagged `arthur-ai-discovery=enabled`
   ([section 02](mdm/ec2.md#02--the-install-association--terminal)).
3. **Make sure custom inventory is gathered.** An instance runs only one inventory
   association. If one already exists, update it rather than adding a second
   ([section 03](mdm/ec2.md#03--the-inventory-association--terminal)).
4. **Tag the instances to cover:**

   ```bash
   aws ec2 create-tags --resources INSTANCE --tags Key=arthur-ai-discovery,Value=enabled
   ```

5. **Check one instance.** Wait for the timer's first run and the next inventory upload
   ([section 05](mdm/ec2.md#05--prove-it-on-one-instance--terminal)):

   ```bash
   aws ssm list-inventory-entries --instance-id INSTANCE \
     --type-name Custom:ArthurAIDiscovery --query 'Entries[].[Key,Part,Parts]' --output text
   ```

6. **Connect Arthur.** Grant a credential the three read-only actions listed in
   [section 07](mdm/ec2.md#07--access-for-the-arthur-collector). Then add an EC2 discovery
   source with that credential and your regions. To scan every account in the organization,
   deploy the member role to each account and set `accounts` to `all`.

## Next

- **Roll out in stages.** Watch collection health as you go: on Jamf, use the
  [Smart Groups](mdm/jamf-pro.md#06--smart-groups--jamf-pro); on Compute Engine and EC2, the
  [status line](mdm/gce.md#05--reading-the-status).
- **Field reference.** Every discovery source field is listed in
  [standalone-discovery.md](../../../ml-engine/docs/standalone-discovery.md#sources).
- **Uninstalling.** Each runbook ends with a rollback section.
- **How it works.** See [architecture.md](architecture.md).
