# Cloudflare AI Gateway

- Lists callers and their requests through its API: a `network_gateway` source.
- SaaS on a fixed host: the source takes an account id instead of `base_url`, and has no `ca_certificate` / `tls_verification` fields.

## Enforcement surface (not built)

The vendor documents guardrails and rate limits on the gateway.
