# Tests

```bash
test/lint.sh                   # static checks, ~1s; no VM, no network, no osquery
test/run-collector.sh          # run this platform's collector and assert on it, ~15s; needs osquery
test/run-guest-attributes.sh   # the Compute Engine reporter against a fake metadata server, ~3s
test/run-ssm-inventory.sh      # the EC2 reporter against a fake IMDS, ~6s
```

`lint.sh` **reads** the deployable and `run-collector.sh` **runs** it. Both are needed, because
no static check exercises the extraction code inside `dist/collect.sh`.

These tests cover what this tree owns: the build, the `arthur1.` framing, the size budget and
the carriers. The queries, the runner, the Docker health guard and the wall-clock bound belong
to [`osquery-ai-discovery`](https://github.com/arthur-ai/osquery-ai-discovery), and so do their
tests. **Do not re-create that suite here.** A local copy would test a local query rather than
what a fleet receives.

## `test/lint.sh`

| Guard | What it catches |
|---|---|
| No `.sql`, no `osqueryi` call, no plaintext query outside `vendor/` | A second discovery implementation reappearing |
| `build-collector.py --check` | `dist/collect.sh` built before the last `tools/vendor-queries.sh` |
| Payload files admitted by name (`ENDPOINT_FILES` in `tools/build-collector.py`, run through `--check`) | A file upstream adds to its bundle reaching endpoints unvetted, catalog-derived ones above all |
| No `agents.yaml`, no `catalog/` in the built collector | The catalog reaching a Mac. The endpoint enumerates and matches nothing |
| No `--names` in the driver | Matching on the endpoint. The bundle carries `dist/signatures.sql` for it, unread |
| One `ARTHUR_PAYLOAD_EOF` pair | The collector embedding a previous copy of itself |
| Every flag either collector passes to `bin/discover`, in every call, is still accepted | A vendor bump removing a flag. This has happened: upstream deleted `--framed`, correctly, and the collector called it |
| Both builds checked by every collector guard | A guard proving one build and saying nothing about the other's bytes |
| `CAP` at most 262,144 | The budget rising past what a Compute Engine guest attribute accepts, so GCE's 400 would fire before our `ERROR:oversize` |
| The units: a oneshot running the reporter as root; a timer with `OnBootSec` and `OnUnitActiveSec`, wanted by `timers.target` | A VM that never runs the scan, or reports nothing for its first hour |
| The unit, the reporter and the collector agree on one install directory | Every VM failing its first run on a missing path |
| No interpreter in the reporter; upstream still prints `no osqueryi found` | The reporter needing more than the collector does; `osquery=absent` silently never firing after a vendor bump |
| The OS policy installs each of the four files where the unit, the reporter or systemd runs it, from its URL in this tree | A VM whose policy reads compliant and whose first run fails on a missing path; a file with no copy here to pin a checksum to |
| `tools/render-os-policy.sh HEAD` leaves no placeholder and pins each file to its own sha256 | A rendered policy every VM refuses. Skipped, and says so, until the policy is committed: the renderer reads git |
| The EC2 drop-in clears `ExecStart` before setting it, and runs `report-ssm-inventory.sh` from the reporter's directory; that reporter runs the same collector and calls no interpreter | An instance that also runs the guest-attribute reporter, and fails every run |
| The EC2 reporter's `PART` is at most 4,096 and equals the reader's part size, and its type name, attribute names and budget match ml-engine's `cloud/ec2/client.py` | A part the SSM Agent skips without saying so; values the reader refuses; every instance reading as never reported after a rename on one side |
| The EC2 install script in `docs/mdm/ec2.md` is POSIX `sh`: no bashism, and `dash -n` accepts it where dash is installed | Every Ubuntu instance failing section 02 with `Illegal option -o pipefail`, while Amazon Linux, where `sh` is bash, passes. Measured |
| `arthur1.` and `ERROR:oversize` present | The framing or its over-cap reason being dropped, which leaves an empty attribute — indistinguishable from a Mac with no AI tools on it |
| `bash -n` on both collectors, the reporter and `vendor-queries.sh` | A template edit in `build-collector.py` producing a syntax error nobody runs until a Policy does |
| Vendored `VERSION` exists; `PROVISIONAL` is announced | A commit pin becoming permanent by inattention |
| The plist runs `collect.sh` with `RunAtLoad` | A fresh Mac reporting nothing until the first interval elapses |
| `DOCKER_PING_TIMEOUT` ≥ 10 **and** ≥ the vendored default | A cold Docker reported as `unhealthy:000`. The second half catches an upstream bump crossing our value, after which the export would lower the bound instead of raising it |
| No interpreter in the collector's own code | The framing step reaching for `python3` again. `/usr/bin/python3` is a shim that fails without Command Line Tools, silently |
| The payload's real prerequisites match the runbook's table | Docs claiming the endpoint needs less than it does. This shipped once: the collector's own code was interpreter-free while the vendored runner called `python3` in ten places, invisible because the payload is base64 |

The `no second implementation` guard is mutation-tested by construction — drop a `.sql`
file anywhere outside `vendor/`, add a script that shells out to `osqueryi`, or paste
`FROM apps` into a `.py`, and it names the file and fails.

## `test/run-collector.sh`

Runs this platform's build — `dist/collect.sh` on macOS, `dist/collect-linux.sh` on Linux —
three times into a scratch directory and asserts on what it wrote. Root is not required — a Policy runs it as root and sees more rows, but nothing asserted here
depends on that.

| Guard | What it catches |
|---|---|
| `collect.sh` exits 0 and writes all three files | The preamble failing to extract or run at all — `base64 -D` vs `-d`, `tar`, `chmod`, a `TMPDIR` a Jamf-run script does not have |
| `inventory.ea` is one line, mode 644, `arthur1.`-prefixed | A wrapped base64 value carrying newlines into `<result>`, or a value the EA script cannot read as a user |
| `inventory.ea` decodes byte-for-byte back to `inventory.json` | **The attribute not being this scan.** This tree shipped that: a failed run left the previous payload in place and the framing step re-framed it into a fresh-looking value and exited 0 |
| Six-column rows, one `kind=scan` marker per branch, every marker dated within the hour | A branch silently not running; a kept payload passing as a fresh one |
| The branch set in `status.txt` equals the marker set in the payload | The two attributes describing different scans — a Smart Group and a payload that disagree about what ran |
| Framed size under the cap `collect.sh` itself declares | A Mac that would report `ERROR:oversize` instead of its inventory, and a cap that drifted from the one being enforced |
| A failed scan: non-zero exit, **both attribute values untouched** | Either half of the trade this tree made — republishing a stale value as fresh, or deleting a good one to signal a problem |
| A failed first-ever scan: non-zero exit, **no files at all** | A partial file left behind claiming to be a result, when `no-cache` is the true answer |
| A scan that fails its JSON check — the shipped driver against a stub `discover` whose `--cache` cannot run — leaves both previous files untouched, passes discover's reason through, and leaves no staging directory | A failure after the scan erasing the last good inventory. Every step of a run, not only the scan, keeps the last good one |
| No `arthur-collect.*` directory left behind | The extraction directory leaking once per run, which on an Ongoing schedule fills a volume months later |

The container branch: the macOS runner has no Docker and reports `absent`; the Ubuntu runner
has one and reports `ok`. The 15s cold-ping bound is reached by neither. The daemon states are
upstream's `test/docker_states.sh`, against the vendored runner.

## `test/run-guest-attributes.sh`

Runs `deploy/report-guest-attributes.sh` against `test/fake-metadata-server.py`, with a stub
for the collector, because the question is what the reporter publishes from each thing a
collector can leave behind. The fake answers only as a real VM measurably did: the 262,144-byte
cap with its 400, and the 403 when guest attributes are disabled.

| Case | What it catches |
|---|---|
| A clean scan is published byte for byte, without the file's newline | A value one byte too long, or not this scan |
| A value of exactly 262,144 bytes is accepted | The newline pushing a value at the cap over it |
| A refused inventory keeps the previous value; the status says `inventory=refused:400` | A VM serving an old inventory with nothing saying why |
| A failed run publishes the kept scan with `failed=<UTC>` | A failure that looks like a fresh scan |
| No scan ever, no osquery: `no-cache`, and `no-cache failed=<UTC> osquery=absent` | An empty key, which reads as a clean VM |
| Guest attributes disabled: the 403 named, nothing stored | A VM that cannot report and says nothing |
| No metadata server: named, non-zero | The same, off Compute Engine |
| `status.txt` without `inventory.ea`: both keys `no-cache` | A status claiming a scan the inventory does not carry |
| One 503, retried through to success | A transient failure failing the run |
| Inventory refused, then the status request dropped: each logged with its own reason | A reason left over from the previous request |
| `http_proxy` set to a dead proxy: published directly | A fleet-wide proxy capturing the link-local metadata request |
| `TERM` during collection: non-zero, nothing published | A stopped run carrying on without its working directory and blaming the metadata server |

`flaky` (one 503) and `drop-status` (no answer on the `status` key) are the fake's own
behaviours, labelled as such; every other answer it gives was measured on a real VM.

## `test/run-ssm-inventory.sh`

Runs `deploy/report-ssm-inventory.sh` against `test/fake-imds.py`, with a stub for the
collector, and asserts on the values the custom inventory file's parts make again, not on the
file's shape alone: a part dropped, cut short or hashed before cleaning still leaves valid
JSON.

| Case | What it catches |
|---|---|
| A clean scan is written as the instance's custom inventory, under the directory IMDS names | A value that is not this scan, or a file the agent never finds |
| A value at the budget is cut into 64 parts that make it again | A last part cut short, or more parts than the reader accepts |
| The file is replaced, and nothing half-written is left beside it | The agent reading half a file |
| A failed run keeps the last good scan, with `failed=<UTC>` | A failure that looks like a fresh scan |
| Never collected, osquery absent: both values name the state | An empty value, which reads as a clean instance |
| A status without its inventory: both `no-cache` | A status claiming a scan the inventory does not carry |
| A quote, a backslash or a control character in a value | A file the agent cannot parse, or parts that hash to something else |
| No IMDS, a refused token, no instance id, no SSM Agent: each named, nothing written | An instance that cannot report and says nothing |
| A fleet-wide proxy | The link-local IMDS request going through the proxy |
| `TERM` during collection; the working directory afterwards | A stopped run carrying on; temporary files left behind |

## `test/run-systemd.sh`

Installs the Linux collector, the reporter and the units at their real paths, runs one
activation under systemd against the fake, one with `/tmp` and `/var/tmp` remounted `noexec`
(where the collector run by hand with no `TMPDIR` must fail and the unit must succeed), one with
guest attributes disabled, then starts the timer and checks it has a next run, and removes
everything. It writes to the machine, so it runs only with
`ARTHUR_TEST_INSTALLS_UNITS=1`, as root, where systemd is PID 1 — in CI, the Ubuntu runner.

## `deploy/terraform/tests/`

`terraform test` from `deploy/terraform/`, against mocked providers: no credentials, nothing
created. It asserts on what the module decides, in the plan.

**Each rendering is compared whole with the policy file.** The suite reads the file, puts each
file's URL at the test ref and the sha256 of the copy beside the module into it, and compares
each rendered resource with that, mapped back to the file's shape. That covers every
assignment, the folder orchestrator and the organization orchestrator. A field cannot drift in
one rendering without a run failing: a repository, a package, a script, an inventory filter,
the label, the rollout, a file mode or a URL. Replaying eight such mutations, one per field and
rendering, fails the suite eight times.

| Case | What it catches |
|---|---|
| An assignment per project and zone, each rendering the whole policy without file modes, and none waiting for the rollout | A zone with no assignment, which leaves its VMs unmanaged with nothing saying so; any field of the policy lost or changed on the way to a VM |
| `pinned_files`, and the URLs a VM downloads under `file_base_url` | A VM refusing every file, or a mirror serving the wrong path |
| `label` and `reader` reach every assignment, `arthur_source` and IAM | An Arthur source whose labels match no VM the policy reached |
| `project_metadata` limited to one key, and empty | A project that already holds `enable-osconfig` failing the apply with no way around it |
| Folder and organization orchestrators, each rendering the whole policy with its file modes; projects by number and zones as separate selectors; a named resource, and no payload under `DELETE`; folders alone, with no project selector and a null `arthur_source.project_ids` | An orchestrator scoped wider than asked, one whose `DELETE` cannot find its assignments, or an empty project list the source refuses |
| Downloaded files matching the module's copy pass; one that does not fails the plan | A `?ref=` bumped without `arthur_engine_ref` reaching every VM as a checksum mismatch |
| No ref and no mirror; no projects and no folders; folder and organization both; prefixed or empty numbers; project numbers for IDs; a project or zone twice; a label value no VM can hold; a metadata key this module does not set | A plan that would reach no VM, or the wrong scope, without saying so; Terraform's own error in place of one that names the input |

Beside the module tests, `terraform_data.policy` rebuilds the policy from the keys the module
renders and compares it whole with the file, and the renderings read only that rebuild. So a
key added, removed or reshaped in the file fails every plan with that precondition's message,
never with an attribute error from a rendering. Add `allowNoResourceGroupMatch` or a yum
repository, or swap the percentage disruption budget for a fixed one, and the first plan fails
naming the file.

CI also validates a caller at the lowest Terraform and Google provider `versions.tf` admits, in
all three modes. Every other check runs a recent Terraform and the latest provider, where
anything added since a floor passes.
