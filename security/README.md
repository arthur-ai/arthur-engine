# Container image security — scanning & vulnerability justification

This directory holds the **vulnerability justification source of truth** for the Docker images
Arthur ships (`genai-engine-cpu`, `genai-engine-gpu`, `ml-engine`, `genai-engine-models-*`).

Customers cannot accept HIGH/CRITICAL vulnerabilities, so for every such finding we maintain a
documented position: either it is remediated (upgrade the package/base image) or it is
**justified** via a [VEX](https://openvex.dev/) statement explaining why it is not exploitable
/ acceptable. CI scans every image (Docker Scout + Trivy, **advisory — non-blocking**), publishes
findings to the GitHub **Security tab**, and generates a per-image **justification report** with
this VEX applied.

> The CI gate is intentionally **off** today (scans never fail the build). Flipping it on for
> *fixable* HIGH/CRITICAL is a one-line change per scan step — see "Turning on enforcement".

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

1. Find it in **Security → Code scanning** (categories `scout-*` / `trivy-*`) or in the report
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
# Preview findings with the VEX applied (HIGH/CRITICAL only):
trivy image --severity HIGH,CRITICAL \
  --vex security/vex/openvex.json --show-suppressed \
  --format json -o /tmp/report.json arthurplatform/genai-engine-cpu:latest

# Render the human-readable justification report:
python3 security/render_report.py /tmp/report.json /tmp/report.md arthurplatform/genai-engine-cpu:latest

# Scout view (recommendations for base-image upgrades):
docker scout cves arthurplatform/genai-engine-cpu:latest --only-severity critical,high
```

## Turning on enforcement (future)

When the backlog is triaged (every HIGH/CRITICAL is either fixed or has a VEX statement), make
the build block on **fixable** HIGH/CRITICAL by editing the composite action's Trivy step:

- set `--exit-code 1` and `--ignore-unfixed` on the Trivy scan, and/or
- set Docker Scout's `exit-on: vulnerability` with `only-severities: critical,high`.

`--ignore-unfixed` is important: it blocks only findings that have an available patch, so
unfixable base-OS CVEs (documented via VEX) do not permanently block releases.
