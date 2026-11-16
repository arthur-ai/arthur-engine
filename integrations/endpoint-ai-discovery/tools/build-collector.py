#!/usr/bin/env python3
"""Build dist/collect.sh, dist/collect-linux.sh and dist/collect-windows.ps1 around the
vendored bundler -- one file per platform, which is what an MDM or a VM policy deploys.

    tools/build-collector.py            write all three
    tools/build-collector.py --check    fail if one does not carry the vendored tree

THE SELF-EXTRACTING HALF IS UPSTREAM'S. It ships osquery/tools/bundle.py -- reproducible tar,
base64/gzip wrapping, the extraction preamble -- tested on its macOS and Linux runners. Do
not re-implement it here.

WHAT IS STILL OURS IS THE DRIVER, and it is the whole of what made the old file Arthur's:
/var/lib/arthur, the 15s cold-Docker ping bound, the keep-the-last-good-scan policy, the
`arthur1.` frame, the 256 KB cap and its ERROR:oversize reason, and the Jamf status line. None
of those is a fact about osquery, which is why upstream deleted `--framed` and offers a
--driver hook instead of a place to put them.

SO THE SEAM NOW READS: upstream packs bin/ and dist/ into one self-extracting script and runs
what it is given; this repo writes what it is given. `AI_DETECTION_SPEC_ROOT` is the interface --
the wrapper sets it to the extracted tree and runs the driver with it.

ONE THING GOT WORSE AND IT IS WORTH KNOWING. The macOS-only refusal is upstream's message now,
and it ends "build it with osquery/tools/bundle.py --platform" -- a sentence about a tool a
Jamf admin does not have. It still names the real cause (this bundle carries the darwin
artifact), it fires before anything is unpacked, and the alternative is a second platform
guard here, which is the duplication this change exists to remove.

WINDOWS IS THE SAME SEAM IN POWERSHELL. Upstream's runner there is bin/discover.ps1 and its
bundle is a PowerShell file, so the driver handed to it is PowerShell too: DRIVER_PS, the
same policy as DRIVER with one file fewer. It writes no inventory.ea, because the framed
value is what a carrier's attribute holds and no carrier reads a Windows machine yet.

NO CATALOG IN THE PAYLOAD, AND ONE CATALOG-DERIVED FILE CARRIED UNREAD. Upstream refuses the
catalog too, but only in its own main(); this builds through bundle.build() and so asserts what
may reach an endpoint itself, by name -- see ENDPOINT_FILES. The endpoint enumerates and
matches nothing -- see docs/architecture.md.
"""

import importlib.util
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "ai-detection-spec"
DIST = ROOT / "dist"
# ONE BUILD PER PLATFORM. Upstream's bundle carries one platform's artifact and refuses the
# others by name, so each platform is its own file. macOS and Linux share one driver; the
# darwin build keeps the name every Jamf runbook and the LaunchDaemon already use. Windows
# has a driver of its own, because its runner and its bundle are PowerShell.
BUILDS = {
    "darwin": DIST / "collect.sh",
    "linux": DIST / "collect-linux.sh",
    "windows": DIST / "collect-windows.ps1",
}

# WHAT MAY REACH AN ENDPOINT, BY NAME. Upstream decides what its bundle packs; this decides what
# Arthur deploys, so a file upstream adds is refused until it is named here. A pattern over
# catalog-shaped names is not enough: the catalog rendered into SQL is named like a query.
#
# dist/signatures.sql IS CARRIED AND NEVER READ. It is the catalog rendered into SQL for
# `bin/discover --names`, and upstream packs it into every bundle. The driver does not pass
# --names and test/lint.sh fails if it starts to, so matching stays off the device. Leaving the
# file out would mean patching the vendored bundler, and the catalog is public anyway.
ENDPOINT_FILES = (
    "bin/discover",
    "bin/discover.ps1",
    "bin/container-scan",
    "dist/discovery-{platform}.sql",
    "dist/discovery-deep.sql",
    "dist/ai-detection-spec.conf",
    "dist/signatures.sql",
)


def vendored_bundler():
    """Import tools/bundle.py out of the vendored tree.

    By path, not by name: the vendored tools/ is not a package and must not become one --
    an __init__.py here would be an edit to a vendored tree, which tools/vendor-queries.sh
    overwrites wholesale on the next bump.
    """
    path = VENDOR / "tools" / "bundle.py"
    if not path.is_file():
        sys.exit(
            f"no {path.relative_to(ROOT)} -- the collector is built by upstream's "
            f"bundler. Re-vendor at v0.18.0 or later with tools/vendor-queries.sh.",
        )
    # Importing writes __pycache__ beside the module, which would have the build editing
    # vendor/ -- the one directory this tree does not edit. Restored rather than left set,
    # because a caller may have imported this module for one function.
    was = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("vendored_bundle", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = was
    # THIS TREE BUILDS THREE COLLECTORS, SO IT NEEDS A BUNDLER THAT KNOWS WINDOWS. One that
    # does not would fail further down on a platform name, which says nothing about the
    # vendored ref being the cause. Asked of the module, not searched for in its text.
    # tools/vendor-queries.sh refuses such a ref before it clears vendor/.
    if "windows" not in getattr(mod, "PLATFORMS", ()):
        sys.exit(
            f"{path.relative_to(ROOT)} cannot build a Windows bundle, and this tree builds "
            f"one for each of three platforms. Re-vendor at v0.18.0 or later with "
            f"tools/vendor-queries.sh.",
        )
    return mod


# THE SAME DRIVER RUNS ON BOTH PLATFORMS, so nothing in it may be one platform's: gzip, base64,
# tr, wc and mv are stock on macOS and on every Linux image this tree deploys to, and the JSON
# check is the vendored runner's. Which artifact a build carries is the bundle's business.
DRIVER = r"""#!/bin/bash
# GENERATED by tools/build-collector.py. Do not edit; rebuild.
#
# The Arthur half of the collector: what to do with the tree the bundle just extracted.
# Upstream's wrapper sets AI_DETECTION_SPEC_ROOT to it and runs this. Everything here is a
# property of Arthur's reporting channel rather than of osquery -- which is exactly why it
# lives on this side of the seam.
#
#   $OUT/inventory.json   the readable payload
#   $OUT/inventory.ea     the framed value to report, ~21KB of a 256KB budget
#   $OUT/status.txt       one line, for a Smart Group to match on
#
# WHY A SCHEDULED SCRIPT AND NOT AN EXTENSION ATTRIBUTE. osquery's docker_images has no
# timeout of its own, and against a daemon that answers /_ping and then stops serving, the
# query does not return. No documented Jamf timeout for an EA script exists, so an unbounded
# EA does not fail fast -- it hangs that Mac's inventory collection. Nothing waits on a Policy.
set -uo pipefail

# Set by the bundle's wrapper, which extracted bin/ and dist/ into a private temp directory
# and removes it on the way out. Guarded rather than assumed: run by hand without the wrapper
# this would otherwise fail somewhere further down, as a missing path.
[ -n "${AI_DETECTION_SPEC_ROOT:-}" ] || {
  echo "arthur: AI_DETECTION_SPEC_ROOT is not set. This is the driver half of a built collector" \
       "(dist/collect.sh or dist/collect-linux.sh); run that, not this." >&2; exit 1; }

OUT="${ARTHUR_OUT_DIR:-/var/lib/arthur}"

mkdir -p "$OUT" 2>/dev/null || { echo "arthur: cannot create $OUT" >&2; exit 1; }

# EACH RUN WRITES INTO A STAGING DIRECTORY AND PUBLISHES BY RENAME, only once the scan, its JSON
# check and its framing have all succeeded. A failure at any of them leaves the previous three
# files as they were, together and describing one scan. Inside $OUT, so a rename never crosses
# a filesystem.
stage="$(mktemp -d "$OUT/.scan.XXXXXX")" || {
  echo "arthur: cannot create a staging directory in $OUT" >&2; exit 1; }
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM

# A RUN THAT CANNOT FINISH KEEPS THE LAST GOOD ONE, in either direction. On a schedule a
# transient failure is ordinary, and discarding a good scan because one run could not complete
# reports a well-equipped machine as empty -- so serve what the last successful run produced,
# whose own timestamp says how old it is, and fail the run rather than the data. With nothing
# good ever written there is nothing to keep: leave no partial file claiming to be a result, so
# both attributes report `no-cache`, which is true.
keep_last_good() {
  if [ -s "$OUT/inventory.ea" ] && [ -s "$OUT/status.txt" ]; then
    echo "arthur: keeping the last successful scan; the value below is that run, not this one" >&2
    cat "$OUT/status.txt"
    exit 1
  fi
  rm -f "$OUT/inventory.json" "$OUT/status.txt" "$OUT/inventory.ea"
  echo "arthur: no previous scan to fall back on; no attribute value written" >&2
  exit 1
}

# THE PING TIMEOUT IS 15s, ABOVE UPSTREAM'S DEFAULT OF 8. Why a cold daemon needs a longer
# ping, and what each Docker state costs, is upstream's osquery/docs/containers.md. What is this
# repo's is the number: 15 clears the ~10s a wedged engine takes to answer 500, so the branch
# reports `unhealthy:500` instead of collapsing it into an indistinguishable `000`. Upstream
# sizes its default against a 10s budget that does not bind here -- this runs in the scheduled
# collector, not the Extension Attribute, whose side is a `cat`. test/lint.sh holds the floor.
#
# The cost lands off the reporting path: no socket means no ping at all (`absent`,
# immediately), so this only spends time where a socket exists but nothing answers.
# Overridable, because a fleet that has measured its own Macs should use its own number.
export DOCKER_PING_TIMEOUT="${DOCKER_PING_TIMEOUT:-15}"

# Into the staging directory; nothing in $OUT changes until the publish at the end.
# A FAILED SCAN MUST NOT REPLACE A GOOD ONE, IN EITHER DIRECTION. discover's exit status used
# to be discarded -- no `set -e`, no `||` -- and because discover writes by rename, a failed
# run left the previous inventory.json in place and the framing step below re-framed it into a
# fresh-looking value and exited 0. Measured: a Mac that lost osquery reported `ok` with a
# stale timestamp and a green policy, having collected nothing.
#
# The fix is NOT to delete the last good scan. On an Ongoing schedule a transient failure is
# ordinary, and discarding a good payload because one run could not look would report a
# well-equipped Mac as empty -- the same wrong answer in the other direction, and the one this
# project treats as its most dangerous. So: keep the last successful scan, serve it, and fail
# the POLICY rather than the data. Jamf then carries the best evidence this Mac ever produced
# while its policy log says plainly that the latest attempt did not run.
#
# HOW A READER TELLS IT IS OLD. The kept payload dates itself -- the status line opens with a
# UTC timestamp and every branch carries a dated kind=scan row -- so age is a property of the
# value, not of the file's mtime, which a redeploy would reset. Nothing here is silently
# refreshed: on this path no file is rewritten at all.
#
# SAFE TO TREAT NON-ZERO AS FATAL, which is worth checking rather than assuming: every failure
# path in discover's --write branch leaves the destination alone and says so ("produced no
# payload; $WRITE left alone"). A branch that could not look is NOT a failure -- it writes a
# dated kind=scan row, the status line says `degraded`, exit 0. So non-zero always means
# nothing was written, never that good rows are being kept in place of better ones.
"$AI_DETECTION_SPEC_ROOT/bin/discover" \
  --write  "$stage/inventory.json" \
  --status "$stage/status.txt" > /dev/null || {
  echo "arthur: discover failed. Is osquery installed?" >&2
  keep_last_good
}

# THE FRAMED VALUE IS BUILT HERE, not by bin/discover: `arthur1.` is Arthur's wire format and
# the size budget a property of the reporting channel, and neither is a fact about osquery.
#
# The writer frames rather than the reader because the raw JSON is ~127 KB on a reference Mac
# against ~21 KB framed, so the reporting path cannot carry the raw file. Framing here keeps
# that path a literal `cat`, and needs no interpreter on either side.
#
# BY RENAME, for the same reason as the payload above: a reader catching a half-written value
# uploads a truncated base64 blob, which decodes to nothing at all.
#
# OVER THE CAP WRITES A REASON, NOT NOTHING. An absent, empty or stale attribute value is
# indistinguishable from a Mac with no AI tools on it -- this project's most dangerous failure
# mode -- so an oversize payload replaces the value with ERROR:oversize:<bytes>, unframed and
# matchable by a Smart Group. This is the only implementation of that rule left: an inline
# Extension Attribute script in this repo carried a second one, and it is gone.
# NO INTERPRETER ON THE ENDPOINT. python3 is not part of macOS -- /usr/bin/python3 is a shim
# that fails without Command Line Tools -- and a collector that needed it wrote nothing, which
# reads as a machine with no AI tools. Framing is gzip and base64; the JSON check is below.
#
# bin/discover writes compact JSON already, so nothing re-serialises it.
#
# CHECKED BY THE VENDORED RUNNER: `discover --cache` parses the file with osquery's own
# json_valid() and json_type() and exits non-zero unless it is a JSON array -- a truncated or
# corrupt payload is refused rather than published, with nothing the scan did not already need.
# A check that could not run -- osqueryi not answering -- is a failed check like any other, and
# discover's own stderr says which it was.
"$AI_DETECTION_SPEC_ROOT/bin/discover" --cache "$stage/inventory.json" > /dev/null || {
  echo "arthur: this scan failed its JSON check (the reason is above)" >&2
  keep_last_good
}

# ONE LINE, WHATEVER base64 DOES. Line wrapping differs between base64 implementations and
# versions; `tr -d` makes the result one line regardless, and the attribute must be one line --
# the EA reader wraps `cat` output in <result> and a wrapped value would carry newlines into it.
eatmp="$stage/inventory.ea"
{ printf 'arthur1.'; gzip -9 -c "$stage/inventory.json" | base64 | tr -d '\n'; } > "$eatmp" || {
  echo "arthur: could not frame the payload" >&2
  keep_last_good
}

# 256 KB, AND ON COMPUTE ENGINE IT IS THE PLATFORM LIMIT, so it must not rise. A guest
# attribute refuses a value over exactly 262,144 bytes with HTTP 400 (measured 2026-10-03), and
# the trailing newline added below is not part of the value -- the reporter strips it. Jamf
# stores at least 1 MB (measured 2026-09-05), so there the budget is ours rather than Jamf's.
#
# The budget is not about bandwidth -- fleet cost is payload x fleet whatever this number says
# -- it is about WHOSE FAILURE FIRES FIRST. Ours is loud and known: ERROR:oversize:<bytes>,
# naming the fault and its size, where a carrier's own limit might truncate, drop the value, or
# refuse the whole submission.
#
# At the measured 25.4 framed bytes per row the cap fires near 10,300 rows, against the ~840 a
# loaded developer Mac carries. A Mac at 10,000 rows is a defect rather than a heavy Mac, so
# this doubles as a tripwire for a runaway branch.
CAP=262144
bytes=$(wc -c < "$eatmp" | tr -d ' ')
if [ "$bytes" -gt "$CAP" ]; then
  echo "arthur: framed value is $bytes bytes, over the $CAP-byte cap by $((bytes - CAP)). Reporting the reason instead of the payload." >&2
  printf 'ERROR:oversize:%s' "$bytes" > "$eatmp"
else
  echo "arthur: framed $(wc -c < "$stage/inventory.json" | tr -d ' ') bytes of JSON into $bytes bytes ($(( (bytes * 100 + CAP / 2) / CAP ))% of cap)" >&2
fi

# 644 so an attribute script can read it as any user.
printf '\n' >> "$eatmp"
chmod 644 "$eatmp"
[ -s "$stage/status.txt" ] || { echo "arthur: no status written" >&2; keep_last_good; }

# PUBLISH: three renames on one filesystem, the framed value last, so a reader between two of
# them finds the new readable payload beside the previous value, never a partial file.
for f in inventory.json status.txt inventory.ea; do
  mv -f "$stage/$f" "$OUT/$f" || { echo "arthur: could not publish $f" >&2; exit 1; }
done

# The scheduler records the exit status -- Jamf shows a non-zero one as a failed Policy, systemd
# a failed unit. A branch that could not look is NOT a failed collection: the payload says so
# per branch, and the status line is what a Smart Group reads. Only an inability to collect is
# an error.
cat "$OUT/status.txt"
exit 0
"""


# THE WINDOWS DRIVER: the same policy as DRIVER, in the language the Windows runner and its
# bundle are written in. What it shares with DRIVER is stated there and not repeated here.
#
# CMDLETS AND CORE TYPES ONLY. Where AppLocker or WDAC is enforced, an unsigned script runs
# in PowerShell's ConstrainedLanguage mode, which refuses .NET beyond a short list of core
# types. The vendored runner and wrapper keep to that, and test/lint.sh holds this to it too.
DRIVER_PS = r"""# GENERATED by tools/build-collector.py. Do not edit; rebuild.
#
# The Arthur half of the Windows collector: what to do with the tree the bundle just
# extracted. Upstream's wrapper sets AI_DETECTION_SPEC_ROOT to it and runs this.
#
#   $out\inventory.json   the readable payload
#   $out\status.txt       one line, for a reader to match on
#
# NO inventory.ea. The framed value is what a carrier's attribute holds, and no carrier
# reads a Windows machine yet, so nothing would read the file.
$ErrorActionPreference = 'Stop'

# Set by the bundle's wrapper, which extracted bin\ and dist\ into a private temp directory
# and removes it on the way out. Guarded, so that run by hand without the wrapper this says
# so and does not fail further down, as a missing path.
if (-not $env:AI_DETECTION_SPEC_ROOT) {
    Write-Host ('arthur: AI_DETECTION_SPEC_ROOT is not set. This is the driver half of a ' +
        'built collector (dist/collect-windows.ps1); run that, not this.')
    exit 1
}
$discover = Join-Path (Join-Path $env:AI_DETECTION_SPEC_ROOT 'bin') 'discover.ps1'

$out = $env:ARTHUR_OUT_DIR
$ours = -not $out
if ($ours) { $out = Join-Path $env:ProgramData 'Arthur' }
try {
    New-Item -ItemType Directory -Path $out -Force | Out-Null
} catch {
    Write-Host "arthur: cannot create $out"
    exit 1
}

# A RUN WITH ADMINISTRATOR RIGHTS WRITES ONLY IN A FOLDER THAT IS ADMINISTRATORS'. Any user
# may create a folder in ProgramData, and whoever creates one owns it. And a folder an
# administrator made can still let other accounts add, change or delete what is in it: one
# made on the system drive outside a profile does, by default. Either way they can rewrite
# what a run publishes there, or swap an entry for a link, and this run moves and deletes
# through it with rights they do not have. So a run as SYSTEM or as an elevated
# administrator refuses a folder owned by anyone but SYSTEM, the Administrators group or
# the account it runs as, and a folder any other account can write in. A run as a standard
# user has no rights to lend, and is not asked.
#
# The token's integrity label says which run this is: S-1-16-12288 is High and S-1-16-16384
# is System. Read with whoami, which every Windows has, and taken as elevated when it
# cannot be read. Get-Acl is missing only off Windows, where the test runs this file.
$elevated = $false
$me = ''
$sid = ''
$system32 = ''
if (Get-Command -Name Get-Acl -ErrorAction SilentlyContinue) {
    $elevated = $true
    try {
        $system32 = Join-Path $env:SystemRoot 'System32'
        $whoami = Join-Path $system32 'whoami.exe'
        $me = "$(& $whoami)".Trim()
        if ("$(& $whoami /user /fo csv /nh)" -match '"(S-1-[0-9-]+)"') { $sid = $Matches[1] }
        foreach ($line in @(& $whoami /groups /fo csv /nh)) {
            if ($line -match 'S-1-16-(\d+)') { $elevated = [int]$Matches[1] -ge 12288 }
        }
    } catch { }
}

# Owned by SYSTEM (SY), the Administrators group (BA) or this account. The first two are
# read off the SDDL, because their names are localised.
function Test-Ours([string]$Path) {
    try {
        $acl = Get-Acl -LiteralPath $Path
        return (($acl.Sddl -match '^O:(BA|SY)') -or ($me -and $acl.Owner -eq $me))
    } catch {
        return $false
    }
}

# THE OTHER ACCOUNTS A FOLDER LETS WRITE IN IT, read off the SDDL of its access list, where
# an allowing entry is (A;flags;rights;;;account). Not counted: SYSTEM (SY), the
# Administrators group (BA), the built-in Administrator (LA) and TrustedInstaller, which
# are administrators by other names; this account, by its SID; and CREATOR OWNER (CO) and
# OWNER RIGHTS (OW), which stand for whoever made or owns an entry, and so for one of the
# accounts allowed to. The rights are a mask or two-letter codes. All but reading, listing
# and traversing count as writing, and a mask or code that cannot be read counts too. So
# does an entry only the folder's contents inherit: this run makes its files there.
function Get-Writers([string]$Path) {
    $trusted = @('SY', 'BA', 'LA', 'CO', 'OW',
        'S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464')
    if ($sid) { $trusted += $sid }
    $known = @{ 'BU' = 'Users'; 'AU' = 'Authenticated Users'; 'WD' = 'Everyone'; 'IU' = 'Interactive' }
    $reads = @('FR', 'FX', 'GR', 'GX', 'RC', 'CC', 'SW', 'WP', 'LO')
    # Add an entry, change one, delete one, or take the folder over.
    $writes = 0x500D0156
    $sddl = ''
    try { $sddl = (Get-Acl -LiteralPath $Path).Sddl } catch { }
    if ($sddl -notmatch 'D:') { return , @('(not known: its access list cannot be read)') }
    if ($sddl -match 'NO_ACCESS_CONTROL') { return , @('Everyone (it has no access list)') }
    $found = @()
    foreach ($piece in @($sddl -split '\(' | Select-Object -Skip 1)) {
        $entry = ($piece -split '\)')[0] -split ';'
        if ($entry.Count -lt 6 -or @('A', 'OA', 'XA', 'ZA') -notcontains $entry[0]) { continue }
        $who = $entry[5]
        if ($trusted -contains $who) { continue }
        $rights = $entry[2]
        $can = $true
        if ($rights -match '^0x[0-9a-f]+$') {
            try { $can = (([long]$rights) -band $writes) -ne 0 } catch { }
        } elseif ($rights -match '^([A-Z][A-Z])*$') {
            $can = $false
            for ($i = 0; $i -lt $rights.Length; $i += 2) {
                if ($reads -notcontains $rights.Substring($i, 2)) { $can = $true }
            }
        }
        if (-not $can) { continue }
        if ($known[$who]) { $who = "$($known[$who]) ($who)" }
        if ($found -notcontains $who) { $found += $who }
    }
    return , $found
}

# Both: owned by one of those accounts, and no other account can write in it. Asked of a
# file as of a folder, since a file can hold an entry of its own that its folder does not.
function Test-Trusted([string]$Path) {
    return ((Test-Ours $Path) -and ((Get-Writers $Path).Count -eq 0))
}

if ($elevated) {
    if (-not (Test-Ours $out)) {
        $owner = ''
        try { $owner = (Get-Acl -LiteralPath $out).Owner } catch { }
        Write-Host "arthur: $out is owned by '$owner', not by SYSTEM, the Administrators group or this account."
        Write-Host 'arthur: a run with administrator rights does not write where another account put the folder. Remove it, or set ARTHUR_OUT_DIR to one an administrator made.'
        exit 1
    }
    # THE FOLDER THIS CHOSE IS FOR ADMINISTRATORS ONLY, AND IS HELD TO THAT ON EVERY RUN. One
    # made in ProgramData, by this run or by an administrator's mkdir, takes on its rule
    # that any user may add files. A folder named in ARTHUR_OUT_DIR is for whoever named it
    # to restrict: its list is read below and never changed.
    #
    # THE WHOLE LIST IS REPLACED, NOT EDITED. A new folder can hold entries of its own that
    # came from its parent, which removing inheritance leaves: on Windows Server 2025,
    # `icacls /inheritance:r /grant:r` left a folder made under a user's profile with full
    # control for the account that made it. `icacls /restore` sets the list it is handed,
    # in SDDL: SYSTEM (SY) and Administrators (BA) in full, Users (BU) to read and traverse,
    # each for the folder and what is made in it, and nothing inherited (P). It reads a
    # file in the form `icacls /save` writes: a name, then its list, in UTF-16.
    if ($ours) {
        $list = Join-Path $out ".acl.$(Get-Random)"
        $restricted = $false
        try {
            Set-Content -LiteralPath $list -Encoding Unicode -Value @(
                (Split-Path -Leaf $out),
                'D:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1200a9;;;BU)')
            & (Join-Path $system32 'icacls.exe') (Split-Path -Parent $out) /restore $list | Out-Null
            $restricted = ($LASTEXITCODE -eq 0)
        } catch { }
        Remove-Item -LiteralPath $list -Force -ErrorAction SilentlyContinue
        if (-not $restricted) {
            Write-Host "arthur: cannot restrict $out to administrators"
            exit 1
        }
    }
    # ASKED OF EITHER FOLDER, after the default one's list is set, so that list is checked
    # too. What a folder let another account leave before it was restricted is not trusted
    # either: see Use-LastGood and Restore-Kept below.
    $others = Get-Writers $out
    if ($others.Count -gt 0) {
        Write-Host "arthur: $out lets other accounts write in it: $($others -join ', ')."
        Write-Host 'arthur: a run with administrator rights writes only where SYSTEM, the Administrators group and this account can. Restrict the folder to them, run without administrator rights, or leave ARTHUR_OUT_DIR unset to use the default folder.'
        exit 1
    }
}

# EACH RUN WRITES INTO A STAGING DIRECTORY AND PUBLISHES BY MOVE, only once the scan and its
# JSON check have both succeeded. A failure at either leaves the previous files as they
# were, together and describing one scan. Inside $out, so a move never crosses a volume.
$stage = Join-Path $out ".scan.$(Get-Random)"
try {
    New-Item -ItemType Directory -Path $stage | Out-Null
} catch {
    Write-Host "arthur: cannot create a staging directory in $out"
    exit 1
}
$inventory = Join-Path $stage 'inventory.json'
$status = Join-Path $stage 'status.txt'
$published = @('inventory.json', 'status.txt')

# WHAT A PUBLISH COULD NOT PUT BACK WAITS IN .previous, AND NOTHING IS SERVED WHILE IT WAITS.
# A publish that fails renames the previous pair back into place. When it cannot, because a
# file it placed will not be taken back or a previous one will not go back, the files still
# set aside are moved here: in the output folder, under a fixed name, where the next run
# finds them. The folder's presence is the marker that what is in place may be half of two
# scans. Every run that reaches a publish or a fallback first finishes that job: it clears
# the places of the kept files, then renames them in. Clearing comes first and stops at the
# first file that will not go, so a kept file never lands beside one of another scan.
$kept = Join-Path $out '.previous'
function Restore-Kept {
    if (-not (Test-Path -LiteralPath $kept -PathType Container)) { return $true }
    # One another account made, before the folder was restricted, or can write in, is not
    # read at all: clearing a place for a file one of them put there would delete a scan.
    if ($elevated -and -not (Test-Trusted $kept)) { return $true }
    try {
        $names = @()
        foreach ($name in $published) {
            if (Test-Path -LiteralPath (Join-Path $kept $name) -PathType Leaf) { $names += $name }
        }
        foreach ($name in $names) {
            $dest = Join-Path $out $name
            if (-not (Test-Path -LiteralPath $dest)) { continue }
            # Files only, as in the publish below.
            if (-not (Test-Path -LiteralPath $dest -PathType Leaf)) { throw "$dest is a folder" }
            Remove-Item -LiteralPath $dest -Force
        }
        foreach ($name in $names) {
            Move-Item -LiteralPath (Join-Path $kept $name) -Destination (Join-Path $out $name)
        }
    } catch {
        Write-Host "arthur: $kept holds the previous scan, which cannot be put back yet. Nothing is published or served until it is."
        return $false
    }
    Remove-Item -LiteralPath $kept -Recurse -Force -ErrorAction SilentlyContinue
    if ($names.Count -gt 0) { Write-Host "arthur: put back the previous scan, which an earlier run left in $kept" }
    return $true
}

# A RUN THAT CANNOT FINISH KEEPS THE LAST GOOD ONE. On a schedule a transient failure is
# ordinary, and discarding a good scan because one run could not complete reports a
# well-equipped machine as empty. So serve what the last successful run produced, whose own
# timestamp says how old it is, and fail the run. With nothing good ever written there is
# nothing to keep: leave no partial file claiming to be a result.
function Use-LastGood {
    if (-not (Restore-Kept)) { return }
    # AND, FOR A RUN WITH ADMINISTRATOR RIGHTS, ONLY A PAIR THAT SUCH A RUN WROTE AND NO OTHER
    # ACCOUNT CAN CHANGE. A folder can have let any user add files before it was restricted,
    # and a pair one of them left there before the first scan would be served as the last
    # good one. And a file can let an account write in it that its folder does not. This is
    # asked of the files in place, so of a pair Restore-Kept has just put back as well.
    $good = $true
    foreach ($name in $published) {
        $path = Join-Path $out $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) {
            $good = $false
        } elseif ($elevated -and -not (Test-Trusted $path)) {
            $good = $false
        }
    }
    if ($good) {
        Write-Host 'arthur: keeping the last successful scan; the value below is that run, not this one'
        Get-Content -LiteralPath (Join-Path $out 'status.txt') -Encoding UTF8 | ForEach-Object { Write-Host $_ }
        return
    }
    foreach ($name in $published) {
        $path = Join-Path $out $name
        # Files only: a folder under one of these names is never this run's to delete.
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host 'arthur: no previous scan to fall back on; no value written'
}

$code = 1
try {
    # A FAILED SCAN MUST NOT REPLACE A GOOD ONE. Non-zero from --write always means nothing
    # was written: a branch that could not look is not a failure, it writes a dated
    # kind=scan row, the status line says `degraded`, and the exit is 0.
    & $discover --write $inventory --status $status
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'arthur: discover failed. Is osquery installed?'
        Use-LastGood
    } else {
        # CHECKED BY THE VENDORED RUNNER: --cache parses the file with osquery's own
        # json_valid() and json_type() and exits non-zero unless it is a JSON array, so a
        # truncated or corrupt payload is refused and not published. It also prints the
        # payload, which nothing here wants.
        & $discover --cache $inventory | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host 'arthur: this scan failed its JSON check (the reason is above)'
            Use-LastGood
        } elseif (-not (Test-Path -LiteralPath $status -PathType Leaf) -or (Get-Item -LiteralPath $status).Length -eq 0) {
            Write-Host 'arthur: no status written'
            Use-LastGood
        } elseif (Restore-Kept) {
            # (When an earlier run's pair still cannot be put back, Restore-Kept has said so,
            # and this scan is not published over a folder in that state.)
            #
            # PUBLISH BY RENAME, IN TWO STEPS, AND PUT THE PREVIOUS PAIR BACK IF IT CANNOT
            # FINISH. Nothing is overwritten: Windows PowerShell's Move-Item -Force onto an
            # existing file deletes it and then moves, so a move that failed there would leave
            # neither. First both previous files are renamed into the staging directory, then
            # both new ones into their places. A reader in between finds a file missing, never
            # a partial one and never a payload beside another scan's status.
            #
            # AND A PUBLISH CAN FAIL HALFWAY HERE, which it cannot on macOS or Linux: Windows
            # refuses to rename a file another process holds open. That stops the first step,
            # before anything new is in place, and what was set aside is moved back. If the
            # second step fails, what it placed is taken back first. THE PREVIOUS PAIR RETURNS
            # ONLY TO AN EMPTY PLACE: beside a new file that could not be taken back it would
            # be two scans passing for one. Then, or when a previous file will not go back,
            # what is still set aside is kept in .previous for the next run: see Restore-Kept.
            $aside = Join-Path $stage 'previous'
            New-Item -ItemType Directory -Path $aside | Out-Null
            $failed = ''
            $set = @()
            foreach ($name in $published) {
                $dest = Join-Path $out $name
                if (-not (Test-Path -LiteralPath $dest)) { continue }
                # A FOLDER UNDER A PUBLISHED NAME IS NOT A PREVIOUS SCAN, AND IS LEFT WHERE IT
                # IS. It may be a link to another folder, left before this one was restricted,
                # and what is set aside is deleted with the staging directory, contents and all.
                if (-not (Test-Path -LiteralPath $dest -PathType Leaf)) {
                    Write-Host "arthur: $dest is a folder, not a file. Remove it."
                    $failed = $name
                    break
                }
                try {
                    Move-Item -LiteralPath $dest -Destination (Join-Path $aside $name)
                    $set += $name
                } catch {
                    $failed = $name
                    break
                }
            }
            $placed = @()
            if (-not $failed) {
                foreach ($name in $published) {
                    try {
                        Move-Item -LiteralPath (Join-Path $stage $name) -Destination (Join-Path $out $name)
                        $placed += $name
                    } catch {
                        $failed = $name
                        break
                    }
                }
            }
            if ($failed) {
                Write-Host "arthur: could not publish $failed"
                $clean = $true
                foreach ($name in $placed) {
                    try {
                        Remove-Item -LiteralPath (Join-Path $out $name) -Force
                    } catch {
                        $clean = $false
                    }
                }
                $keep = $false
                if ($clean) {
                    foreach ($name in $set) {
                        $dest = Join-Path $out $name
                        try {
                            # Only into a gap: a file that refused to move is still in place.
                            if (-not (Test-Path -LiteralPath $dest)) {
                                Move-Item -LiteralPath (Join-Path $aside $name) -Destination $dest
                            }
                        } catch {
                            Write-Host "arthur: could not put back the previous $name"
                            $keep = $true
                        }
                    }
                } else {
                    Write-Host 'arthur: could not take back what this run placed, so the previous scan is not put back beside it'
                    # Half a pair was never a scan to serve, so only a whole one is kept.
                    $keep = ($set.Count -eq $published.Count)
                }
                if ($keep) {
                    # Out of the staging directory, which the end of this run removes.
                    try {
                        if (-not (Test-Path -LiteralPath $kept)) {
                            New-Item -ItemType Directory -Path $kept | Out-Null
                        }
                        if ($elevated -and -not (Test-Trusted $kept)) { throw 'another account made it, or can write in it' }
                        foreach ($name in $set) {
                            $from = Join-Path $aside $name
                            if (Test-Path -LiteralPath $from) {
                                Move-Item -LiteralPath $from -Destination (Join-Path $kept $name)
                            }
                        }
                        Write-Host "arthur: the previous scan is kept in $kept for the next run to put back"
                    } catch {
                        Write-Host "arthur: could not keep the previous scan in $kept, so it is lost"
                    }
                }
                Use-LastGood
            } else {
                # The scheduler records the exit status. A branch that could not look is not
                # a failed collection: the payload says so per branch, and this line is what
                # a reader matches on.
                Get-Content -LiteralPath (Join-Path $out 'status.txt') -Encoding UTF8 | ForEach-Object { Write-Host $_ }
                $code = 0
            }
        }
    }
} finally {
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue
}
exit $code
"""

DRIVERS = {"darwin": DRIVER, "linux": DRIVER, "windows": DRIVER_PS}


def collector(bundle, platform, label):
    """One platform's collector: upstream's wrapper around the vendored tree, running our
    driver."""
    # The driver reaches the bundler as a FILE because that is its interface -- it goes into
    # the payload like any other member, with its mtime, uid and mode pinned there. Which
    # temporary path it had does not reach the artifact: the member is named `driver`.
    # newline="" so the bytes are the template's on any build machine: the Windows bundle
    # refuses a member with a carriage return in it.
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, newline="") as fh:
        fh.write(DRIVERS[platform])
        tmp = fh.name
    try:
        return bundle.build(VENDOR, platform, driver=tmp, label=label), tmp
    finally:
        pass


def driver_of(bundle, path):
    """The driver as it actually SHIPS, read back out of a built collector.

    EVERY GUARD OVER THE DRIVER NEEDS THIS. The Arthur half lives inside the payload --
    base64 of gzip of a tar -- so `grep arthur1.` on the artifact finds nothing, and a guard
    that finds nothing either fails for the wrong reason or passes vacuously. Reading the
    member back asserts on what a Mac will actually run.

    THROUGH THE SUPPORTED READER, AND IT WAS NOT ONE WHEN THIS WAS WRITTEN. The first
    version unpacked the payload here, through the underscore-prefixed splitter, then gzip,
    then tarfile -- a downstream repo pinned to a private function. That is the exact shape
    of the breakage this project has already taken once: upstream removed
    `bin/discover --framed`, correctly, and it took this collector with it. Upstream added
    read_member() at v0.7.0 for this reason. A private call that works is still a private
    call, and the point of asking for the interface was not to be allowed to keep one.
    """
    try:
        return bundle.read_member(pathlib.Path(path).read_text(), "driver").decode()
    except KeyError:
        sys.exit(
            f"{path} carries no driver -- it was not built by tools/build-collector.py.",
        )
    except bundle.CorruptBundle as exc:
        # Including a file with no payload marker at all: the commonest mistake is the
        # wrong path, and the bundler names it as not a bundle.
        sys.exit(f"{path} is not a readable bundle: {exc}")


def vendored_ref():
    """The pinned ref, which rides along in the bundle's banner."""
    version = (VENDOR / "VERSION").read_text().splitlines()
    return next(
        (l.split(None, 1)[1].strip() for l in version if l.startswith("ref")),
        "?",
    )


def main():
    check = "--check" in sys.argv
    if "--driver-of" in sys.argv:
        # For the guards in test/, so there is ONE implementation of unpacking a collector
        # rather than one in lint.sh and another in run-collector.sh.
        target = sys.argv[sys.argv.index("--driver-of") + 1]
        sys.stdout.write(driver_of(vendored_bundler(), target))
        return
    if not VENDOR.exists():
        sys.exit(
            "no vendor/ai-detection-spec/ -- run tools/vendor-queries.sh <ref> first",
        )
    bundle = vendored_bundler()

    label = vendored_ref()
    for platform, out in BUILDS.items():
        # A MISSING PAYLOAD FILE IS MORE OFTEN A RENAME THAN A BAD VENDOR RUN. v0.3.0 replaced
        # dist/discovery.sql with per-platform files and this check is what caught it. The list
        # itself is upstream's now -- one less copy to drift -- but the failure it produces is
        # still ours to explain.
        files = bundle.payload_files(platform)
        missing = [f for f in files if not (VENDOR / f).is_file()]
        if missing:
            sys.exit(
                f"vendored tree does not carry {missing}. Either the vendor run was "
                f"incomplete, or upstream renamed or dropped it in this ref -- check the "
                f"release notes. Re-vendoring will not fix a rename.",
            )

        # Only vetted files reach an endpoint. The failure this prevents -- a Mac carrying the
        # catalog, or matching on it -- would be invisible in a base64 blob.
        allowed = {f.format(platform=platform) for f in ENDPOINT_FILES}
        unvetted = [f for f in files if f not in allowed]
        if unvetted:
            sys.exit(
                f"the vendored bundler would pack {unvetted}, which this tree has not vetted for "
                f"endpoints. Anything catalog-derived must not ship; otherwise add it to "
                f"ENDPOINT_FILES. The endpoint holds no catalog -- see docs/architecture.md.",
            )

        built, tmp = collector(bundle, platform, label)
        try:
            if check:
                if not out.exists():
                    sys.exit(
                        f"{out.relative_to(ROOT)} is missing. Run tools/build-collector.py.",
                    )
                # COMPARED BY MEANING, NOT BY BYTES -- upstream's matches() decompresses the
                # payload and compares the tar, because zlib's output is not identical across
                # zlib versions and a byte comparison fails at random on a CI runner against
                # content that matches. That lesson was learned here and went upstream with the
                # code.
                if not bundle.matches(
                    out.read_text(),
                    VENDOR,
                    platform,
                    driver=tmp,
                    label=label,
                ):
                    sys.exit(
                        f"{out.relative_to(ROOT)} does not carry the vendored tree or the "
                        f"current driver. Run tools/build-collector.py.",
                    )
                print(f"{out.relative_to(ROOT)} is up to date (vendored ref {label})")
                continue
            DIST.mkdir(exist_ok=True)
            # As bytes, for the reason collector() gives: no build machine's line endings.
            out.write_bytes(built.encode())
            out.chmod(0o755)
            print(
                f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB, "
                f"{len(files)} vendored files + the Arthur driver, ref {label})",
            )
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
