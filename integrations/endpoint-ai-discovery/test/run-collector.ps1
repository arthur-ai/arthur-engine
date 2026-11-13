# Run the collector built for Windows, dist/collect-windows.ps1, and assert on what it
# produced. Needs osquery, and python for one step; about 30s.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File test\run-collector.ps1
#
# test/run-collector.sh's questions, asked of the Windows build: did the collector publish
# this scan, keep the last good one when a run failed, and leave nothing behind. Whether a
# query found some piece of software is upstream's question, and is not asked here.
#
# ASSERTS ON COUNTS AND IDENTIFIERS, NEVER ON "DID IT PARSE". The failure mode here is
# plausible output with wrong values and exit code zero.
#
# CMDLETS AND CORE TYPES ONLY, like the collector. CI runs this file a second time with
# __PSLockdownPolicy=4, which puts it and every collector it starts in ConstrainedLanguage
# mode: the mode an unsigned script gets where AppLocker or WDAC is enforced.

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Collect = Join-Path (Join-Path $Root 'dist') 'collect-windows.ps1'
$Build = Join-Path (Join-Path $Root 'tools') 'build-collector.py'
# The PowerShell running this file, so the collector is tested under the same one.
$Shell = (Get-Process -Id $PID).Path
$Fail = 0

function Note([string]$Message) { Write-Host "ok: $Message" }
function Bad([string]$Message) {
    Write-Host "FAIL: $Message"
    $script:Fail = 1
}

if (-not (Test-Path -LiteralPath $Collect -PathType Leaf)) {
    Write-Host 'FAIL: no dist/collect-windows.ps1 -- run tools/build-collector.py'
    exit 1
}

# THE TEST NEEDS python; THE COLLECTOR MUST NOT. Reading the driver back out of the built
# collector is tools/build-collector.py's job, and this runs on a build machine.
$Python = Get-Command -Name python, python3 -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $Python) {
    Write-Host 'FAIL: this test needs python on PATH (the collector does not, deliberately).'
    exit 1
}

$Work = Join-Path $env:TEMP "collector-test.$(Get-Random)"
$Out = Join-Path $Work 'arthur'
# A LEAKED WORK DIRECTORY IS A DISK THAT FILLS ON A SCHEDULE. Every run writes to TEMP: the
# bundle's extraction directory, the runner's working directory, and what osqueryi leaves.
# A TEMP of the test's own makes "nothing is left" an assertion.
$RunTemp = Join-Path $Work 'temp'
New-Item -ItemType Directory -Path $RunTemp | Out-Null
$HostTemp = $env:TEMP
$HostTmp = $env:TMP

# A script as a scheduler starts it: a process of its own, by file. Returns the lines it
# printed; its exit status is in $LASTEXITCODE. $Pack and $SpecRoot are how a run is broken:
# a pack the runner cannot find, or a tree with a stub runner in it.
function Invoke-Script([string]$Script, [string]$OutDir, [string]$Pack, [string]$SpecRoot) {
    # Under 'Stop', 5.1 turns the first line a program writes to a redirected stderr into
    # a terminating error, and the line is wanted here as a line.
    $ErrorActionPreference = 'Continue'
    $env:TEMP = $RunTemp
    $env:TMP = $RunTemp
    $env:ARTHUR_OUT_DIR = $OutDir
    if ($Pack) { $env:DISCOVER_PACK = $Pack }
    if ($SpecRoot) { $env:AI_DETECTION_SPEC_ROOT = $SpecRoot }
    try {
        $lines = & $Shell -NoProfile -ExecutionPolicy Bypass -File $Script 2>&1 | ForEach-Object { "$_" }
    } finally {
        $env:TEMP = $HostTemp
        $env:TMP = $HostTmp
        $env:ARTHUR_OUT_DIR = $null
        $env:DISCOVER_PACK = $null
        $env:AI_DETECTION_SPEC_ROOT = $null
    }
    return , @($lines)
}

function Show([string[]]$Lines) {
    foreach ($line in $Lines) { Write-Host "    $line" }
}

function Get-Hash([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-Names([string]$Dir) {
    if (-not (Test-Path -LiteralPath $Dir)) { return , @() }
    return , @(Get-ChildItem -LiteralPath $Dir -Force | ForEach-Object { $_.Name } | Sort-Object)
}

# 5.1's ConvertFrom-Json hands an array back as one object, and 7's unrolls it.
function Read-Rows([string]$Path) {
    $parsed = ConvertFrom-Json -InputObject (Get-Content -LiteralPath $Path -Raw -Encoding UTF8)
    foreach ($item in @($parsed)) {
        if ($item -is [array]) { foreach ($row in $item) { $row } } else { $item }
    }
}

try {
    Write-Host '== a clean run =========================================================='
    $printed = Invoke-Script $Collect $Out '' ''
    $code = $LASTEXITCODE
    Show $printed
    if ($code -ne 0) {
        # A MISSING PREREQUISITE IS NOT A DEFECT, and the collector already says which it
        # is: the vendored runner prints "no osqueryi found". Read off that message, where
        # a second copy of the search path here would drift from the one that matters.
        if (@($printed | Where-Object { $_ -match 'no osqueryi found' }).Count -gt 0) {
            Write-Host 'FAIL: osquery is not installed on this machine. That is a prerequisite, not a'
            Write-Host '      defect in the collector -- install osquery, or set OSQI, and run again.'
        } else {
            Bad "the collector exited $code on a healthy machine"
        }
        Write-Host 'collector: FAIL'
        exit 1
    }
    Note 'collect-windows.ps1 exited 0'

    $inventory = Join-Path $Out 'inventory.json'
    $status = Join-Path $Out 'status.txt'
    # EXACTLY THE TWO, which also says no staging directory was left beside them and no
    # inventory.ea was written for a carrier that does not exist.
    $names = (Get-Names $Out) -join ' '
    if ($names -ne 'inventory.json status.txt') {
        Bad "the output directory holds [$names], not inventory.json and status.txt"
        Write-Host 'collector: FAIL'
        exit 1
    }
    foreach ($path in @($inventory, $status)) {
        if ((Get-Item -LiteralPath $path).Length -eq 0) { Bad "$path is empty" }
    }
    Note 'wrote inventory.json and status.txt, and nothing else'

    Write-Host '== the payload, and what the two files agree on ========================='
    $before = $Fail
    $rows = @(Read-Rows $inventory)
    $line = Get-Content -LiteralPath $status -Raw -Encoding UTF8
    # Not "is it valid JSON". A scan that dies on its first table can leave a valid, empty,
    # entirely plausible array.
    if ($rows.Count -eq 0) { Bad 'the payload has no rows at all -- a clean machine and a failed scan look alike' }

    # Evidence rows (SPEC.md 5.1): `kind` and `id` always, every value a string, and no
    # member the spec does not name.
    $named = @('kind', 'id', 'ver', 'loc', 'extra', 'perms')
    $off = @($rows | Where-Object {
        $members = @($_.PSObject.Properties | ForEach-Object { $_.Name })
        $values = @($_.PSObject.Properties | ForEach-Object { $_.Value })
        ($members -notcontains 'kind') -or ($members -notcontains 'id') -or
            (@($members | Where-Object { $named -notcontains $_ }).Count -gt 0) -or
            (@($values | Where-Object { $_ -isnot [string] }).Count -gt 0)
    })
    if ($off.Count -gt 0) { Bad "$($off.Count) rows are not evidence rows of the members the spec names" }

    # ONE STATUS LINE, and its vocabulary is what a reader matches on.
    if ($line -notmatch '^[^\r\n]+\n$') { Bad "status.txt must be exactly one line ending in a newline, got: $line" }
    $tokens = @{}
    $first = ''
    if ($line -match '^(\S+) (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) (.*)') {
        $first = $Matches[1]
        foreach ($part in ($Matches[3].Trim() -split ' ')) {
            $pair = $part -split '=', 2
            if ($pair.Count -eq 2) { $tokens[$pair[0]] = $pair[1] }
        }
    } else {
        Bad "status.txt does not open with a word and an ISO-8601 UTC timestamp: $line"
    }
    if (@('ok', 'degraded') -notcontains $first) { Bad "status starts with '$first', want ok or degraded" }
    foreach ($key in $tokens.Keys) {
        if ($key -eq 'rows') { continue }
        $value = $tokens[$key]
        if (@('ok', 'absent', 'error') -notcontains $value -and $value -notmatch '^(unhealthy|timeout|unreadable):') {
            Bad "unknown outcome '$value' for branch $key"
        }
    }
    if ($tokens['rows'] -ne "$($rows.Count)") { Bad "status says rows=$($tokens['rows']) and the payload holds $($rows.Count)" }

    # THE TWO FILES MUST DESCRIBE THE SAME SCAN. Derived from each other, never from a list
    # of branches typed here, which would only trail the real one.
    $scans = @{}
    foreach ($row in $rows) { if ($row.kind -eq 'scan') { $scans[$row.id] = $row } }
    $branches = (@($tokens.Keys | Where-Object { $_ -ne 'rows' }) | Sort-Object) -join ' '
    $markers = (@($scans.Keys) | Sort-Object) -join ' '
    if ($branches -ne $markers) { Bad "status names [$branches] but the payload carries markers for [$markers]" }
    if ($scans.Count -eq 0) { Bad 'the payload carries no scan marker, so nothing says which branches ran' }

    # A DATED MARKER IS HOW A READER TELLS AN OLD VALUE FROM A NEW ONE. The file's
    # modification time cannot be used: a redeploy resets it without changing the truth.
    $now = [int64]([datetime]::UtcNow - [datetime]'1970-01-01').TotalSeconds
    foreach ($name in $scans.Keys) {
        $ver = $scans[$name].ver
        if ($ver -notmatch '^\d+$' -or ($now - [int64]$ver) -lt 0 -or ($now - [int64]$ver) -gt 3600) {
            Bad "branch $name is dated '$ver', which is not a timestamp from this run"
        }
    }

    # The endpoint enumerates and matches nothing, so the catalog must not be in the payload.
    $blob = Get-Content -LiteralPath $inventory -Raw -Encoding UTF8
    foreach ($leak in @('agents.yaml', 'routes.yaml', 'catalog.json')) {
        if ($blob.Contains($leak)) { Bad "the payload mentions $leak -- the endpoint holds no catalog" }
    }
    # The scheduler's log line is the status a reader finds on disk.
    if (@($printed | Where-Object { $_ -ceq $line.Trim() }).Count -ne 1) {
        Bad 'the collector did not print the status line it wrote'
    }
    if ($Fail -eq $before) {
        Note "$($rows.Count) rows, $($scans.Count) branches, status $first, containers=$($tokens['containers'])"
    }

    Write-Host '== a failed scan must keep the last good one ============================='
    # Keep the last successful value, serve it, and fail the run, so the scheduler's log
    # says the latest attempt did not finish. THE RUNNER IS BROKEN BY TAKING ITS PACK AWAY:
    # the branch under test is "discover exited non-zero", and DISCOVER_PACK reaches it.
    $before = $Fail
    $absent = Join-Path $Work 'no-such-pack.conf'
    $hashes = @((Get-Hash $inventory), (Get-Hash $status))
    $printed = Invoke-Script $Collect $Out $absent ''
    $code = $LASTEXITCODE
    Show $printed
    if ($code -eq 0) { Bad 'a scan that could not run exited 0 -- the scheduler would show success' }
    if ((Get-Hash $inventory) -ne $hashes[0]) { Bad 'a failed run rewrote inventory.json -- the last good scan was lost or re-dated' }
    if ((Get-Hash $status) -ne $hashes[1]) { Bad 'a failed run rewrote status.txt' }
    if (@($printed | Where-Object { $_ -match 'keeping the last successful scan' }).Count -ne 1) {
        Bad 'a failed run did not say it was serving an older value'
    }
    if ($Fail -eq $before) { Note "failed scan: exit $code, both files untouched" }

    Write-Host '== with nothing to fall back on, no value at all ========================='
    # A file that is absent, empty or stale cannot be told from a machine with no AI tools
    # on it. With no previous scan there is nothing honest to serve, so the collector must
    # leave no file behind claiming to be a result.
    $before = $Fail
    $fresh = Join-Path $Work 'fresh'
    $printed = Invoke-Script $Collect $fresh $absent ''
    $code = $LASTEXITCODE
    Show $printed
    if ($code -eq 0) { Bad 'a first-ever scan that could not run exited 0' }
    $left = (Get-Names $fresh) -join ' '
    if ($left) { Bad "[$left] was left behind with no successful scan to back it" }
    if ($Fail -eq $before) { Note "no previous scan: exit $code, no partial value written" }

    Write-Host '== a scan that fails its JSON check keeps the last good one too =========='
    # The shipped driver, read back out of the built collector, against a stub runner whose
    # scan succeeds and whose --cache check cannot run, which a real machine cannot be made
    # to do on demand. Every step after the scan must leave the previous files as they were.
    $before = $Fail
    $stub = Join-Path $Work 'stub'
    New-Item -ItemType Directory -Path (Join-Path $stub 'bin') | Out-Null
    $runner = @(
        "if (`$args[0] -eq '--write') {",
        "    New-Item -ItemType File -Path `$args[1] -Value '[]' -Force | Out-Null",
        "    New-Item -ItemType File -Path `$args[3] -Value 'ok 2026-10-12T00:00:00Z rows=0' -Force | Out-Null",
        '    exit 0',
        '}',
        "if (`$args[0] -eq '--cache') {",
        "    Write-Host `"discover: could not validate `$(`$args[1]) -- the validator did not answer.`"",
        '    exit 1',
        '}',
        'exit 2') -join "`n"
    New-Item -ItemType File -Path (Join-Path (Join-Path $stub 'bin') 'discover.ps1') -Value "$runner`n" | Out-Null
    $driver = Join-Path $Work 'driver.ps1'
    $text = & $Python.Path $Build --driver-of $Collect
    if ($LASTEXITCODE -ne 0 -or -not $text) {
        Bad 'tools/build-collector.py --driver-of could not read the driver out of the built collector'
    } else {
        New-Item -ItemType File -Path $driver -Value ((@($text) -join "`n") + "`n") | Out-Null
        $printed = Invoke-Script $driver $Out '' $stub
        $code = $LASTEXITCODE
        Show $printed
        if ($code -eq 0) { Bad 'a scan that failed its JSON check exited 0' }
        if ((Get-Hash $inventory) -ne $hashes[0]) { Bad 'a failed JSON check replaced or removed the last good inventory.json' }
        if ((Get-Hash $status) -ne $hashes[1]) { Bad 'a failed JSON check replaced the last good status.txt' }
        if (@($printed | Where-Object { $_ -match 'the validator did not answer' }).Count -ne 1) {
            Bad "the runner's own reason for the failed check was not passed through"
        }
        $names = (Get-Names $Out) -join ' '
        if ($names -ne 'inventory.json status.txt') { Bad "the output directory now holds [$names]: a staging directory was left" }
        if ($Fail -eq $before) { Note "failed JSON check: exit $code, both files untouched, no staging left" }
    }

    Write-Host '== nothing is left in TEMP ==============================================='
    $left = (Get-Names $RunTemp) -join ' '
    if ($left) { Bad "left in TEMP: $left" } else { Note 'every run above, failed ones included, left nothing in TEMP' }
} finally {
    $env:TEMP = $HostTemp
    $env:TMP = $HostTmp
    Remove-Item -LiteralPath $Work -Recurse -Force -ErrorAction SilentlyContinue
}

if ($Fail -eq 0) { Write-Host 'collector: PASS' } else { Write-Host 'collector: FAIL' }
exit $Fail
