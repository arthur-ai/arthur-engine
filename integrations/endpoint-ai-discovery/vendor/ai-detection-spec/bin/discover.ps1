# Collect this Windows machine's agent evidence. bin/discover's scheduled writer, for the
# platform that script does not serve: it is bash.
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File bin\discover.ps1 --write PATH
#     powershell -NoProfile -ExecutionPolicy Bypass -File bin\discover.ps1 --write PATH --status TXT
#     powershell -NoProfile -ExecutionPolicy Bypass -File bin\discover.ps1 --cache PATH
#
# --write PATH    EVERY Windows branch of the pack, each in its own osqueryi, merged into
#                 one payload file. One unavailable table costs one branch, and a dated
#                 kind=scan row says which.
# --status TXT    with --write: the one-line health summary, `ok|degraded <time> rows=N ...`.
# --cache PATH    check the file --write produced and print it. Runs no query.
#
# THE STATEMENTS ARE bin/discover's AND bin/container-scan's: the merge, the payload CTE and
# the status expression. test/lint.sh renders each from both runners and fails when they
# differ, so the two platforms cannot come to mean different things by one payload.
#
# --write PRINTS MESSAGES AND NO PAYLOAD. Windows PowerShell 5.1 re-encodes what a script
# prints, and its `>` writes UTF-16, which nothing here reads. Every byte of the payload
# goes from osqueryi to the file through a redirected handle, and a reader uses the file.
#
# WINDOWS POWERSHELL 5.1, IN ASCII, WITH CMDLETS AND CORE TYPES ONLY. 5.1 is what every
# supported Windows ships, and it reads a script with no byte order mark as ANSI. Where
# AppLocker or WDAC is enforced an unsigned script runs in ConstrainedLanguage mode, which
# refuses Add-Type and every type and method outside its short core list, so nothing here
# reaches for one. CLAUDE.md has the closed list of what this script may call.
#
# No --deep and no --names. osquery reads no container on Windows; runtime-windows.sql
# names an engine found on disk in the `containers` marker instead. Matching on a Windows
# endpoint is dist/agents-windows.sql or Fleet's policies.

Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

$Argv = $args
$Root = Split-Path -Parent $PSScriptRoot
# Overridable so test/discover_windows.ps1 can hand this a pack with a broken query and
# assert the other branches still report.
$Pack = $env:DISCOVER_PACK
if (-not $Pack) { $Pack = Join-Path (Join-Path $Root 'dist') 'ai-detection-spec.conf' }

# One branch's wall clock, as bin/discover bounds it. A branch that cannot finish costs
# one branch, not the inventory.
$BranchSeconds = 30

$Osqi = $null
$RunDir = $null
$StagePaths = @()
$SavedTemp = $null
$SavedTmp = $null
$BoundFired = $false
$Code = 1

function Say([string]$Message) {
    Write-Host "discover: $Message"
}

function Show-Usage {
    Get-Content -LiteralPath $PSCommandPath | Select-Object -Skip 3 -First 9 |
        ForEach-Object { Write-Host ($_ -replace '^# ?', '') }
}

# Every candidate osqueryi: OSQI, where osquery's MSI installs it, then PATH.
function Find-Osqueryi {
    $candidates = @($env:OSQI)
    if ($env:ProgramFiles) {
        $candidates += Join-Path (Join-Path $env:ProgramFiles 'osquery') 'osqueryi.exe'
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    $found = Get-Command -Name osqueryi -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($found) { return $found.Path }
    return $null
}

# A directory of this run's own for the statements and their output, removed on the way
# out. TEMP and TMP point at it meanwhile, because osqueryi leaves a directory of its own
# in TEMP on every exit.
function New-RunDir {
    if (-not $env:TEMP) { return $false }
    $dir = Join-Path $env:TEMP "discover.$(Get-Random)"
    try {
        New-Item -ItemType Directory -Path $dir | Out-Null
    } catch {
        return $false
    }
    $script:RunDir = $dir
    $script:SavedTemp = $env:TEMP
    $script:SavedTmp = $env:TMP
    $env:TEMP = $dir
    $env:TMP = $dir
    return $true
}

function Remove-RunDir {
    foreach ($path in $script:StagePaths) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
    if ($script:RunDir) {
        $env:TEMP = $script:SavedTemp
        $env:TMP = $script:SavedTmp
        Remove-Item -LiteralPath $script:RunDir -Recurse -Force -ErrorAction SilentlyContinue
        $script:RunDir = $null
    }
}

function Use-Osqueryi {
    $script:Osqi = Find-Osqueryi
    if (-not $script:Osqi) {
        Say 'no osqueryi found (set OSQI)'
        return $false
    }
    if (-not (New-RunDir)) {
        Say 'cannot create a working directory'
        return $false
    }
    return $true
}

# UTF-8 with no byte order mark and no added newline, which is what New-Item -Value writes
# and what Set-Content and Out-File cannot in 5.1. A statement carries a payload, and a
# payload carries paths in any script.
function Write-Text([string]$Path, [string]$Text) {
    New-Item -ItemType File -Path $Path -Value $Text -Force | Out-Null
}

function Read-Text([string]$Path) {
    $text = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ($null -eq $text) { return '' }
    return $text
}

# The one escape a single-quoted SQL literal needs.
function ConvertTo-SqlText([string]$Text) {
    return ($Text -replace "'", "''")
}

# osqueryi over a statement file, its output and its errors in files of their own.
#
# THROUGH FILES IN BOTH DIRECTIONS. PowerShell encodes what it pipes to a native program
# as ASCII and decodes what comes back in the console's code page, so a path outside ASCII
# survives neither. A redirected handle carries the bytes.
#
# Returns osqueryi's exit status, or 124 with $BoundFired set when the bound fired.
# THE KILL DECIDES, NOT THE CHILD: a caller discards the output of a run this stopped.
# Zero seconds is no bound, for a statement that reads a document and no table.
# An osqueryi that cannot be started is 127 and a message: a status every caller already
# reads, where an exception would end the run.
function Invoke-Osqueryi([string]$Sql, [string]$Out, [string]$Err, [int]$Seconds, [string[]]$Flags) {
    $script:BoundFired = $false
    try {
        $process = Start-Process -FilePath $script:Osqi -ArgumentList $Flags -NoNewWindow -PassThru `
            -RedirectStandardInput $Sql -RedirectStandardOutput $Out -RedirectStandardError $Err
        # Read once now: a process that exits before its handle is first read reports no
        # exit status.
        $null = $process.Handle
    } catch {
        Say "could not start $($script:Osqi): $($_.Exception.Message)"
        return 127
    }
    if ($Seconds -gt 0) {
        $process | Wait-Process -Timeout $Seconds -ErrorAction SilentlyContinue
        if (-not $process.HasExited) {
            $script:BoundFired = $true
            $process | Stop-Process -Force -ErrorAction SilentlyContinue
            # Stop-Process returns before the process has gone, and until it has, it holds
            # its output file open.
            $process | Wait-Process -Timeout 10 -ErrorAction SilentlyContinue
            return 124
        }
    } else {
        $process | Wait-Process -ErrorAction SilentlyContinue
    }
    return $process.ExitCode
}

# osqueryi's own words for a failure, which is the reason and not only the fact.
function Show-OsqueryiErrors([string]$Err) {
    if (Test-Path -LiteralPath $Err) {
        Get-Content -LiteralPath $Err -Encoding UTF8 -ErrorAction SilentlyContinue |
            ForEach-Object { Write-Host "  osqueryi: $_" }
    }
}

# The pack's Windows branches, in the pack's order, which tools/build.py sorts by name.
# ConvertFrom-Json reads the pack: PowerShell has a JSON parser, where bash needed osqueryi.
function Get-PackBranches([string]$Path) {
    $doc = ConvertFrom-Json -InputObject (Read-Text $Path)
    $branches = @()
    foreach ($entry in $doc.queries.PSObject.Properties) {
        if (@('windows', 'all') -contains $entry.Value.platform) {
            $branches += @{ Name = $entry.Name; Query = $entry.Value.query }
        }
    }
    return , $branches
}

# The statement that merges the per-branch documents into one payload: merge_sql in
# bin/container-scan, which carries the reasoning for each arm. A row is a hashtable of
# Name, Failed (0 or 1) and Doc.
$MergeTail = @'
),
s AS (SELECT name, seq,
        CASE WHEN failed=1 OR NOT json_valid(raw) THEN '[]' ELSE raw END AS doc,
        CASE WHEN failed=1 OR NOT json_valid(raw) THEN 0 ELSE 1 END AS ok
      FROM b)
SELECT kind, id, ver, loc, extra, perms FROM (
  SELECT s.seq AS bseq, 0 AS grp, e.key AS rk,
         json_extract(e.value,'$.kind')  AS kind, json_extract(e.value,'$.id')    AS id,
         json_extract(e.value,'$.ver')   AS ver,  json_extract(e.value,'$.loc')   AS loc,
         json_extract(e.value,'$.extra') AS extra,json_extract(e.value,'$.perms') AS perms
  FROM s, json_each(s.doc) e WHERE json_extract(e.value,'$.kind') IS NOT 'scan'
  UNION ALL
  SELECT s.seq, 1, e.key,
         json_extract(e.value,'$.kind'),  json_extract(e.value,'$.id'),
         json_extract(e.value,'$.ver'),   json_extract(e.value,'$.loc'),
         json_extract(e.value,'$.extra'), json_extract(e.value,'$.perms')
  FROM s, json_each(s.doc) e WHERE json_extract(e.value,'$.kind') = 'scan'
  UNION ALL
  SELECT s.seq, 2, 0, 'scan', s.name, CAST(strftime('%s','now') AS TEXT), '',
         CASE WHEN s.ok=1 THEN 'ok' ELSE 'error' END, ''
  FROM s WHERE NOT EXISTS (
    SELECT 1 FROM json_each(s.doc) e2
    WHERE json_extract(e2.value,'$.kind')='scan'
      AND json_extract(e2.value,'$.id')=s.name)
) ORDER BY bseq, grp, rk;
'@

function Get-MergeSql($Rows) {
    $values = @()
    $seq = 0
    foreach ($row in $Rows) {
        $seq++
        $values += "('$(ConvertTo-SqlText $row.Name)',$seq,$($row.Failed),'$(ConvertTo-SqlText $row.Doc)')"
    }
    return 'WITH b(name, seq, failed, raw) AS (VALUES' + "`n" + ($values -join ",`n") + $MergeTail
}

# A payload as an `ev` CTE and the status expression over it: payload_cte and status_sql in
# bin/discover, which carry the reasoning.
$PayloadCteTail = @'
')), ev AS (SELECT json_extract(e.value,'$.kind') AS kind, coalesce(json_extract(e.value,'$.id'),'') AS id, coalesce(json_extract(e.value,'$.ver'),'') AS ver, coalesce(json_extract(e.value,'$.loc'),'') AS loc, json_extract(e.value,'$.extra') AS extra FROM d, json_each(d.doc) e)
'@

$StatusSql = @'
rtrim((CASE WHEN EXISTS (SELECT 1 FROM ev WHERE kind='scan' AND extra IS NOT 'ok' AND extra IS NOT 'absent') THEN 'degraded' ELSE 'ok' END) || ' ' || strftime('%Y-%m-%dT%H:%M:%SZ','now') || ' rows=' || (SELECT count(*) FROM ev) || ' ' || COALESCE((SELECT group_concat(id || '=' || extra, ' ') FROM (SELECT id, extra FROM ev WHERE kind='scan' ORDER BY id, extra)), ''))
'@

function Get-SummarySql([string]$Doc) {
    return "WITH d(doc) AS (VALUES ('" + (ConvertTo-SqlText $Doc) + $PayloadCteTail + "`n" +
        "SELECT '' AS names, " + $StatusSql + ' AS status;'
}

# The verdict on a cache file, as bin/discover's --cache asks for it: json_valid() and
# json_type() answer `bad` on a malformed document, where json_each() would raise.
function Get-VerdictSql([string]$Doc) {
    return "WITH d(doc) AS (VALUES ('" + (ConvertTo-SqlText $Doc) + "'))" +
        " SELECT CASE WHEN json_valid(doc) AND json_type(doc)='array'" +
        " THEN 'ok' ELSE 'bad' END AS v FROM d;"
}

# One JSON string: escape what JSON requires, then replace any control character still
# standing, as json_str in bin/container-scan does.
function ConvertTo-JsonText([string]$Text) {
    $json = $Text -replace '\\', '\\' -replace '"', '\"'
    $json = $json -replace "`n", '\n' -replace "`r", '\r' -replace "`t", '\t'
    $json = $json -replace '[\x00-\x1f]', '?'
    return '"' + $json + '"'
}

# The kind=scan row for a cache that cannot be read, built here and not by osqueryi: a
# marker row may not depend on anything that could be the thing it reports.
function Get-CacheMarker([string]$Path, [string]$Reason) {
    $epoch = [int64]([datetime]::UtcNow - [datetime]'1970-01-01').TotalSeconds
    return '[{"kind":"scan","id":"inventory","ver":"' + $epoch + '","loc":' +
        (ConvertTo-JsonText $Path) + ',"extra":"' + $Reason + '","perms":""}]'
}

# Beside its destination, so the move into place is a rename on one volume and a reader
# never finds a half-written file.
function New-StagePath([string]$Destination) {
    $path = "$Destination.$(Get-Random).tmp"
    $script:StagePaths += $path
    return $path
}

function Resolve-OutPath([string]$Path) {
    if (-not (Split-Path -Path $Path -IsAbsolute)) {
        $Path = Join-Path (Get-Location).Path $Path
    }
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $Path
}

function Invoke-Cache([string]$Cache) {
    # A MISSING CACHE ANSWERS BEFORE THE osqueryi LOOKUP, on a machine with nothing
    # installed: saying nothing would read as nothing installed here.
    if (-not (Test-Path -LiteralPath $Cache -PathType Leaf)) {
        Say "no readable cache at $Cache -- is the scheduled writer installed?"
        Write-Output (Get-CacheMarker $Cache 'no-cache')
        return
    }
    if (-not (Use-Osqueryi)) { return }
    $doc = Read-Text $Cache
    $sql = Join-Path $script:RunDir 'verdict.sql'
    $out = Join-Path $script:RunDir 'verdict.out'
    Write-Text $sql (Get-VerdictSql $doc)
    $rc = Invoke-Osqueryi $sql $out (Join-Path $script:RunDir 'verdict.err') 0 @('--csv', '--header=false')
    $verdict = ''
    if ($rc -eq 0) { $verdict = (Read-Text $out).Trim() }
    if ($verdict -eq 'ok') {
        Write-Output $doc
        $script:Code = 0
    } elseif ($verdict -eq 'bad') {
        Say "$Cache is not a JSON array. The writer may have been interrupted."
        Write-Output (Get-CacheMarker $Cache 'error')
    } else {
        # A broken validator is not a broken cache, and saying so sends nobody to the file.
        Say "could not validate $Cache -- osqueryi did not answer."
    }
}

function Invoke-Write([string]$Write, [string]$Status) {
    if (-not (Use-Osqueryi)) { return }
    if (-not (Test-Path -LiteralPath $Pack -PathType Leaf)) {
        Say "no $Pack (in a clone, run osquery/tools/build.py)"
        return
    }
    $branches = $null
    try {
        $branches = Get-PackBranches $Pack
    } catch {
        Say "could not read $Pack"
        return
    }
    if ($branches.Count -eq 0) {
        Say "no queries in $Pack for platform windows"
        return
    }

    # ON STDIN, NOT AS AN ARGUMENT: osqueryi reads an argv query that begins with `--` as a
    # command-line flag and returns no rows.
    $rows = @()
    $n = 0
    foreach ($branch in $branches) {
        $n++
        $sql = Join-Path $script:RunDir "branch$n.sql"
        $out = Join-Path $script:RunDir "branch$n.out"
        $err = Join-Path $script:RunDir "branch$n.err"
        Write-Text $sql $branch.Query
        $rc = Invoke-Osqueryi $sql $out $err $BranchSeconds @('--json')
        if ($rc -eq 0) {
            $rows += @{ Name = $branch.Name; Failed = 0; Doc = (Read-Text $out) }
            continue
        }
        # FAILED IS A FLAG, NOT AN EMPTY DOCUMENT: a branch that ran and matched nothing and
        # a branch that never finished would otherwise merge to the same `ok`.
        $rows += @{ Name = $branch.Name; Failed = 1; Doc = '' }
        if ($script:BoundFired) {
            Say "branch '$($branch.Name)' did not complete (no answer in ${BranchSeconds}s)"
        } else {
            Say "branch '$($branch.Name)' did not complete (exit $rc)"
            Show-OsqueryiErrors $err
        }
    }

    $Write = Resolve-OutPath $Write
    $sql = Join-Path $script:RunDir 'merge.sql'
    $err = Join-Path $script:RunDir 'merge.err'
    $stage = New-StagePath $Write
    Write-Text $sql (Get-MergeSql $rows)
    # osqueryi prints "[`n`n]" beside its error on a statement that fails, so the status
    # decides and the output of a failed merge is never published.
    $rc = Invoke-Osqueryi $sql $stage $err 0 @('--json')
    if ($rc -ne 0 -or -not (Test-Path -LiteralPath $stage) -or (Get-Item -LiteralPath $stage).Length -eq 0) {
        Show-OsqueryiErrors $err
        Say "produced no payload; $Write left alone"
        return
    }
    Move-Item -LiteralPath $stage -Destination $Write -Force

    # The status reads back the file a consumer will find, never the rows on their way there.
    if ($Status) {
        $Status = Resolve-OutPath $Status
        $sql = Join-Path $script:RunDir 'status.sql'
        $out = Join-Path $script:RunDir 'status.out'
        Write-Text $sql (Get-SummarySql (Read-Text $Write))
        $rc = Invoke-Osqueryi $sql $out (Join-Path $script:RunDir 'status.err') 0 @('--line')
        $line = ''
        if ($rc -eq 0) {
            foreach ($text in (Get-Content -LiteralPath $out -Encoding UTF8)) {
                if ($text -match '^ *status = (.*)$') { $line = $Matches[1] }
            }
        }
        if ($line) {
            $stage = New-StagePath $Status
            Write-Text $stage ($line + "`n")
            Move-Item -LiteralPath $stage -Destination $Status -Force
        } else {
            # The payload was written and is good; the line is what failed.
            Say "could not summarise $Write; $Status left alone"
        }
    }
    $script:Code = 0
}

function Invoke-Discover($Arguments) {
    $write = ''
    $status = ''
    $cache = ''
    $i = 0
    while ($i -lt $Arguments.Count) {
        $flag = ([string]$Arguments[$i]) -replace '^--', '-'
        if ($flag -eq '-h' -or $flag -eq '-help') {
            Show-Usage
            $script:Code = 0
            return
        }
        if (@('-write', '-status', '-cache') -notcontains $flag) {
            Say "unknown argument: $($Arguments[$i]). This script takes --write, --status and --cache."
            return
        }
        if ($i + 1 -ge $Arguments.Count -or -not [string]$Arguments[$i + 1]) {
            Say "$($Arguments[$i]) needs a path"
            return
        }
        $value = [string]$Arguments[$i + 1]
        if ($flag -eq '-write') { $write = $value }
        elseif ($flag -eq '-status') { $status = $value }
        else { $cache = $value }
        $i += 2
    }
    if ($cache -and $write) {
        Say '--cache and --write are opposite ends of the same pipe; pick one'
        return
    }
    if ($status -and -not $write) {
        Say '--status needs --write'
        return
    }
    if (-not $cache -and -not $write) {
        Show-Usage
        return
    }
    # The pack's Windows branches name tables no other platform has, so anywhere else most
    # of them would fail and the payload would be a list of `error` markers.
    if ($env:OS -ne 'Windows_NT') {
        Say 'this script serves Windows. On macOS and Linux, run bin/discover.'
        return
    }
    if ($cache) { Invoke-Cache $cache } else { Invoke-Write $write $status }
}

# Dot-sourced, this defines the functions and runs nothing, which is how test/lint.sh and
# test/discover_windows.ps1 reach the statements.
if ($MyInvocation.InvocationName -eq '.') { return }

try {
    Invoke-Discover $Argv
} catch {
    Say $_.Exception.Message
    $Code = 1
} finally {
    Remove-RunDir
}
exit $Code
