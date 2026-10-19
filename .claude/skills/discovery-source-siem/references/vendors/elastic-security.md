# Elastic Security

Reference connector: `ml-engine/src/ml_engine/discovery/siem/elastic_security/`.

- One call: `POST /_query` runs ES|QL and returns the whole result; there is no cursor. Records are yielded in batches of 500 (`BATCH_SIZE`).
- Row caps are the cluster's: 1,000 rows without a `LIMIT`, 10,000 with one, at the defaults of `esql.query.result_truncation_default_size` and `esql.query.result_truncation_max_size`. A capped result is logged as a warning before the first batch.
- Lookback rides in the request's `filter`, a range on `@timestamp` (`now-<h>h`); the ES|QL text is never edited.
- ES|QL only. A Query DSL body (a JSON object) is refused as `DiscoveryConfigurationError`: DSL cannot name its output columns, and the contract is checked against them.
- Timeouts: `REQUEST_TIMEOUT_SECONDS = (10.0, 90.0)`.
- TLS: `ca_only` fits Elasticsearch's auto-generated certificate reached through an alias it was not issued for. A refused handshake is `DiscoveryConfigurationError(...) from exc`.
- `_redacted` strips quoted spans from warnings so row values never reach the log.
- `_error_of` / `_reason_suffix` put Elastic's error reason into the exception text. Safe for Elastic; do not copy that part to a vendor whose errors echo credentials.
