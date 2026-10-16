# Splunk

Reference connector: `ml-engine/src/ml_engine/discovery/siem/splunk/`.

- Async search job: create, poll, page results by `result_count`, and delete the job in `finally` whatever happened (a finished job holds a slot of the user's search quota). Ask the stop check on every poll. Retry only `GET` and `DELETE`.
- Lookback is the job's `earliest_time=-<h>h` beside the SPL; `lookback_hours <= 0` sends no `earliest_time`.
- The search API requires a search to start with `search` or a generating command's `|`. The search bar adds `search` silently, so the connector prefixes it when missing; that is the only edit made to the customer's text.
- A distributed search with a peer down still finishes `DONE`; it says so only in its messages. Log `WARN:` / `ERROR:` / `FATAL:` messages as warnings, and warn when fewer rows were readable than `result_count`.
- Zero rows: hint that the token's role must be able to search the query's indexes (`srchIndexesAllowed`).
- TLS: Splunk's default `SplunkServerDefaultCert` names no host; `ca_only` is for it.
- Its client wraps a TLS failure in `SplunkError`, which reports `provider_error` on a scan. Do not copy that; raise `DiscoveryConfigurationError(...) from exc` as Elastic does.
