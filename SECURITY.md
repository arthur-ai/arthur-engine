# Security Policy

## Reporting a vulnerability

Please report security vulnerabilities in the Arthur Engine privately by email to
**security@arthur.ai**. Do not open a public GitHub issue, discussion or pull request for a
suspected vulnerability.

Include as much of the following as you can:

- the affected component (`genai-engine`, `ml-engine`, `arthur-observability-sdk`, an
  `integrations/` package, or a deployment template) and version or commit;
- steps to reproduce, or a proof of concept;
- the impact you expect (for example, authentication bypass, data exposure across tasks or
  tenants, remote code execution).

We will acknowledge your report, keep you updated while we investigate, and credit you in the
release notes if you would like.

## Supported versions

Security fixes are made on the `dev` branch and shipped in the next release. We recommend running
the latest release.

## Container image vulnerabilities

Known CVEs in the published Docker images, and our position on each, are tracked in
[`security/`](security/README.md).
