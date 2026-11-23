#!/usr/bin/env python3
"""Pack the runner and its artifacts into ONE self-contained file an MDM can host.

    tools/bundle.py --platform darwin
    tools/bundle.py --platform linux --out /tmp/ai-detection-spec.sh
    tools/bundle.py --platform windows
    tools/bundle.py --platform darwin --driver my-driver.sh
    tools/bundle.py --platform darwin --check artifacts/ai-detection-spec-darwin.sh

WHAT PROBLEM THIS SOLVES. A release ships bin/ and dist/ as loose files, and the release
notes have to warn that they will not find each other unless they are laid out as they are
in the repo: bin/container-scan resolves dist/discovery-deep.sql relative to its own parent,
and bin/discover sources bin/container-scan. Placing files on disk in a fixed layout is
exactly what a management platform is worst at -- it wants a package, which wants code
signing, notarization and on macOS a PPPC profile. What every one of them CAN do is host a
script and run it on a schedule. So: one script, with the layout inside it.

    $ ./ai-detection-spec-darwin.sh --write /var/lib/ai-detection-spec/inventory.json \
                                    --status /var/lib/ai-detection-spec/status.txt

Every argument is passed through to bin/discover, so everything in docs/deployment.md works
unchanged. It INSTALLS NOTHING: the payload is extracted to a private temp directory, run,
and removed.

THE WINDOWS BUNDLE IS POWERSHELL AROUND bin/discover.ps1, and its payload is plain text in
comment lines. Where AppLocker or WDAC is enforced an unsigned script runs in
ConstrainedLanguage mode, which has no base64 decoder and no archive reader, so a payload
packed as the POSIX one is could not be unpacked on the machines that most need one file.
It adds no prerequisite: what bin/discover.ps1 needs is enough to unpack it.

ON macOS AND LINUX IT ADDS TWO PREREQUISITES, AND THAT IS THE ONE THING TO KNOW BEFORE
USING IT. bin/discover and bin/container-scan hold to a closed list of utilities (CLAUDE.md
names it) so that what the endpoint needs is what a stock machine has. The extraction
preamble below adds `base64` and `tar` to that list. Both ship with macOS and with every Linux base image this repo has
run on, and the cost is opt-in -- a consumer who unpacks bin/ and dist/ themselves pays
neither -- but it is a real widening and it is not hidden in a comment.

NOT IN THE PAYLOAD: catalog/ AND bin/classify. The endpoint enumerates; matching happens off
the machine, which is what lets a new signature re-match evidence already collected, and
nothing here can read a catalog file anyway. Asserted below rather than remembered, because
inside a base64 blob it would be invisible.

IN THE PAYLOAD, AND A DELIBERATE EXCEPTION: dist/signatures.sql, the catalog RENDERED into
SQL by tools/render_match.py. It is what `bin/discover --names` matches with, and --names
exists because an Extension Attribute is one printed value a Smart Group matches on -- a
machine that can only host this script and read one line back needs the names on the
machine. The rendered file reaches an endpoint only by redeploying the bundle, which is the
trade the JSON payload avoids and the one line cannot.

--driver IS THE HOOK FOR A WRAPPER, and it exists because the alternative is worse. A
consumer whose reporting channel needs its own framing, its own size budget or its own
output paths would otherwise fork this file or rebuild the bundle by hand. Given a driver,
the bundle runs THAT with `AI_DETECTION_SPEC_ROOT` set to the extracted tree and the arguments
passed through. What the driver does with them is none of this repo's business -- which is
the point of the seam, and why nothing product-specific appears anywhere in this file.

No dependencies. Python is a BUILD-time tool here; nothing it emits needs an interpreter.
"""
import argparse
import base64
import gzip
import io
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLATFORMS = ("darwin", "linux", "windows")
UNAME = {"darwin": "Darwin", "linux": "Linux"}
# The bundle a POSIX bundle's refusal names: the other one bin/discover serves.
OTHER = {"darwin": "linux", "linux": "darwin"}

# WHAT THE RUNNER ACTUALLY OPENS, and no more. bin/discover reads the composed artifact for
# its platform, the deep artifact through bin/container-scan, and the pack (DISCOVER_PACK)
# to get one named query per branch on the --write path. Everything else in the repo is for
# a reader, a maintainer or a test.
#
# ONE PLATFORM PER BUNDLE. The composed artifacts name disjoint sets of tables and
# bin/discover picks by `uname -s`, so a bundle carrying both would be a file that claims
# two platforms and is tested on whichever one built it. Two files, each refusing by name,
# is the honest shape.
#
# WINDOWS CARRIES TWO FILES. bin/discover.ps1 has no composed mode and no --names, so the
# pack is all it opens.
def payload_files(platform):
    if platform == "windows":
        return ("bin/discover.ps1", "dist/ai-detection-spec.conf")
    return ("bin/discover", "bin/container-scan",
            f"dist/discovery-{platform}.sql", "dist/discovery-deep.sql",
            "dist/ai-detection-spec.conf", "dist/signatures.sql")

FORBIDDEN = ("catalog/", "agents.yaml", "routes.yaml", "catalog.json", "bin/classify")

MARKER = "AI_DETECTION_SPEC_PAYLOAD_EOF"

WRAPPER = r"""#!/bin/bash
# GENERATED by osquery/tools/bundle.py from ai-detection-spec. Do not edit; rebuild.
# platform: @PLATFORM@@LABEL@
# carries:  @FILES@
#
# Collect this machine's agent evidence. One file, no installation: the payload below is
# extracted to a private temp directory, run, and deleted. Arguments are passed straight
# through to bin/discover, so:
#
#     ./this-file --write /var/lib/ai-detection-spec/inventory.json \
#                 --status /var/lib/ai-detection-spec/status.txt
#
# DO NOT PUT THIS ON A SYNCHRONOUS REPORTING PATH. docker_images has no timeout of its own,
# and against a daemon that accepts the connection and never answers, the query does not
# return. Run it on a schedule and read the file it writes. See osquery/docs/deployment.md.
#
# NEEDS base64 AND tar on top of what bin/discover needs. Both are stock on macOS and on
# every Linux base image this repo has run on; unpacking bin/ and dist/ yourself needs
# neither.
set -uo pipefail

# ONE PLATFORM PER BUNDLE, AND IT REFUSES BY NAME. bin/discover picks its artifact from
# `uname -s`; on the other platform this bundle would die on a missing path, and the
# message would be about a file when the truth is about the build. The composed artifacts
# name disjoint sets of tables, so there is no bundle that runs on both.
case "$(uname -s)" in
  @UNAME@) ;;
  *) echo "ai-detection-spec: this bundle carries dist/discovery-@PLATFORM@.sql and runs on" \
          "@UNAME@ only. Use the @OTHER@ bundle -- every release attaches one per" \
          "platform -- or build it with osquery/tools/bundle.py --platform @OTHER@." >&2
     exit 1 ;;
esac

# TMPDIR is not guaranteed for a script run by a management agent, and /var/tmp outlives a
# cleared /tmp.
work="$(mktemp -d "${TMPDIR:-/var/tmp}/ai-detection-spec.XXXXXX")" || {
  echo "ai-detection-spec: cannot create a working directory" >&2; exit 1; }
trap 'rm -rf "$work"' EXIT HUP INT TERM

cat > "$work/payload.b64" <<'@MARKER@'
@PAYLOAD@
@MARKER@

# BSD base64 decodes with -D, GNU with -d, and GNU's -i means something else entirely
# (ignore garbage). Read from a FILE rather than a pipe, so the fallback can retry: a
# consumed pipe cannot be read twice, and the first form failing is the normal case on
# exactly half the platforms this repo supports.
base64 -D -i "$work/payload.b64" -o "$work/payload.tgz" 2>/dev/null \
  || base64 -d "$work/payload.b64" > "$work/payload.tgz" 2>/dev/null \
  || { echo "ai-detection-spec: could not decode the embedded payload" >&2; exit 1; }

tar -xzf "$work/payload.tgz" -C "$work" || {
  echo "ai-detection-spec: could not unpack the embedded payload" >&2; exit 1; }
chmod +x "$work/bin/"* 2>/dev/null

# RUN, DO NOT exec. `exec` replaces this shell, and a replaced shell does not run its EXIT
# trap -- verified, not assumed: the extracted tree is then left in TMPDIR. On a schedule
# that is one copy of the payload per run, and it surfaces months later as a full volume
# rather than as anything to do with this script.
#
# A SIGNAL ARRIVES LATE HERE, AND THAT IS THE TRADE. bash defers a trap until the
# foreground command returns, so a TERM sent to this shell ALONE does not stop the runner.
# Measured: TERM at t+1 against an 8s runner ran the cleanup at t+8, when the runner
# finished, not on arrival. Nothing leaks -- HUP, INT and TERM are trapped, so the shell
# leaves through EXIT and the tree goes either way -- and a signal sent to the process
# group, which is what both a terminal and a scheduler send, reaches the runner directly.
#
# The alternative is to background the runner, wait on its pid and forward signals to its
# group. NOT DONE, DELIBERATELY. Backgrounding WITHOUT forwarding is strictly worse: the
# trap fires immediately and deletes the tree out from under a process still reading its
# own SQL. Forwarding properly means a signal supervisor in bash 3.2 -- re-waiting around
# interrupted waits, an escalation timer -- inside the one file that has to work on every
# managed machine, to shorten a cleanup that already happens. The bound that actually
# matters is a wall-clock kill on a query that can block forever, and it exists one level
# down in bin/container-scan, where a second copy of it does not belong.
@RUN@
status=$?
exit "$status"
"""

RUN_DEFAULT = '"$work/bin/discover" "$@"'

# The driver gets the tree's location and the arguments, and owns everything after that:
# output paths, any framing its reporting channel needs, its own exit status. It is stored
# under a fixed name so this wrapper does not have to know what the file was called.
RUN_DRIVER = ('AI_DETECTION_SPEC_ROOT="$work" "$work/driver" "$@"')

WRAPPER_PS = r"""# GENERATED by osquery/tools/bundle.py from ai-detection-spec. Do not edit; rebuild.
# platform: @PLATFORM@@LABEL@
# carries:  @FILES@
#
# Collect this Windows machine's agent evidence. One file, no installation: the payload at
# the end of this file is extracted to a private temp directory, run, and deleted.
# Arguments are passed straight through to bin\discover.ps1, so:
#
#     powershell -NoProfile -ExecutionPolicy Bypass -File this-file.ps1 `
#         --write C:\ProgramData\ai-detection-spec\inventory.json `
#         --status C:\ProgramData\ai-detection-spec\status.txt
#
# RUN IT AS A FILE, on a schedule, and read the file it writes. It reads its payload out of
# itself, so it cannot be piped into powershell or run through Invoke-Expression. See
# osquery/docs/deployment.md.
#
# NEEDS NOTHING bin\discover.ps1 DOES NOT: Windows PowerShell 5.1, with cmdlets and core
# types only, so it runs unsigned in ConstrainedLanguage mode as that script does.
$ErrorActionPreference = 'Stop'

# ONE PLATFORM PER BUNDLE, AND IT REFUSES BY NAME. Windows PowerShell runs on Windows alone;
# PowerShell 7 also runs where bin/discover is the runner, and there every branch of the
# pack this carries would fail.
if ($env:OS -ne 'Windows_NT') {
    Write-Host ('ai-detection-spec: this bundle carries bin\discover.ps1 and runs on Windows ' +
        'only. Use the darwin or the linux bundle -- every release attaches one per ' +
        'platform -- or build it with osquery/tools/bundle.py --platform darwin, or linux.')
    exit 1
}
if (-not $PSCommandPath) {
    Write-Host ('ai-detection-spec: run this file with powershell -File. It reads its ' +
        'payload out of itself.')
    exit 1
}
if (-not $env:TEMP) {
    Write-Host 'ai-detection-spec: TEMP is not set, so there is nowhere to unpack the payload'
    exit 1
}

$work = Join-Path $env:TEMP "ai-detection-spec.$(Get-Random)"
$savedRoot = $env:AI_DETECTION_SPEC_ROOT
$code = 1
try {
    $unpacked = $false
    try {
        New-Item -ItemType Directory -Path $work | Out-Null

        # THE PAYLOAD IS COMMENT LINES after the marker at the end of this file: `#:` names
        # a file, and each `#|` line after it is one line of that file. Comments, so that no
        # payload line can end a quoted string early.
        $files = @{}
        $member = $null
        $lines = @()
        $inPayload = $false
        foreach ($line in (Get-Content -LiteralPath $PSCommandPath -Encoding UTF8)) {
            if (-not $inPayload) {
                if ($line -eq '# @MARKER@') { $inPayload = $true }
                continue
            }
            if ($line.StartsWith('#:')) {
                if ($member) { $files[$member] = $lines }
                $member = $line.Substring(2)
                $lines = @()
            } elseif ($line.StartsWith('#|')) {
                $lines += $line.Substring(2)
            }
        }
        if ($member) { $files[$member] = $lines }
        if ($files.Count -eq 0) { throw 'it carries no payload' }

        foreach ($member in $files.Keys) {
            $path = $work
            foreach ($part in ($member -split '/')) { $path = Join-Path $path $part }
            # A script PowerShell will run needs the extension; the payload stores the
            # driver under one fixed name on every platform.
            if ($member -eq 'driver') { $path = "$path.ps1" }
            $dir = Split-Path -Parent $path
            if (-not (Test-Path -LiteralPath $dir)) {
                New-Item -ItemType Directory -Path $dir | Out-Null
            }
            # New-Item -Value writes no byte order mark, which Set-Content cannot in 5.1.
            New-Item -ItemType File -Path $path -Value (($files[$member] -join "`n") + "`n") |
                Out-Null
        }
        $unpacked = $true
    } catch {
        Write-Host "ai-detection-spec: could not unpack the embedded payload: $($_.Exception.Message)"
    }

    if ($unpacked) {
        # A script that ends without `exit` leaves this as it found it.
        $global:LASTEXITCODE = 0
@RUN@
        $code = $LASTEXITCODE
    }
} finally {
    $env:AI_DETECTION_SPEC_ROOT = $savedRoot
    if (Test-Path -LiteralPath $work) {
        Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
    }
}
exit $code

# @MARKER@
@PAYLOAD@"""

RUN_DEFAULT_PS = "        & (Join-Path (Join-Path $work 'bin') 'discover.ps1') @args"

# As RUN_DRIVER: the driver gets the tree's location and the arguments, and owns the rest.
RUN_DRIVER_PS = ("        $env:AI_DETECTION_SPEC_ROOT = $work\n"
                 "        & (Join-Path $work 'driver.ps1') @args")


def _member_paths(root, platform, driver=None):
    """(name in the payload, file on disk) for every member, sorted by name."""
    members = [(rel, root / rel) for rel in payload_files(platform)]
    if driver:
        members.append(("driver", pathlib.Path(driver)))
    for _, path in sorted(members):
        if not path.is_file():
            sys.exit(f"bundle: {path} is missing. Run osquery/tools/build.py, or check "
                     f"--platform: the composed artifacts are per platform and a "
                     f"rename will not come back by rebuilding the same ref.")
    return sorted(members)


def payload_tar(root, platform, driver=None):
    """The payload, as tar bytes. BYTE-REPRODUCIBLE ACROSS MACHINES, which the compressed
    form is not: tar records mtimes, uids, modes and entry order, and every one of them is
    pinned here. A release attaches a bundle and a consumer may commit one; both want the
    same input to keep producing the same file."""
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        for arcname, path in _member_paths(root, platform, driver):
            info = tar.gettarinfo(str(path), arcname=arcname)
            info.mtime, info.uid, info.gid = 0, 0, 0
            info.uname = info.gname = ""
            info.mode = 0o755 if arcname.startswith("bin/") or arcname == "driver" else 0o644
            with path.open("rb") as fh:
                tar.addfile(info, fh)
    return raw.getvalue()


def wrapper(platform, files, driver=None, label=""):
    """The shell around the payload, with no payload in it yet."""
    # A LABEL LANDS IN A COMMENT LINE, so a newline in it ends that comment and everything
    # after it is shell -- in a file that still looks exactly like a bundle, which is this
    # project's worst failure shape. A git ref cannot carry a control character, so a
    # release tag cannot reach this; `--label "$(some command)"` from a human can.
    # Refused HERE rather than in main() so that every caller is covered, --check included.
    if any(c in label for c in "\r\n"):
        sys.exit("bundle: --label must not contain a newline. It is interpolated into a "
                 "comment line in the generated wrapper, and a newline there turns the "
                 "rest of the label into shell.")
    if platform == "windows":
        return (WRAPPER_PS
                .replace("@PLATFORM@", platform)
                .replace("@LABEL@", f"  release: {label}" if label else "")
                .replace("@FILES@", " ".join(files) + (" + driver" if driver else ""))
                .replace("@MARKER@", MARKER)
                .replace("@RUN@", RUN_DRIVER_PS if driver else RUN_DEFAULT_PS))
    return (WRAPPER
            .replace("@PLATFORM@", platform)
            .replace("@OTHER@", OTHER[platform])
            .replace("@UNAME@", UNAME[platform])
            .replace("@LABEL@", f"  release: {label}" if label else "")
            .replace("@FILES@", " ".join(files) + (" + driver" if driver else ""))
            .replace("@MARKER@", MARKER)
            .replace("@RUN@", RUN_DRIVER if driver else RUN_DEFAULT))


def payload_lines(root, platform, driver=None):
    """The Windows payload: every member as comment lines, `#:<name>` then one `#|<line>`
    per line of the file.

    A MEMBER MUST SURVIVE THE ROUND TRIP, so one that cannot is refused here. The wrapper
    reads lines and writes them back joined by a newline, which loses a carriage return and
    a missing final newline. And Windows PowerShell 5.1 reads a script with no byte order
    mark as ANSI, where a byte outside ASCII is another character."""
    out = []
    for arcname, path in _member_paths(root, platform, driver):
        data = path.read_bytes()
        why = ("holds a byte outside ASCII" if any(b > 127 for b in data) else
               "holds a carriage return" if b"\r" in data else
               "does not end in a newline" if not data.endswith(b"\n") else "")
        if why:
            sys.exit(f"bundle: {path} {why}, and the Windows bundle carries its files as "
                     f"ASCII lines, each ending in a newline.")
        out.append("#:" + arcname)
        out.extend("#|" + line for line in data.decode("ascii").split("\n")[:-1])
    return "\n".join(out) + "\n"


def build(root, platform, driver=None, label=""):
    """One file: the wrapper, with the payload inside it. base64 of a gzipped tar in the
    shell wrapper, comment lines in the PowerShell one."""
    if platform == "windows":
        return (wrapper(platform, list(payload_files(platform)), driver, label)
                .replace("@PAYLOAD@", payload_lines(root, platform, driver)))
    blob = base64.b64encode(gzip.compress(payload_tar(root, platform, driver), 9, mtime=0))
    b64 = blob.decode()
    wrapped = "\n".join(b64[i:i + 76] for i in range(0, len(b64), 76))
    files = list(payload_files(platform))
    return wrapper(platform, files, driver, label).replace("@PAYLOAD@", wrapped)


PAYLOAD_OPEN = "<<'" + MARKER + "'\n"
PAYLOAD_CLOSE = "\n" + MARKER + "\n"


def _split(text):
    """(everything before the payload, the base64 body, everything after it)."""
    open_at = text.index(PAYLOAD_OPEN) + len(PAYLOAD_OPEN)
    close_at = text.index(PAYLOAD_CLOSE, open_at)
    return text[:open_at], text[open_at:close_at], text[close_at:]


class CorruptBundle(Exception):
    """A bundle's payload could not be decoded into the files it is supposed to be."""


PS_PAYLOAD_OPEN = "\n# " + MARKER + "\n"


def _is_ps(text):
    """Is this the PowerShell bundle? The shell bundle opens with a shebang and this one
    never does, and its payload marker is a comment line of its own."""
    return not text.startswith("#!") and PS_PAYLOAD_OPEN in text


def _ps_split(text):
    """(the wrapper up to and including the marker line, the payload lines)."""
    open_at = text.index(PS_PAYLOAD_OPEN) + len(PS_PAYLOAD_OPEN)
    return text[:open_at], text[open_at:]


def _ps_members(text):
    """Every file in a PowerShell bundle's payload, as {name: bytes}, or CorruptBundle.

    STRICTER THAN THE WRAPPER, which skips a line it does not know. A line that is neither
    a name nor a line of a file means this is not the payload that was built, and a reader
    that skipped it would report the files around the damage as the whole."""
    _, body = _ps_split(text)
    lines = body.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    members, name = {}, None
    for line in lines:
        if line.startswith("#:"):
            name = line[2:]
            members[name] = []
        elif line.startswith("#|") and name is not None:
            members[name].append(line[2:])
        else:
            raise CorruptBundle(f"a payload line is neither a file's name nor a file's "
                                f"line: {line[:40]!r}")
    if not members:
        raise CorruptBundle("the payload names no file")
    return {n: ("\n".join(ls) + "\n").encode() for n, ls in members.items()}


def _payload_bytes(text):
    """The decompressed payload of a bundle, or CorruptBundle.

    ONE EXCEPTION FOR A CLASS OF FAILURE, BECAUSE ENUMERATING THEM HAS BEEN WRONG THREE
    TIMES. The callers used to list the types they expected from base64 and gzip, and the
    list was short every time: first OSError and ValueError, then EOFError (a TRUNCATED
    payload, which is what a half-copied file is) and tarfile.TarError, then zlib.error,
    which inherits straight from Exception and is what malformed DEFLATE raises -- three of
    four ways of corrupting a stream produce it. Each round was a traceback where the
    caller had promised an answer.

    So the catch is broad and the SCOPE is narrow: two stdlib calls on bytes a caller
    supplied. Anything either of them raises means one thing -- this is not a payload --
    and there is nothing else in here for a broad catch to hide. payload_tar() and the
    comparison stay outside it, where a real defect still surfaces as one.

    _split() IS INSIDE THE TRY, and was not. A file with no payload marker is not a bundle,
    which is the same answer as a bundle whose payload will not decode -- but it arrived as
    a bare ValueError through read_member() while every other failure arrived as
    CorruptBundle. The first consumer to hand this a wrong path got a traceback for the
    commonest mistake there is, and a caller cannot be asked to catch two things to learn
    one thing.
    """
    try:
        _, body, _ = _split(text)
    except ValueError as exc:
        # NAMED, BECAUSE THIS IS THE COMMONEST MISTAKE AND THE LEAST INFORMATIVE ERROR.
        # str.index raises "substring not found", which tells a caller nothing about what
        # it handed over. The likeliest cause by far is the wrong path.
        raise CorruptBundle(f"no {MARKER} marker -- this is not a bundle") from exc
    try:
        return gzip.decompress(base64.b64decode(body))
    except Exception as exc:
        raise CorruptBundle(f"{type(exc).__name__}: {exc}") from exc


def read_member(text, name):
    """One file out of a built bundle, by its name in the payload.

    PUBLIC BECAUSE A CONSUMER ALREADY NEEDS IT, and was reaching past the underscore to get
    it. A wrapper built with --driver puts the consumer's own script inside the payload, so
    every check that consumer had which used to grep its own script -- is the frame still
    there, is the size cap still enforced -- now has to read the member back. The first
    repo to adopt --driver wrote that against `_split`, which is exactly the shape of the
    breakage this project has already shipped once: `bin/discover --framed` was removed
    here for good reasons and took a downstream consumer with it. An interface a consumer
    must use is an interface this repo maintains, and the way to make that true is to say
    so rather than to hope.

    Returns bytes. A name that is not in the payload raises KeyError, so a caller asking
    for the wrong thing is told, rather than handed an empty string it will treat as a file
    that exists and is empty.
    """
    import io
    if _is_ps(text):
        members = _ps_members(text)
        if name not in members:
            raise KeyError(f"{name!r} is not a file in this bundle's payload; it carries "
                           f"{sorted(members)}")
        return members[name]
    try:
        tar = tarfile.open(fileobj=io.BytesIO(_payload_bytes(text)))
    except tarfile.TarError as exc:
        raise CorruptBundle(f"{type(exc).__name__}: {exc}") from exc
    try:
        member = tar.extractfile(name)
    except KeyError:
        member = None
    if member is None:
        # tarfile raises its own KeyError first, whose message names only what was asked
        # for. Saying what IS in there turns "not found" into an answer: a caller reading
        # `driver` out of a bundle built without one needs to know that is why.
        raise KeyError(f"{name!r} is not a file in this bundle's payload; it carries "
                       f"{sorted(tar.getnames())}")
    return member.read()


def matches(text, root, platform, driver=None, label=""):
    """Does an existing bundle carry this tree?

    COMPARED BY MEANING, NOT BY BYTES. zlib's output is not identical across zlib versions,
    so a byte comparison can pass on the machine that built the bundle and fail on a CI
    runner against the same content -- a gate that fails at random, which trains people to
    re-run it, after which a real failure gets re-run too. The wrapper is compared as text
    and the payload DECOMPRESSED, where the tar is reproducible by construction. Which
    bytes zlib chose is not a fact about this repo.
    """
    if platform == "windows":
        # The same two questions, asked of text: is the wrapper the one this tree builds,
        # and does the payload hold these files.
        want = wrapper(platform, list(payload_files(platform)), driver, label)
        if not _is_ps(text) or _ps_split(text)[0] != _ps_split(want)[0]:
            return False
        try:
            members = _ps_members(text)
        except CorruptBundle:
            return False
        return members == {name: path.read_bytes()
                           for name, path in _member_paths(root, platform, driver)}
    try:
        head, _, tail = _split(text)
        want = wrapper(platform, list(payload_files(platform)), driver, label)
        want_head, _, want_tail = _split(want)
    except ValueError:
        return False
    if (head, tail) != (want_head, want_tail):
        return False
    try:
        payload = _payload_bytes(text)
    except CorruptBundle:
        # CORRUPT IS "DOES NOT MATCH", WHICH IS THIS FUNCTION'S WHOLE QUESTION. This is what
        # --check calls and what a consumer's own gate calls, so raising here crashed the
        # gate instead of reporting the artifact as not carrying the tree -- and "the check
        # blew up" and "the check says no" are different answers to someone deciding
        # whether to ship.
        return False
    # OUTSIDE the catch on purpose: a missing vendored file is this repo's problem, not a
    # corrupt bundle, and it should not be able to read as "does not match".
    return payload == payload_tar(root, platform, driver)


def main():
    """Build a bundle, or check that an existing one still carries this tree."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--platform", choices=PLATFORMS, required=True)
    ap.add_argument("--out", help="default: artifacts/ai-detection-spec-<platform>.sh, "
                                  "or .ps1 for windows")
    ap.add_argument("--driver", help="run this instead of bin/discover, with "
                                     "AI_DETECTION_SPEC_ROOT pointing at the extracted tree")
    ap.add_argument("--label", default="", help="a release name, recorded in the banner")
    ap.add_argument("--check", metavar="PATH",
                    help="fail unless PATH already carries this tree; writes nothing")
    ap.add_argument("--member", nargs=2, metavar=("NAME", "PATH"),
                    help="print one file out of a built bundle, e.g. --member driver ./b.sh")
    args = ap.parse_args()

    # READING A BUNDLE BACK IS PART OF THE INTERFACE, not a debugging convenience. A
    # consumer using --driver has checks that used to grep its own script and now have to
    # reach into the payload; giving them a command means they do not reach into `_split`.
    if args.member:
        name, path = args.member
        try:
            sys.stdout.buffer.write(read_member(pathlib.Path(path).read_text(), name))
        except KeyError as exc:
            sys.exit(f"bundle: {exc}")
        except CorruptBundle as exc:
            # Every way a payload can be wrong arrives here as one thing, named rather than
            # raised: bad base64, bad gzip magic, a truncated payload, malformed DEFLATE, or
            # a blob that ungzips to something that is not a tar.
            sys.exit(f"bundle: {path} is not a bundle this can read: {exc}")
        except (OSError, ValueError) as exc:
            sys.exit(f"bundle: cannot read {path}: {exc}")
        return

    # THE CATALOG MUST NOT REACH AN ENDPOINT. One line here, and the failure it prevents --
    # a machine carrying the signatures it is supposed to enumerate past -- would be
    # invisible in a base64 blob.
    listed = list(payload_files(args.platform)) + ([args.driver] if args.driver else [])
    for f in listed:
        if any(bad in f for bad in FORBIDDEN):
            sys.exit(f"bundle: {f} is not endpoint material. The endpoint enumerates and "
                     f"matches nothing; matching happens in bin/classify, off the machine.")

    if args.check:
        path = pathlib.Path(args.check)
        if not path.exists():
            sys.exit(f"bundle: {path} does not exist. Run osquery/tools/bundle.py --platform "
                     f"{args.platform}.")
        if not matches(path.read_text(), ROOT, args.platform, args.driver, args.label):
            sys.exit(f"bundle: {path} does not carry this tree. Rebuild it.")
        print(f"{path} is up to date ({args.platform})")
        return

    ext = "ps1" if args.platform == "windows" else "sh"
    out = pathlib.Path(args.out) if args.out else \
        ROOT.parent / "artifacts" / f"ai-detection-spec-{args.platform}.{ext}"
    out.parent.mkdir(parents=True, exist_ok=True)
    # As bytes: text mode on Windows writes every newline as CRLF.
    out.write_bytes(build(ROOT, args.platform, args.driver, args.label).encode())
    out.chmod(0o755)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB, {len(listed)} files, "
          f"{args.platform})")


if __name__ == "__main__":
    main()
