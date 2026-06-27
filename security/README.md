# Container image security — scanning & vulnerability justification

This directory holds the **vulnerability justification source of truth** for the Docker images
Arthur ships (`genai-engine-cpu`, `genai-engine-gpu`, `ml-engine`, `genai-engine-models-*`).

Customers cannot accept HIGH/CRITICAL vulnerabilities, so for every such finding we maintain a
documented position: either it is remediated (upgrade the package/base image) or it is
**justified** via a [VEX](https://openvex.dev/) statement explaining why it is not exploitable
/ acceptable. CI scans every image (Trivy, **advisory — non-blocking**), publishes
findings to the GitHub **Security tab**, and generates a per-image **justification report** with
this VEX applied.

**Every** HIGH/CRITICAL is surfaced — unfixed CVEs are not hidden. The expectation is that each one
is triaged to a documented position (fix it, or justify it via VEX); we do **not** filter findings
out with `--ignore-unfixed`. Two views:

- **GitHub Security tab** (`trivy-*` categories) — VEX applied, so it shows the **not-yet-triaged
  backlog**: every HIGH/CRITICAL (fixable or not) that does not yet have a VEX statement. A
  VEX-accepted finding drops off here automatically.
- **Justification report artifact** (`report-*.md`) — the **full** picture: every unresolved
  finding plus a table of everything accepted via VEX, with status + justification.

> The CI gate is intentionally **off** today (scans never fail the build). Flipping it on for
> *fixable* HIGH/CRITICAL is a small change — see "Turning on enforcement".

## Layout

| Path | Purpose |
| --- | --- |
| `vex/openvex.json` | OpenVEX source of truth — one statement per accepted (CVE, product). |
| `render_report.py` | Renders the human-readable Markdown report from a Trivy JSON report. |
| `README.md` | This file. |

Generated artifacts (SBOM, per-image reports) are **not** committed; they are produced by CI and
uploaded as workflow artifacts (and re-generated daily by `.github/workflows/image-vuln-scan.yml`).

## Where the scanning runs

- **Per release build** — `.github/workflows/arthur-engine-workflow.yml` calls the
  `vuln-report` composite action after building `genai-engine-*` and `ml-engine`.
- **Daily + on-demand** — `.github/workflows/image-vuln-scan.yml` re-scans all published
  `:latest` images, so newly-disclosed CVEs on already-shipped images are caught and the
  justification reports regenerate without a rebuild. This also covers the `genai-engine-models-*`
  images (which are rebuilt only when models change).

Both call the shared composite action `.github/workflows/composite-actions/vuln-report`.

## Triaging a new HIGH/CRITICAL finding

1. Find it in **Security → Code scanning** (categories `trivy-*`) or in the report
   artifact from the latest scan run.
2. **If a fix exists** (the report shows a "Fixed" version): let Renovate bump it, or bump the
   dependency / Docker base image manually, and rebuild. Prefer fixing over justifying.
3. **If no fix exists, or it is not exploitable in our usage**: add a VEX statement (below).

### Adding a VEX statement

Edit `vex/openvex.json` (or author with [`vexctl`](https://github.com/openvex/vexctl)). Each
statement binds a vulnerability to one or more products and gives a status + justification:

```jsonc
{
  "vulnerability": { "name": "CVE-2025-12345" },
  "products": [ { "@id": "pkg:oci/genai-engine-cpu" } ],
  "status": "not_affected",
  "justification": "vulnerable_code_not_in_execute_path",
  "impact_statement": "The affected function is never called by the engine; see <link>.",
  "timestamp": "2026-06-25T00:00:00Z"
}
```

- `status`: `not_affected` | `affected` | `fixed` | `under_investigation`.
- For `not_affected`, OpenVEX requires a `justification` (one of: `component_not_present`,
  `vulnerable_code_not_present`, `vulnerable_code_not_in_execute_path`,
  `vulnerable_code_cannot_be_controlled_by_adversary`, `inline_mitigations_already_exist`).
- `products[].@id` must match the image purl the scanner reports (e.g. `pkg:oci/ml-engine`).
- **Subcomponents: scope by package name only — never pin a version or qualifiers.** Use
  `pkg:deb/debian/libssl3`, **not** `pkg:deb/debian/libssl3@3.0.19-1~deb12u2?distro=debian-12`.
  Trivy's package purls carry `?arch=…&distro=debian-12.NN` (the distro **point release**), which
  changes on every base-image bump. A version/qualifier-pinned subcomponent silently stops matching
  the moment that drifts, and the suppression breaks with no error — the CVE just reappears as open.
  A name-only subcomponent matches across rebuilds. (This is exactly what broke the VEX before:
  every statement pinned `?distro=debian-12` and matched nothing.)
- Include a **rationale + owner + review date** so the justification is auditable. Re-review
  `under_investigation` and `affected` entries regularly.

With `vexctl`:

```bash
vexctl create \
  --product "pkg:oci/genai-engine-cpu" \
  --vuln CVE-2025-12345 \
  --status not_affected \
  --justification vulnerable_code_not_in_execute_path \
  --author "security@arthur.ai" \
  >> vex/openvex.json   # then merge into the single document with `vexctl merge`
```

## Verifying locally

```bash
# Full picture (HIGH/CRITICAL, incl. unfixed + VEX-suppressed) — same scan CI runs:
trivy image --severity HIGH,CRITICAL \
  --vex security/vex/openvex.json --show-suppressed \
  --format json -o /tmp/report.json arthurplatform/genai-engine-cpu:latest

# Render the human-readable justification report:
python3 security/render_report.py /tmp/report.json /tmp/report.md arthurplatform/genai-engine-cpu:latest

# What reaches the GitHub Security tab = the converted SARIF (VEX-accepted findings excluded):
trivy convert --format sarif -o /tmp/trivy.sarif /tmp/report.json
```

> Tip: to confirm a VEX statement actually matches, check that the CVE moves into
> `ExperimentalModifiedFindings` in the JSON report (or just disappears from `Vulnerabilities`).
> If it's still under `Vulnerabilities`, the subcomponent purl didn't match — see the name-only
> rule above. On Apple Silicon, add `--image-src remote` if a local `docker` layer export fails.

## Turning on enforcement (future)

When the backlog is triaged (every HIGH/CRITICAL is either fixed or has a VEX statement), make
the build block on **fixable** HIGH/CRITICAL by adding `--exit-code 1` **and** `--ignore-unfixed`
to the Trivy scan step in the composite action.

`--ignore-unfixed` is important *for enforcement* (not for the advisory Security-tab view): it
blocks only findings that have an available patch, so unfixable base-OS CVEs (documented via VEX)
do not permanently block releases.
