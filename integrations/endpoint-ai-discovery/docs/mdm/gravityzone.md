# AI Inventory on Bitdefender GravityZone

GravityZone can run a command on an endpoint, but it cannot schedule a script or keep a
24 KB value on an endpoint (a label holds 64 characters). So the two halves of a carrier
are split: **your own tooling schedules the collector**, which writes
`/var/lib/arthur/inventory.ea` as it does for every other carrier, and **Arthur's scan asks
each online endpoint for that file** through GravityZone's Investigation API, with one
read-only command:

```bash
printf 'ARTHUR-%s\n' BEGIN; cat /var/lib/arthur/inventory.ea 2>/dev/null || printf 'no-cache'; printf '\nARTHUR-%s\n' END
```

The command is fixed in the engine; nothing you configure is put into it. It is
GravityZone's [`startCommandExecutionOnEndpoint`](https://www.bitdefender.com/business/support/en/77209-1566170-startcommandexecutiononendpoint.html),
which runs under the [Remote Shell](https://www.bitdefender.com/business/support/en/77209-111689-remote-shell.html)
prerequisites, and Remote Shell runs as a user with root privileges. So the API key that
starts it is a privileged credential: treat it like one, and get your security team's
sign-off before you create it.

> **Status: Beta, not yet run against a GravityZone tenant.** Built from Bitdefender's
> [Public API reference](https://www.bitdefender.com/business/support/en/77211-125277-public-api.html).
> What a tenant still has to confirm is listed in [Unverified](#unverified).

| | |
|---|---|
| Target | macOS and Linux endpoints managed by GravityZone with the BEST agent. Windows endpoints are listed and counted as `unsupported-platform`: the Windows collector writes no framed value |
| Requires | GravityZone Cloud with EDR or XDR plus the Remote Shell add-on (or Bitdefender MDR / MXDR), Remote Shell connection enabled in the endpoints' policy, a personal API key whose user has the Manage Networks and Advanced Investigation rights, osquery 5.18+ on the endpoint |
| Per-endpoint cost | The collector's own run, on your schedule. The scan adds one `cat` per endpoint per scan |
| Scan cost | Every scan lists every managed endpoint: GravityZone cannot filter on when an endpoint was last seen. Three to six API calls per online endpoint, spaced under GravityZone's default 10 requests a second per key; commands go out twenty at a time |

## 00 · Prerequisites — GravityZone

1. Your company meets Bitdefender's [Remote Shell prerequisites](https://www.bitdefender.com/business/support/en/77209-111689-remote-shell.html)
   (all but 2FA, which the API does not need):
   - a licence for a Bitdefender product with EDR or XDR plus the Remote Shell add-on, or
     Bitdefender MDR, MDR Plus, MXDR or MXDR Plus;
   - company type Customer, not managed by a Partner (unless MDR-onboarded);
   - **Remote Shell connection with endpoint** enabled in the endpoints' policy under
     *General → Agent → Communication* (enabling it reconfigures and updates the agent,
     which can take a few minutes);
   - endpoints able to reach DigiCert's CRL/OCSP servers, and, behind TLS inspection,
     `cloud*-wbs-endpoints.gravityzone.bitdefender.com` on 443.
2. osquery 5.18 or later on each endpoint, as for Jamf ([Jamf runbook, section 00](jamf-pro.md#00--install-osquery--jamf-pro)).

## 01 · Get the collector — terminal

As for Jamf ([section 01](jamf-pro.md#01--get-the-collector--terminal)): take
`dist/collect.sh` (macOS) and `dist/collect-linux.sh` (Linux) from a release tag.

## 02 · Run the collector on a schedule — your tooling

GravityZone does not deploy third-party scripts, so use what you already deploy with
(Intune, Ansible, a GPO-managed image, Munki, Chef, a golden image).

**macOS:** install `dist/collect.sh` with `deploy/com.arthur.ai-discovery.plist`; the
plist's header has the install commands. It runs at load and hourly.

**Linux:** install `dist/collect-linux.sh`, the systemd units and the GravityZone drop-in:

```bash
install -d -m 755 /usr/local/arthur /etc/systemd/system/arthur-ai-discovery.service.d
install -m 755 dist/collect-linux.sh /usr/local/arthur/collect-linux.sh
install -m 644 deploy/arthur-ai-discovery.service deploy/arthur-ai-discovery.timer /etc/systemd/system/
install -m 644 deploy/arthur-ai-discovery.service.d/gravityzone.conf /etc/systemd/system/arthur-ai-discovery.service.d/
systemctl daemon-reload && systemctl enable --now arthur-ai-discovery.timer
```

The drop-in replaces the unit's reporter with the collector itself: GravityZone reads the
file directly, so nothing is published.

## 03 · Prove it on one endpoint — the endpoint

```bash
ls -l /var/lib/arthur/        # inventory.ea (~24 KB), inventory.json, status.txt
head -c 8 /var/lib/arthur/inventory.ea; echo    # arthur1.
```

Then, in GravityZone Control Center, open a Remote Shell session to the same endpoint and
run the command above. It should print `ARTHUR-BEGIN`, one long `arthur1.` line and
`ARTHUR-END`. If it prints `no-cache`, the collector has not run there.

## 04 · Access for the Arthur collector — GravityZone

In Control Center, go to *My Account → API keys → Add* (a personal key: the scan
authenticates with HTTP Basic, and service API keys, which use an `X-API-Key` header, are
not supported yet). Enable the **Network** API (to list endpoints) and the **Investigation**
API (to run the command and read its output), and nothing else. The user who owns the key
needs the **Manage Networks** and **Advanced Investigation** rights
([getInvestigationFileUrl](https://www.bitdefender.com/business/support/en/77209-1565959-getinvestigationfileurl.html)). Copy the key; it is shown once. Copy the **Access URL** shown under *Control
Center API* on the same page, for example `https://cloudgz.gravityzone.bitdefender.com/api`.

In Arthur, add a Bitdefender GravityZone source with `access_url` set to that Access URL and
`api_key` set to the key. Test Connection lists endpoints and, within its two-minute
deadline, asks the first online ones for their value.

## 05 · Reading the coverage

A scan never fails for one endpoint. Each endpoint it could not read is listed in the run's
device coverage under a reason:

| Reason | What to do |
|---|---|
| `offline` | GravityZone reports the endpoint offline or suspended. It does so only for endpoints in a virtualization integration ([getManagedEndpointDetails](https://www.bitdefender.com/business/support/en/77211-128484-getmanagedendpointdetails.html)); a laptop that is off is asked anyway and ends as `command-timed-out` |
| `not-seen-in-window` | Its `lastSeen` is older than the scan's lookback. A lookback of `0` asks every endpoint |
| `unsupported-platform` | Windows. Not supported by this source yet |
| `command-refused` | GravityZone would not start the command there: check Remote Shell is enabled in that endpoint's policy and its BEST version |
| `command-failed` | GravityZone reports the task failed; the job log names its errorCode (for example -112 or -311, no disk space; -161, the agent needs updating) |
| `command-timed-out` | No output within five minutes, or GravityZone failed the task for exceeding its execution time (errorCode -99997) |
| `output-unreadable` | The output could not be downloaded, or did not hold the `ARTHUR-BEGIN`/`ARTHUR-END` block |
| `no-cache`, `malformed`, `oversize` | As for every carrier ([Jamf section 08](jamf-pro.md#08--reading-the-status--jamf-pro)): the collector has not run, or its value could not be read |

A refused key (401), a key without the Investigation API, or a command refused on every
endpoint fails the scan, because each is the key or the licence and not the fleet.

## Unverified

Only a GravityZone tenant can settle these. Each one is handled defensively in the
connector, and none of them changes what this runbook asks you to set up:

- The exact `enabledApis` name of the Investigation API in `getApiKeyDetails`, and whether
  `startCommandExecutionOnEndpoint` is available on-premises.
- The user and shell an API command runs as (Remote Shell sessions are root), the length of
  GravityZone's execution limit, and the size cap on output (errorCodes -1130 / -329 say
  one exists).
- The format of the output archive (the reference says only "archive containing the command
  output log"; Remote Shell file downloads from Linux are GPG-encrypted, which would read
  here as `output-unreadable`), and whether its URL needs the API key (the connector sends
  the key to the access URL's host and, on GravityZone Cloud, to other
  `*.gravityzone.bitdefender.com` hosts only).
- Whether each command raises an audit or incident entry in GravityZone (Remote Shell
  sessions are logged in the User activity log).
- Whether an endpoint's id survives an agent reinstall or re-image (a new id lists the
  machine's agents again under the new id).
- The access URLs of regions other than `cloudgz`.

## 06 · Rollback — your tooling and GravityZone

Delete the API key in *My Account → API keys*, then remove the collector with the tooling
that installed it (the plist's header has the macOS commands; on Linux, disable the timer
and remove `/usr/local/arthur`, the units and `/var/lib/arthur`).
