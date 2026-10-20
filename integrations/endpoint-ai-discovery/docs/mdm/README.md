# Carrying the payload: what an MDM has to provide

`dist/collect.sh` and its Linux build `dist/collect-linux.sh` name no vendor: each runs on a
schedule, writes three files to `/var/lib/arthur/`, and stops. A carrier gets that script onto
the machine, reads two files back as custom attributes, and serves them over an API.

Supporting another is a runbook here and an API client in
`ml-engine/src/ml_engine/discovery/endpoint/<vendor>/`, or `discovery/cloud/<vendor>/` for a
cloud that lists its own VMs. The payload, the matching and the record shape are the same
whoever carried the string, so none of them changes.

## The four requirements

| | What it means | Jamf Pro | Compute Engine | EC2 |
|---|---|---|---|---|
| **Run a script on a schedule** | Run `collect.sh` as root, hourly to daily | A Policy running the script, or a package with a LaunchDaemon | OS policy + systemd timer | State Manager association + the same systemd timer |
| **A per-device string attribute** | Two of them, populated from the files. The evidence one reaches ~24 KB on a loaded Mac and must not be truncated | Extension Attribute (measured ≥ 1 MB) | Guest attribute, written by `deploy/report-guest-attributes.sh` (measured cap: exactly 262,144 bytes) | SSM custom inventory, written by `deploy/report-ssm-inventory.sh` and uploaded by the SSM Agent. **4,096 characters per value** (measured), so each value travels in parts |
| **An inventory API** | List devices with their attribute values, filtered and sorted on a per-device report date so a scan can page without losing records that shift mid-pagination | `/api/v1/computers-inventory` | `instances.aggregatedList` + `instances.getGuestAttributes`. **No report date** | `DescribeInstances` + `DescribeInstanceInformation` + `ListInventoryEntries`. **No report date**: `CaptureTime` dates the upload |
| **A stable device id** | Assigned by the MDM, not the hardware serial — VMs and refurbished units produce empty or duplicate serials | `general.managementId` | The instance's numeric `id` — never its name, which is reused on recreate | The instance id, `i-…` — never its `Name` tag |

A carrier missing the report date can still be supported, but only by full enumeration every
run: without one to filter and sort on there is no incremental scan, and the only way to tell a
machine that stopped reporting from one with nothing on it is the timestamp inside the value.
Compute Engine and EC2 are that case.

## Why a string

`arthur1.` + base64 of gzip of the rows is one line of ASCII, which survives every MDM's
idea of a custom attribute. The 256 KB budget exists so the endpoint's own loud failure
fires before any vendor's unobserved one. See [`../architecture.md`](../architecture.md).

## Runbooks

- [Jamf Pro](jamf-pro.md)
- [Compute Engine](gce.md)
- [EC2](ec2.md)
