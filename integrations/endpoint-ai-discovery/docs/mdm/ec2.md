# AI Inventory on EC2 instances

Deploying the `osquery-ai-discovery` endpoint to Linux instances on AWS: a systemd timer runs
the collector, and a reporter writes what it wrote as the instance's **SSM custom inventory**,
which the SSM Agent uploads and the SSM API serves to Arthur. Nothing connects to the instance,
and the instance connects to nothing it does not already reach.

**Five files and two associations.** A State Manager association installs osquery, drops
`collect-linux.sh`, the reporter, the two systemd units and a drop-in that points the unit at
the reporter, and enables the timer. The instance's inventory association uploads what the
reporter writes. The collector is the one a Compute Engine VM runs; only the reporter differs.

> **Run on four instances.** On 2026-10-20 sections 01 to 03 ran, from a pinned commit, on fresh
> Amazon Linux 2023 and Ubuntu 24.04 instances, each on x86_64 (`t3.small`) and arm64
> (`t4g.small`), with the install script in an `AWS-RunShellScript` association targeted by a
> tag. Section 02 now carries the same script in a document that skips Windows, and both
> associations target every managed instance; **that shape is not yet run**. Measured then:
> - Section 02's association ran twice in a row on each. The second run changed nothing: the
>   timer was not restarted and every file kept its sha256.
> - Each instance collected, uploaded through section 03's association, and was decoded by the
>   Arthur collector.
> - A Session Manager login's `ssm-user` is an ordinary `/etc/passwd` account. osquery's `users`
>   table lists it, and a `~/.claude` in its home was published as a `claude-code` record.
>
> The same day's first run found that the script failed on Ubuntu under `sh` (section 02).

| | |
|---|---|
| Target | EC2 instances on Amazon Linux 2023 or Ubuntu 24.04, x86_64 or arm64. Each of the four has run on an instance |
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
| A route to wherever the five files are hosted | The install script fetches them by URL (section 01) | As above, or host them in your own bucket |

## 01 · Pin the files — terminal

The install script downloads each file by URL and refuses it unless its sha256 matches, so the
association names exact bytes. Pin a commit of this tree:

```bash
git clone https://github.com/arthur-ai/arthur-engine && cd arthur-engine
COMMIT=$(git rev-parse HEAD)
cd integrations/endpoint-ai-discovery
tools/build-collector.py --check && test/lint.sh        # the tree you are pinning is the built one
shasum -a 256 dist/collect-linux.sh deploy/report-ssm-inventory.sh \
              deploy/arthur-ai-discovery.service deploy/arthur-ai-discovery.timer \
              deploy/arthur-ai-discovery.service.d/ec2.conf
echo "$COMMIT"
```

## 02 · The install association — terminal

Replace `COMMIT` and the five `SHA256_*` values with section 01's output. The script is
idempotent: State Manager re-applies it on its schedule, and a run that changes nothing leaves
the timer as it was.

**It is POSIX `sh`, not bash.** The `aws:runShellScript` step runs it with `sh`, which on
Ubuntu is dash: a `set -o pipefail` there fails every run with `Illegal option -o pipefail`
(measured 2026-10-20 on Ubuntu 24.04). Keep it free of bashisms when editing it.

```sh
# arthur-ai-discovery-install.sh
set -eu
BASE=https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/integrations/endpoint-ai-discovery
fetch() {  # path destination mode sha256
  curl -fsSL --retry 3 -o "$2.new" "$BASE/$1"
  echo "$4  $2.new" | sha256sum -c --quiet
  chmod "$3" "$2.new" && mv -f "$2.new" "$2"
}
if ! command -v osqueryi >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    curl -fsSL -o /etc/pki/rpm-gpg/RPM-GPG-KEY-osquery https://pkg.osquery.io/rpm/GPG
    curl -fsSL -o /etc/yum.repos.d/osquery-s3-rpm.repo https://pkg.osquery.io/rpm/osquery-s3-rpm.repo
    dnf install -y osquery
  else
    install -d -m 755 /etc/apt/keyrings
    curl -fsSL -o /etc/apt/keyrings/osquery.asc https://pkg.osquery.io/deb/pubkey.gpg
    echo "deb [signed-by=/etc/apt/keyrings/osquery.asc] https://pkg.osquery.io/deb deb main" \
      > /etc/apt/sources.list.d/osquery.list
    apt-get update -q && apt-get install -y -q osquery
  fi
fi
install -d -m 755 /usr/local/arthur /etc/systemd/system/arthur-ai-discovery.service.d
fetch dist/collect-linux.sh /usr/local/arthur/collect-linux.sh 755 SHA256_COLLECTOR
fetch deploy/report-ssm-inventory.sh /usr/local/arthur/report-ssm-inventory.sh 755 SHA256_REPORTER
fetch deploy/arthur-ai-discovery.service /etc/systemd/system/arthur-ai-discovery.service 644 SHA256_SERVICE
fetch deploy/arthur-ai-discovery.timer /etc/systemd/system/arthur-ai-discovery.timer 644 SHA256_TIMER
fetch deploy/arthur-ai-discovery.service.d/ec2.conf \
      /etc/systemd/system/arthur-ai-discovery.service.d/ec2.conf 644 SHA256_DROPIN
systemctl daemon-reload
systemctl enable --now arthur-ai-discovery.timer
```

**The script travels in a document of its own, not `AWS-RunShellScript`**, so that an
association targeting every instance can skip Windows. In a schema 2.2 document, a step whose
`platformType` precondition does not hold is skipped rather than failed. `AWS-RunShellScript`
would fail on every Windows instance, and each failure would count toward `--max-errors`.

```bash
jq -n --rawfile script arthur-ai-discovery-install.sh '{
  schemaVersion: "2.2",
  description: "Arthur endpoint AI discovery: osquery, the collector and its timer, on Linux",
  mainSteps: [{
    action: "aws:runShellScript", name: "install",
    precondition: { StringEquals: ["platformType", "Linux"] },
    inputs: { runCommand: [$script] }
  }]
}' > arthur-ai-discovery-install.json
aws ssm create-document --name arthur-ai-discovery-install --document-type Command \
  --document-format JSON --content file://arthur-ai-discovery-install.json
aws ssm create-association --association-name arthur-ai-discovery \
  --name arthur-ai-discovery-install \
  --targets 'Key=InstanceIds,Values=*' \
  --schedule-expression 'rate(1 day)' \
  --max-concurrency 10% --max-errors 10%
```

The document and the association are per region; create both in each region the fleet runs
in. An instance SSM starts managing later is picked up by the association, which runs on it at
once.

`--max-concurrency 10%` runs the install on a tenth of the instances at a time. `--max-errors
10%` stops State Manager sending it to further instances once more than a tenth of them have
failed. Runs already under way at that point still finish, and some of them may fail too, so a
bad pin can fail on more than a tenth of the fleet before the rollout stops. With
`--max-concurrency 1` the count is exact, at the cost of one instance at a time.

**To change the script**, update the document, then make the new version its default. The
association runs the document's default version, so each instance gets the change on the
association's next run; `start-associations-once` runs it now:

```bash
version=$(aws ssm update-document --name arthur-ai-discovery-install \
  --content file://arthur-ai-discovery-install.json --document-format JSON \
  --document-version '$LATEST' --query DocumentDescription.DocumentVersion --output text)
aws ssm update-document-default-version --name arthur-ai-discovery-install \
  --document-version "$version"
aws ssm start-associations-once --association-ids INSTALL_ASSOCIATION_ID
```

## 03 · The inventory association — terminal

**An instance runs one inventory association. With two, neither runs.** So first find out
whether the fleet already has one:

```bash
aws ssm list-associations \
  --association-filter-list key=Name,value=AWS-GatherSoftwareInventory
aws ssm describe-instance-associations-status --instance-id INSTANCE \
  --query 'InstanceAssociationStatusInfos[?Name==`AWS-GatherSoftwareInventory`]'
```

- **One exists:** it has to gather custom inventory and target every instance, since an
  instance outside its targets never uploads a report. Update it as shown after the next
  block. Quick Setup's host-management association takes priority over any other; whether it
  gathers custom inventory is not documented and **not yet measured**.
- **Several exist, each on part of the fleet:** turn custom inventory on in each, and leave
  their targets alone. Widening one over another's instances gives those instances two, and
  then neither runs.
- **None exists:** create one, on every instance.

```bash
aws ssm create-association --association-name arthur-ai-discovery-inventory \
  --name AWS-GatherSoftwareInventory \
  --targets 'Key=InstanceIds,Values=*' \
  --schedule-expression 'rate(1 hour)' \
  --parameters customInventory=Enabled
```

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

**To pilot on a handful first**, create both associations with
`--targets Key=InstanceIds,Values=i-…,i-…`, then widen each with section 03's update, which
changes only the targets. Never widen with `update-association --targets` alone: it sets the
association's parameters, schedule and rate controls to null.

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

**Every account in the organization.** Set `accounts` to `all`, or to a comma-separated list
of account IDs, and `regions` to `all` or a list. The source lists the organization's active
accounts (`organizations:ListAccounts`, from the management account or a delegated
administrator), assumes `arn:PARTITION:iam::ACCOUNT:role/MEMBER_ROLE_NAME` in each with the
source's `external_id`, as session `arthur-ai-discovery`, and asks each account for its enabled
regions. With `accounts` set, `external_id` is the member roles' and needs no `role_arn` of the
source's own.
`member_role_name` defaults to `arthur-ai-discovery`. The management account is treated like
any other. The credential the source holds needs `organizations:ListAccounts` and
`sts:AssumeRole` on the member role; the member role holds the three actions above plus
`ec2:DescribeRegions`, and trusts that credential. Deploy it to every account with a
CloudFormation StackSet. The named regions choose the partition, and the scan asks STS,
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
aws ssm delete-association --association-id INSTALL_ASSOCIATION_ID
aws ssm delete-association --association-id INVENTORY_ASSOCIATION_ID   # only if you created it
aws ssm delete-document --name arthur-ai-discovery-install
# on each instance:
sudo systemctl disable --now arthur-ai-discovery.timer
sudo rm -rf /etc/systemd/system/arthur-ai-discovery.service.d
sudo rm -f /etc/systemd/system/arthur-ai-discovery.service /etc/systemd/system/arthur-ai-discovery.timer
sudo systemctl daemon-reload
sudo rm -rf /usr/local/arthur /var/lib/arthur
sudo rm -f /var/lib/amazon/ssm/*/inventory/custom/ArthurAIDiscovery.json
```

Deleting an association does not remove what it installed, hence the commands on each
instance. SSM keeps the last upload for 30 days; `aws ssm delete-inventory` removes a custom
type's data for the whole account, never for one instance.
