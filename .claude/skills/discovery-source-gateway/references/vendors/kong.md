# Kong

## Which product

- **Konnect** (SaaS control plane) exposes per-request analytics at `/v2/api-requests`: a `network_gateway` source.
- **Self-hosted Kong Gateway** has no usage API; per-consumer AI traffic exists only in a log plugin's output (the `ai` log object). That is a `discovery-source-siem` query over those logs.

## Identity and least privilege

- Credential identity: the Kong consumer id, the part `external_id` is built from.
- Role: an RBAC role with read on consumers and analytics only.
- Consumer listing is the optional inventory enrichment.

## Enforcement surface (not built)

The vendor documents consumer-level controls and AI plugins (prompt guards, rate limits).
