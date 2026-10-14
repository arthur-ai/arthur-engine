# Kong

## Which product

- **Konnect** (SaaS control plane) exposes per-request analytics at `/v2/api-requests`: a `network_gateway` source.
- **Self-hosted Kong Gateway** has no usage API; per-consumer AI traffic exists only in a log plugin's output (the `ai` log object). That is a `discovery-source-siem` query over those logs.

## Self-hosted via a SIEM

- The http-log plugin's entries carry the caller in `consumer.id` / `consumer.username`, the model in `ai.proxy.meta.response_model` with `ai.proxy.meta.provider_name`, and the status in `response.status`. ai-proxy writes the `ai` object only with `log_statistics: true`.
- The same entries carry request headers, including consumer and provider API keys in clear: a query must project only the contract columns.
- An entry names no Kong node or cluster; `request.url` holds whatever host the client used. Namespace the external id with a fixed label the customer chooses (e.g. `kong:<label>:<consumer.id>`), or add a node field through http-log `custom_fields_by_lua`. DB-less consumer ids are deterministic, so two clusters can share them.
- Rows with no consumer, or on routes without ai-proxy, are not agent traffic.
- The SIEM credential needs read on the log index only.
- Which field marks a request ai-proxy refused is not established yet; capture one before relying on the refused-request fold.

## Identity and least privilege

- Credential identity: the Kong consumer id, the part `external_id` is built from.
- Role: an RBAC role with read on consumers and analytics only.
- Consumer listing is the optional inventory enrichment.

## Enforcement surface (not built)

The vendor documents consumer-level controls and AI plugins (prompt guards, rate limits).
