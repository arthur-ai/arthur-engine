# AI Inventory on EC2 instances

Deploying the `osquery-ai-discovery` endpoint to Linux instances on AWS: a systemd timer runs
the collector, and a reporter writes what it wrote as the instance's **SSM custom inventory**,
which the SSM Agent uploads and the SSM API serves to Arthur. Nothing connects to the instance,
and the instance connects to nothing it does not already reach.

**One template, deployed as a stack or a StackSet.**
[`deploy/arthur-ai-discovery.cfn.yaml`](../../deploy/arthur-ai-discovery.cfn.yaml) holds:
- an SSM document whose script installs osquery, `collect-linux.sh`, the reporter, the two
  systemd units and a drop-in that points the unit at the reporter, and enables the timer
- the State Manager association that runs it on every managed instance
- by parameter, the inventory association that uploads what the reporter writes, and the role
  Arthur's source assumes

Deploy it as a stack in each region of one account (section 02), or as a StackSet across an
organization (section 09). The collector is the one a Compute Engine VM runs; only the reporter
differs.

> **Run from the template on 2026-10-23.** It ran as a self-managed StackSet in one account,
> across us-east-2 and us-east-1, on a fresh Amazon Linux 2023 instance (`t3.small`) and a
> Windows Server 2022 instance. Measured:
> - Each region's stack created the document and both associations. Only us-east-1's stack
>   created the role.
> - The install ran on the Linux instance within a minute of SSM managing it, and was skipped
>   on Windows.
> - The timer's first run collected 809 rows, and the stack's inventory association uploaded
>   them in 3 parts.
> - A scan through the template's role, with its external ID, decoded the instance. It
>   published a `~/.claude` as a `claude-code` record and counted the Windows instance as
>   `unsupported-platform`. With a wrong external ID, STS refused the role.
> - A pin bump re-ran the install at once. Every file kept its sha256 and the timer was not
>   restarted. Drift detection found every resource in sync.
>
> **Run on four instances.** On 2026-10-20 the same script ran from an `AWS-RunShellScript`
> association targeted by a tag. It ran on fresh Amazon Linux 2023 and Ubuntu 24.04 instances,
> each on x86_64 (`t3.small`) and arm64 (`t4g.small`). Measured:
> - The install association ran twice in a row on each. The second run changed nothing: the
>   timer was not restarted and every file kept its sha256.
> - Each instance collected, uploaded through section 03's association, and was decoded by the
>   Arthur collector.
> - A Session Manager login's `ssm-user` is an ordinary `/etc/passwd` account. osquery's `users`
>   table lists it, and a `~/.claude` in its home was published as a `claude-code` record.
>
> The same day's first run found that the script failed on Ubuntu under `sh` (section 02).

| | |
|---|---|
| Target | EC2 instances on Amazon Linux 2023 or Ubuntu 24.04, x86_64 or arm64. Amazon Linux 2 installs too, through yum, but is not yet run on an instance ([Constraints](../architecture.md#constraints)). A host with no osquery and no apt-get, dnf or yum fails the install, naming why, and counts toward `MaxErrors`: install osquery 5.18+ on it first |
| Requires | osquery 5.18+, an SSM-managed instance, an inventory association that gathers custom inventory, IMDS enabled. No interpreter |
| Per-instance cost | as on Compute Engine (`gce.md`), off the reporting path. 6s and 1.4s of CPU per run on a `t3.small`; 2.0s to 2.1s of CPU on a `t4g.small`. Burstable instances in standard credit mode are not yet measured |
| Payload | of the 256 KB budget, cut into parts of 4,096 characters. On fresh headless instances: ~11 KB on Amazon Linux 2023 (809 rows on x86_64, 796 on arm64) and ~17 KB on Ubuntu 24.04 (1,075 rows on x86_64, 1,106 on arm64) |

## What SSM custom inventory gives, measured

Checked on 2026-10-16 on `t3.small` Amazon Linux 2023 instances, SSM Agent 3.3.5390.0, in a
sandbox account, reading back through `ssm:ListInventoryEntries` — the API Arthur reads.
AWS's own figures are in its
[custom inventory](https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html)
and [quotas](https://docs.aws.amazon.com/general/latest/gr/ssm.html) pages.

| Question | Result |
|---|---|
| Value cap | **Exactly 4,096 characters.** 4,096 is uploaded and read back with an identical sha256. 4,097 is refused **by the agent, silently**: it logs `value length (4097) exceeded the limit (4096)` to `/var/log/amazon/ssm/errors.log`, skips that file, uploads the others, and the association reports `Success`. Hence the reporter's parts of 4,096, which `test/lint.sh` holds it to |
| Per type | AWS's quotas page says "200 KB"; **it does not cap data**. One type of 262,144 characters in 64 entries, and one of 614,400 in 150, both uploaded and read back with an identical sha256 |
| Per node, per day | **5,000 KB, enforced.** The upload that crosses it fails with `TotalSizeLimitExceededException: ... inventory data size of 5098 KB exceeded the daily limit of 5000 KB`, the association reports `Failed`, and the previous values are still served. The 5,098 KB matched the uploads whose content had changed |
| Unchanged content | Reported again on every association run, and `CaptureTime` advances, though the values do not change. It did not count toward the daily cap: the 5,098 KB above was the changed uploads alone. `CaptureTime` says the agent ran, never that the collector did |
| Cadence | the inventory association's schedule — not the timer's |
| A credential on the instance | none added: the SSM Agent uploads with the instance's SSM permissions (`AmazonSSMManagedInstanceCore` includes `ssm:PutInventory`) |
| Stopped | `DescribeInstanceInformation` leaves the instance out; its inventory is still served, unchanged |
| Terminated | its inventory is still served — so the collector leaves terminated instances out by their EC2 state |
| Before anything is uploaded | `ListInventoryEntries` answers `InvalidTypeNameException: ... Custom:ArthurAIDiscovery is not defined` until some instance in the account has uploaded the type |
| A real payload | 809 rows, 11,376 bytes framed (4% of the budget) in 3 parts, plus the status; 6s and 1.4s of CPU per run, cold, all thirteen branches `ok` |

## 00 · Prerequisites — account

| Requirement | Why | Set with |
|---|---|---|
| SSM-managed instances | The SSM Agent uploads the inventory | An instance profile with `AmazonSSMManagedInstanceCore`, or [Default Host Management Configuration](https://docs.aws.amazon.com/systems-manager/latest/userguide/fleet-manager-default-host-management-configuration.html). The agent is preinstalled on Amazon Linux 2023 and Ubuntu; RHEL needs it installed |
| A route to the SSM endpoints | The agent's uploads | The managed instance already has one: a NAT, or the `ssm`, `ssmmessages` and `ec2messages` VPC endpoints |
| IMDS enabled | The reporter learns the instance id from IMDSv2; the inventory directory is named for it | On by default (`HttpEndpoint=enabled`). A hop limit of 1 is enough: the reporter runs on the host |
| A route to `pkg.osquery.io` and `pkg.osquerypackages.com` | The osquery package; the first redirects to the second | A NAT, or your own mirror |
| A route to wherever the five files are hosted | The install script fetches them by URL (section 01) | As above, or a mirror named by `FileBaseUrl` |
| Rights to deploy a stack that creates an IAM role | The template creates the role Arthur assumes (section 07) | `CAPABILITY_NAMED_IAM`, as in section 02 |

## 01 · Render the template — terminal

The install script downloads each file by URL and refuses it unless its sha256 matches, so the
template names exact bytes. Render it at a release tag of this repository:

```bash
git clone https://github.com/arthur-ai/arthur-engine && cd arthur-engine/integrations/endpoint-ai-discovery
git checkout REF
tools/build-collector.py --check && test/lint.sh        # the tree you are pinning is the built one
tools/render-cfn-template.sh REF > arthur-ai-discovery.cfn.yaml
```

**Pin a tag or a commit, never a branch.** Every run of the association downloads the files at
`REF`, so a ref that moves breaks every instance. The renderer reads each checksum from git at
`REF`, not from the working tree. The instances download from GitHub at `REF`, so it must be
pushed there.

**To serve the files from a mirror,** set `FileBaseUrl` in section 02 to an `https://` URL.
Under it, the five files must sit at their paths in this tree:
- `dist/collect-linux.sh`
- `deploy/report-ssm-inventory.sh`
- `deploy/arthur-ai-discovery.service`
- `deploy/arthur-ai-discovery.timer`
- `deploy/arthur-ai-discovery.service.d/ec2.conf`

The checksums still pin them.

**Give each ref its own path on the mirror,** such as `https://mirror.example.com/endpoint-ai-discovery/REF`,
and keep the old path serving until the pin change has finished. If one path is overwritten in
place, its bytes and the template's checksums change at different moments, and every run in
between fails its checksum. A new path is also what makes a pin change reach the association,
which runs at once only when its `baseUrl` changes.

## 02 · Deploy the stack — terminal

First settle `CreateInventoryAssociation` with section 03's check, region by region: it has no
default. `CREATE_INVENTORY` below is `true` where the region has no inventory association, and
`false` where it has one. Then deploy in each region the fleet runs in:

```bash
aws cloudformation deploy --region REGION --stack-name arthur-ai-discovery \
  --template-file arthur-ai-discovery.cfn.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides CreateInventoryAssociation=CREATE_INVENTORY \
      ArthurPrincipalArn=ARTHUR_PRINCIPAL_ARN ExternalId=EXTERNAL_ID MemberRoleRegion=ROLE_REGION
```

`ROLE_REGION` is one of the regions you deploy to: its stack creates the role.

| Creates | Where | Turned off by |
|---|---|---|
| The document `arthur-ai-discovery-install`, and the association `arthur-ai-discovery` that runs it daily | Every region's stack | — |
| The association `arthur-ai-discovery-inventory`: `AWS-GatherSoftwareInventory`, custom inventory on, hourly | Every region's stack | `CreateInventoryAssociation=false` |
| The role `arthur-ai-discovery`, which Arthur's source assumes (section 07) | Only the stack in `MemberRoleRegion`, since IAM is global | Leaving `ArthurPrincipalArn` empty |

Both associations target every instance SSM manages in the region. When SSM starts managing a
new instance, the associations pick it up and run on it at once. **`MemberRoleRegion` must be a
region you deploy to**, or no stack creates the role.

**The script is POSIX `sh`, not bash.** The document's `aws:runShellScript` step runs it with
`sh`, which on Ubuntu is dash. A `set -o pipefail` there fails every run with
`Illegal option -o pipefail` (measured 2026-10-20 on Ubuntu 24.04). `test/lint.sh` holds the
template's script to dash.

**The script is idempotent,** since State Manager re-applies it on its schedule:
- It downloads only a file whose installed bytes are not the pinned ones.
- It verifies every download before it replaces any file, so a failed download leaves the
  last install whole.
- A run that changes nothing leaves the timer as it was.
- On a freshly booted Ubuntu instance, cloud-init or unattended-upgrades may hold apt's locks.
  The script waits up to ten minutes for them.

**The script travels in a document of its own, not `AWS-RunShellScript`**, so that a mirror's
URL reaches it as the document's `baseUrl` parameter, held to a pattern that admits no shell
metacharacter, rather than spliced into the script. A `platformType` precondition skips every
instance but Linux.

**Windows is skipped, not failed.** State Manager counts a Windows instance as `Skipped`, so it
never counts toward `MaxErrors`. The measurement is in
[architecture's Constraints](../architecture.md#constraints).

**A hybrid-activated node is left alone.** A node whose id starts `mi-`, such as an on-premises
server, is not an EC2 instance. Arthur's source does not read it, and the reporter finds no
IMDS there, so the script exits at once and installs nothing. State Manager reports that run as
a success.

**The install rolls out a tenth of the fleet at a time.**
- `MaxConcurrency 10%` runs the install on a tenth of the instances at a time.
- `MaxErrors 10%` stops State Manager sending it to further instances once more than a tenth of
  them have failed. Runs already under way at that point still finish, and some of them may
  fail too, so a bad pin can fail on more than a tenth of the fleet before the rollout stops.

**To change the pin**, render the template at the new ref and run the same `deploy` again.
`deploy` keeps the value of any parameter you leave out. CloudFormation adds a version of the
document and makes it the default. The association names the ref in its `baseUrl`, so it is
updated too, and an updated association runs at once, at its own `MaxConcurrency`. The new
pin reaches every instance in that run, not on the next day's.

**A document named `arthur-ai-discovery-install` that the region already holds fails the
stack.** Document names are unique in a region. Delete it and any association that runs it
first.

## 03 · The inventory association — terminal

**An instance runs one inventory association. With two, neither runs.** So first find out
whether the fleet already has one:

```bash
aws ssm list-associations \
  --association-filter-list key=Name,value=AWS-GatherSoftwareInventory
aws ssm describe-instance-associations-status --instance-id INSTANCE \
  --query 'InstanceAssociationStatusInfos[?Name==`AWS-GatherSoftwareInventory`]'
```

- **None exists:** deploy with `CreateInventoryAssociation=true`, and the stack creates one on
  every instance.
- **One exists:** deploy with `false`. The existing association has to gather custom inventory
  and target every instance, since an instance outside its targets never uploads a report.
  Update it as shown below. Quick Setup's host-management association takes priority over any
  other; whether it gathers custom inventory is not documented and **not yet measured**.
- **Several exist, each on part of the fleet:** deploy with `false`, turn custom inventory on in
  each, and leave their targets alone. Widening one over another's instances gives those
  instances two, and then neither runs.

**An update replaces the whole association.** `update-association` sets every field it is not
given to null, the document name, its parameters, the schedule and the rate controls included.
So read the association, change what is needed, and send all of it back. This sets the targets
to every instance and, on an inventory association, turns custom inventory on. For one of
several inventory associations, drop the `.Targets` line:

```bash
ID=ASSOCIATION_ID
aws ssm describe-association --association-id "$ID" --query AssociationDescription --output json \
  | jq 'del(.Date, .InstanceId, .LastExecutionDate, .LastSuccessfulExecutionDate,
            .LastUpdateAssociationDate, .Overview, .Status, .TriggeredAlarms)
        | .Targets = [{Key: "InstanceIds", Values: ["*"]}]
        | if .Name == "AWS-GatherSoftwareInventory"
          then .Parameters.customInventory = ["Enabled"] else . end' > association.json
aws ssm update-association --cli-input-json file://association.json
```

The fields deleted are the ones `describe-association` reports and `update-association` does
not accept, so everything else goes back as it was. The update runs the association at once,
within its own `MaxConcurrency`.

**Hourly, and not faster, because of the daily cap.** Each run that finds new values uploads
them, and the 5,000 KB a day per instance is enforced (section above): a payload near the
256 KB budget, changing every hour, would cross it in the nineteenth hour, and the instance
would read as stale for the rest of the day. A real server's payload is a few percent of the
budget — 11 KB on the instance this was measured on — so hourly leaves a wide margin.

**Leave `files` and `windowsRegistry` at their defaults.** They take a JSON list of paths, and
a value such as `Disabled` fails every run of the association with `invalid character 'D'
looking for beginning of value`.

## 04 · Scope and roll out — terminal

Both associations target every instance SSM manages in the region, so being SSM-managed
(section 00) is the only switch, and Default Host Management Configuration makes that an
account setting rather than a per-instance one.

**No tag narrows the fleet, and no tag excludes an instance.** Discovery is for what nobody
opted in. An instance's owner can set its tags, so an opt-out tag would be a way to hide from
it; the only exclusions are on Arthur's source (section 07), set by whoever owns governance,
and counted. What an owner *can* do is stop the SSM Agent or detach its instance profile.
Arthur's source then counts the instance instead of publishing it as a clean machine:
`not-ssm-managed` once SSM no longer lists it as managed, and otherwise `never-reported`, or
`not-reported-in-window` once its last report is older than the lookback. A service control
policy can deny `ssm:DeregisterManagedInstance` and instance profile changes, which Compute
Engine has no equivalent of.

**To pilot on a handful first**, deploy with `TargetInstanceIds=i-…,i-…`, which narrows both of
the stack's associations. Then widen them by deploying again with `TargetInstanceIds='*'`.
`deploy` keeps a parameter's last value, so the widening has to name it. Across an
organization, pilot by deploying the StackSet to one account or OU first (section 09).

**When the first report arrives:** the timer's first run is 5 minutes after boot plus up to 10
of random delay, and the upload follows on the inventory association's next run, up to its
interval later.

## 05 · Prove it on one instance — terminal

```bash
aws ssm list-inventory-entries --instance-id INSTANCE \
  --type-name Custom:ArthurAIDiscovery --query 'Entries[].[Key,Part,Parts]' --output text
```

Each value — `inventory`, `status` — arrives as parts of at most 4,096 characters. To put them
back together and check them:

```bash
aws ssm list-inventory-entries --instance-id INSTANCE --type-name Custom:ArthurAIDiscovery \
  --output json \
  | python3 -c 'import hashlib,json,sys
parts = {}
for e in json.load(sys.stdin)["Entries"]:
    parts.setdefault(e["Key"], []).append(e)
for key, es in sorted(parts.items()):
    v = "".join(e["Value"] for e in sorted(es, key=lambda e: int(e["Part"])))
    ok = len(es) == int(es[0]["Parts"]) and hashlib.sha256(v.encode()).hexdigest() == es[0]["Sha256"]
    print(key, len(v), "chars", "ok" if ok else "INCOMPLETE", v[:120] if key == "status" else "")'
```

A page holds 50 entries; a payload over 50 parts needs `--starting-token` as well — the CLI
pages for you unless `--max-items` is set.

## 06 · Reading the status — and when an instance is not reporting

`status` carries the same vocabulary as on Compute Engine — read [`gce.md`](gce.md), section 05
— apart from `inventory=refused:<code>`, which this reporter cannot see: a refused upload shows
in the agent's log, not in the value. **Judge age from the status line's timestamp, never from
`CaptureTime`**, which dates the upload.

On the instance:

```bash
systemctl list-timers arthur-ai-discovery.timer        # scheduled?
systemctl status arthur-ai-discovery.service           # the last run's result
journalctl -u arthur-ai-discovery.service -n 50        # the collector's stderr, then the reporter's
sudo ls -l /var/lib/amazon/ssm/*/inventory/custom/        # the file the agent uploads
sudo tail -n 100 /var/log/amazon/ssm/amazon-ssm-agent.log   # the upload, or why it was refused
```

| The journal says | Cause |
|---|---|
| `cannot get an IMDSv2 token` | IMDS is disabled on the instance, or unreachable from the host |
| `no SSM Agent data directory` | The SSM Agent is not installed |
| `discover: no osqueryi found` | osquery is not installed; the status says `osquery=absent` |
| `wrote Custom:ArthurAIDiscovery for i-…` | The reporter did its part. If Arthur still sees nothing, the upload is the problem: `/var/log/amazon/ssm/errors.log` names a value the agent refused, which the association does not report, and the association's status names a refused upload, such as the daily cap |

## 07 · Access for the Arthur collector

The collector is an `aws_ec2` discovery source, in the Platform's Cloud class. Per region it
lists instances, lists the instances SSM manages, and reads each in-scope instance's
`Custom:ArthurAIDiscovery` entries. The least privilege is three actions, none of which can be
scoped to a resource:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["ec2:DescribeInstances", "ssm:DescribeInstanceInformation", "ssm:ListInventoryEntries"],
    "Resource": "*"
  }]
}
```

Grant these three, not `AmazonEC2ReadOnlyAccess` and `AmazonSSMReadOnlyAccess`. Those cover
them, but `ssm:Get*` also reads Parameter Store and `ec2:Describe*` instance user data, where
secrets are often kept. The source's `include_tags` and `exclude_tags` are the only scope there
is, set by whoever owns governance, and an instance they leave out is still counted as excluded
on every scan. A source with `regions` set to `all` also needs `ec2:DescribeRegions`, to ask
which regions the account has enabled.

The source takes an access key (`access_key_id`, `secret_access_key`), and a `role_arn` with an
optional `external_id` to assume with it. A source without a key uses the engine's own AWS
credentials — IRSA on EKS, say — only when the engine sets
`ARTHUR_ENGINE_AWS_EC2_ALLOW_DEFAULT_CREDENTIALS=true`; otherwise the scan fails and names the
fields.

**The template creates that role** when `ArthurPrincipalArn` is set:
- It holds the three actions above plus `ec2:DescribeRegions`.
- It trusts `ArthurPrincipalArn` only with `ExternalId`.
- `ArthurPrincipalArn` is the IAM user or role whose credential the source holds.

For one account, give the source:
- that principal's credential:
  - for an IAM user, its access key
  - for a role, such as the engine's IRSA role, no key: the engine's own credentials, with
    `ARTHUR_ENGINE_AWS_EC2_ALLOW_DEFAULT_CREDENTIALS=true`
- `role_arn` set to the stack's `MemberRoleArn` output
- `external_id` set to `ExternalId`

`test/lint.sh` holds the role's actions to the calls the collector makes.

**Every account in the organization.** Set `accounts` to `all`, or to a comma-separated list
of account IDs, and `regions` to `all` or a list. The source lists the organization's active
accounts (`organizations:ListAccounts`, from the management account or a delegated
administrator), assumes `arn:PARTITION:iam::ACCOUNT:role/MEMBER_ROLE_NAME` in each with the
source's `external_id`, as session `arthur-ai-discovery`, and asks each account for its enabled
regions. With `accounts` set, `external_id` is the member roles' and needs no `role_arn` of the
source's own.
`member_role_name` defaults to `arthur-ai-discovery`. The management account is treated like
any other. The member role is the template's, deployed to every account by section 09's
StackSet, and the credential the source holds needs this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "organizations:ListAccounts", "Resource": "*" },
    { "Effect": "Allow", "Action": "sts:AssumeRole", "Resource": "arn:aws:iam::*:role/arthur-ai-discovery" }
  ]
}
```

In another partition, the role ARN starts `arn:aws-us-gov:` or `arn:aws-cn:`. The named
regions choose the partition, and the scan asks STS,
Organizations and each account's enabled regions in a region every account there has enabled:
`us-east-1`, `us-gov-west-1` or `cn-north-1`. `regions: all` names none and is the `aws`
partition's; a fleet in another partition names its regions, and one source reaches one
partition. An account whose role cannot be assumed, a named region an account has not enabled,
or a region the role is refused, is a denied scope on the run, which Arthur shows as a degraded
source, and the scan reads the rest; refused everywhere, the run fails.

**Measured 2026-10-20 in the sandbox account**, with a role holding exactly the policy above,
trusted only with an external ID:
- Through `role_arn` and `external_id`, a scan read and decoded the region's tagged instance and
  published its record, as an administrator's scan did.
- CloudTrail records the `AssumeRole` under the session name `arthur-ai-discovery`.
- With a wrong external ID, STS refuses (`AccessDenied`) and the scan fails as
  `permission_denied`.

How the collector counts an instance that cannot report:

| Instance | Counted as |
|---|---|
| Running, but not managed by SSM | `not-ssm-managed`, and not read: nothing it holds can be current |
| Windows | `unsupported-platform` |
| No `Custom:ArthurAIDiscovery` entries | `never-reported` |
| Parts that do not reassemble, or a value over the budget | `inventory-incomplete` |
| A status line outside the scan's lookback — stopped, or its timer or uploads gone | `not-reported-in-window`, and not published |

A stopped instance is still read, and its status line decides. An instance still reporting but
failing keeps publishing its last good scan. An instance dated more than 15 minutes past the
scan's clock is published too, and the scan's log names it and how far ahead it is: fix its
time sync.

**Every instance counted is also listed**, by instance id, `Name` tag, `account/region` and
reason, with the time on its status line when it has one, under
`device_coverage.unreadable_devices`, up to 1,000 per run with the rest counted in
`unreadable_devices_truncated`. The instances a scan cannot see are where unmanaged AI sits,
so that list is the finding to work through, and an instance whose owner stopped the SSM Agent
is in it by name. No inventory value travels. Where the list can be read is in
[architecture.md](../architecture.md#what-the-collector-emits).

## 08 · Rollback — terminal

```bash
aws cloudformation delete-stack --region REGION --stack-name arthur-ai-discovery   # each region
# a StackSet (section 09): its instances first, then the set
aws cloudformation delete-stack-instances --stack-set-name arthur-ai-discovery \
  --deployment-targets OrganizationalUnitIds=OU_ID --regions REGION … --no-retain-stacks
aws cloudformation delete-stack-set --stack-set-name arthur-ai-discovery
# on each instance:
sudo systemctl disable --now arthur-ai-discovery.timer
sudo rm -rf /etc/systemd/system/arthur-ai-discovery.service.d
sudo rm -f /etc/systemd/system/arthur-ai-discovery.service /etc/systemd/system/arthur-ai-discovery.timer
sudo systemctl daemon-reload
sudo rm -rf /usr/local/arthur /var/lib/arthur
sudo rm -f /var/lib/amazon/ssm/*/inventory/custom/ArthurAIDiscovery.json
```

Deleting a stack deletes its associations, its document and its role, but not what the
association installed, hence the commands on each instance. If you turned custom inventory on
in an association of your own (section 03), turn it off there. SSM keeps the last upload for 30
days; `aws ssm delete-inventory` removes a custom type's data for the whole account, never for
one instance.

## 09 · Across the organization — terminal

A service-managed StackSet deploys the template to every account in the OUs you name, in each
region you name. It also deploys to each account that joins one of those OUs later.
- Run it from the management account, after `aws cloudformation activate-organizations-access`.
- Or run it from a delegated administrator for StackSets, adding `--call-as DELEGATED_ADMIN` to
  each command.

> **Not yet run against a real organization.** The template ran as a self-managed StackSet
> across two regions of one account (see the measurements at the top). Service-managed
> deployment to OUs, and auto-deployment to an account that joins one, have not run.

```bash
aws cloudformation create-stack-set --stack-set-name arthur-ai-discovery \
  --template-body file://arthur-ai-discovery.cfn.yaml --capabilities CAPABILITY_NAMED_IAM \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --parameters ParameterKey=CreateInventoryAssociation,ParameterValue=CREATE_INVENTORY \
               ParameterKey=ArthurPrincipalArn,ParameterValue=ARTHUR_PRINCIPAL_ARN \
               ParameterKey=ExternalId,ParameterValue=EXTERNAL_ID \
               ParameterKey=MemberRoleRegion,ParameterValue=us-east-1
aws cloudformation create-stack-instances --stack-set-name arthur-ai-discovery \
  --deployment-targets OrganizationalUnitIds=ROOT_OR_OU_ID \
  --regions us-east-1 us-east-2 eu-west-1 \
  --operation-preferences RegionConcurrencyType=PARALLEL,MaxConcurrentPercentage=25,FailureTolerancePercentage=10
```

`CREATE_INVENTORY` is `true` or `false`, chosen by OU as described below.
`FailureTolerancePercentage=10` stops the operation in a region once a tenth of its accounts
have failed, the way `MaxErrors` stops the install on a tenth of the instances.

**The management account is never a target of a service-managed StackSet**, even with the root
as the target. The source scans it like any other account, and without the role it reads as a
denied scope. Deploy the template there as a stack in each region (section 02).

**`MemberRoleRegion` must be one of `--regions`.** Each account's role is created once, by the
stack in that region. Without it, every account reads as a denied scope.

**`CreateInventoryAssociation` follows the OU, not the account.** An account that joins a target
OU later is deployed with the set's own value. An override reaches only the accounts in its
targets when it is made, never one that joins afterwards. The wrong value fails one of two ways:
- `true` in an account with its own inventory association gives its instances two, and then
  neither runs, the account's own included.
- `false` in an account with none uploads nothing, and Arthur counts each of its instances as
  `never-reported`, by name.

So split by OU, with section 03's check in each account:
- **OUs whose accounts all gather inventory already** get a StackSet of their own, set to
  `false`, under another `--stack-set-name`. Two sets must never reach the same account: the
  second's document fails on the first's name.
- **OUs whose accounts gather none** get a set with `true`.
- **An OU that mixes the two** gets a set with `false`, the failure Arthur shows by name. Override
  each account there that has no inventory association, once its instances exist, and again for
  each such account that joins later:

```bash
aws cloudformation update-stack-instances --stack-set-name arthur-ai-discovery \
  --deployment-targets OrganizationalUnitIds=OU_ID,Accounts=ACCOUNT_ID,AccountFilterType=INTERSECTION \
  --regions us-east-1 us-east-2 eu-west-1 \
  --parameter-overrides ParameterKey=CreateInventoryAssociation,ParameterValue=true
```

**An account that moves between two sets' OUs can end up with neither set's stack.** The new set
may deploy before the old one has removed its stack. The new stack then fails on the
document's name, and in `MemberRoleRegion` on the role's. Its instances then read as
`never-reported`, or the account as a denied scope. After a move, check the account's stack
instances, and once the old set's stack is gone, run the failed one again:

```bash
aws cloudformation list-stack-instances --stack-set-name arthur-ai-discovery \
  --stack-instance-account ACCOUNT_ID \
  --query 'Summaries[].[Region,Status,StatusReason]' --output text
aws cloudformation update-stack-instances --stack-set-name arthur-ai-discovery \
  --deployment-targets OrganizationalUnitIds=OU_ID,Accounts=ACCOUNT_ID,AccountFilterType=INTERSECTION \
  --regions us-east-1 us-east-2 eu-west-1
```

One set with per-account overrides has no such window.

**To change the pin**, render the template at the new ref and update the set. Name each
parameter with `UsePreviousValue`, or it returns to its default:

```bash
aws cloudformation update-stack-set --stack-set-name arthur-ai-discovery \
  --template-body file://arthur-ai-discovery.cfn.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=CreateInventoryAssociation,UsePreviousValue=true \
               ParameterKey=ArthurPrincipalArn,UsePreviousValue=true \
               ParameterKey=ExternalId,UsePreviousValue=true \
               ParameterKey=MemberRoleName,UsePreviousValue=true \
               ParameterKey=MemberRoleRegion,UsePreviousValue=true \
               ParameterKey=TargetInstanceIds,UsePreviousValue=true \
               ParameterKey=FileBaseUrl,UsePreviousValue=true \
  --operation-preferences RegionConcurrencyType=PARALLEL,MaxConcurrentPercentage=25,FailureTolerancePercentage=10
```

**Being SSM-managed is still the only switch.** The StackSet does not make instances
SSM-managed. Default Host Management Configuration does that per account and region, and Quick
Setup can turn it on across the organization. Arthur counts an instance that is not managed,
by name, as `not-ssm-managed` (section 07).
