# Carrying the payload: what an MDM has to provide

`dist/collect.sh` names no vendor: it runs on a schedule, writes three files to
`/var/lib/arthur/`, and stops. An MDM gets that script onto the Mac, reads two files back
as custom attributes, and serves them over an API.

Supporting another is a runbook here and an API client in
`ml-engine/src/ml_engine/discovery/endpoint/<vendor>/`. The payload, the matching and the
record shape are the same whoever carried the string, so none of them changes.

## The four requirements

| | What it means | Jamf Pro |
|---|---|---|
| **Run a script on a schedule** | Install and invoke `collect.sh` as root, hourly or thereabouts | Package policy + LaunchDaemon |
| **A per-device string attribute** | Two of them, populated by a script that `cat`s a file. The evidence one reaches ~21 KB on a loaded Mac and must not be truncated | Extension Attribute (measured ≥ 1 MB) |
| **An inventory API** | List devices with their attribute values, filtered and sorted on a per-device report date so a scan can page without losing records that shift mid-pagination | `/api/v1/computers-inventory` |
| **A stable device id** | Assigned by the MDM, not the hardware serial — VMs and refurbished units produce empty or duplicate serials | `general.managementId` |

An MDM missing the third can still be supported, but only by full enumeration every run:
without a report date to filter and sort on there is no incremental scan, and without
one per device there is no way to tell a Mac that stopped reporting from a Mac with
nothing on it.

## Why a string

`arthur1.` + base64 of gzip of the rows is one line of ASCII, which survives every MDM's
idea of a custom attribute. The 256 KB budget exists so the endpoint's own loud failure
fires before any vendor's unobserved one. See [`../architecture.md`](../architecture.md).

## Runbooks

- [Jamf Pro](jamf-pro.md)
